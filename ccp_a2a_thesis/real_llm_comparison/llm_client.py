"""OpenAI/OpenAI-compatible stdlib client for real LLM experiments."""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

class LLMClient:
    """Tiny stdlib OpenAI/OpenAI-compatible client."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str,
        api_mode: str,
        temperature: Optional[float],
        timeout: int,
        retries: int,
        retry_backoff: float,
    ) -> None:
        self.max_output_tokens = None
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_mode = api_mode
        self.temperature = temperature
        self.timeout = timeout
        self.retries = retries
        self.retry_backoff = retry_backoff
        self.api_call_log: List[Dict[str, Any]] = []

    def complete_json(
        self, system: str, user: str, call_label: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        text = self.complete_text(system, user, call_label=call_label)
        return self._parse_json(text)

    def complete_json_with_text(
        self, system: str, user: str, call_label: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
        text = self.complete_text(system, user, call_label=call_label)
        try:
            return self._parse_json(text), text, None
        except json.JSONDecodeError as exc:
            return None, text, str(exc)

    def complete_text(
        self, system: str, user: str, call_label: Optional[Dict[str, Any]] = None
    ) -> str:
        if self.api_mode == "responses":
            payload = {
                "model": self.model,
                "instructions": system,
                "input": user,
            }
            if self.temperature is not None:
                payload["temperature"] = self.temperature
            if self.max_output_tokens is not None:
                payload["max_output_tokens"] = self.max_output_tokens
            response = self._post("/responses", payload, call_label=call_label)
            return self._extract_responses_text(response)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        if self.max_output_tokens is not None:
            payload["max_completion_tokens"] = self.max_output_tokens
        response = self._post("/chat/completions", payload, call_label=call_label)
        return response["choices"][0]["message"]["content"]

    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        call_label: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        max_attempts = self.retries + 1
        for attempt in range(max_attempts):
            started_at = time.time()
            request = urllib.request.Request(
                f"{self.base_url}{path}",
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response_body = json.loads(response.read().decode("utf-8"))
                    self._log_api_call(
                        path=path,
                        payload=payload,
                        status_code=response.status,
                        response_body=response_body,
                        started_at=started_at,
                        call_label=call_label,
                        attempt=attempt,
                        max_attempts=max_attempts,
                    )
                    return response_body
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                self._log_api_call(
                    path=path,
                    payload=payload,
                    status_code=exc.code,
                    response_body=None,
                    started_at=started_at,
                    call_label=call_label,
                    error_body=detail,
                    attempt=attempt,
                    max_attempts=max_attempts,
                )
                if not self._should_retry_http(exc.code, detail, attempt, max_attempts):
                    raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc
            except (TimeoutError, socket.timeout, urllib.error.URLError) as exc:
                self._log_api_call(
                    path=path,
                    payload=payload,
                    status_code=0,
                    response_body=None,
                    started_at=started_at,
                    call_label=call_label,
                    error_body=str(exc),
                    attempt=attempt,
                    max_attempts=max_attempts,
                )
                if attempt >= max_attempts - 1:
                    raise RuntimeError(
                        f"API request failed after {max_attempts} attempts: {exc}"
                    ) from exc
            sleep_seconds = self.retry_backoff * (2**attempt)
            print(
                f"\n  transient API failure; retrying in {sleep_seconds:.1f}s "
                f"(attempt {attempt + 2}/{max_attempts})",
                flush=True,
            )
            time.sleep(sleep_seconds)

        raise RuntimeError("API request failed for an unknown reason.")

    @staticmethod
    def _should_retry_http(
        status_code: int, detail: str, attempt: int, max_attempts: int
    ) -> bool:
        if attempt >= max_attempts - 1:
            return False
        if status_code == 429 and "insufficient_quota" not in detail:
            return True
        return status_code in {408, 409, 500, 502, 503, 504}

    def _log_api_call(
        self,
        path: str,
        payload: Dict[str, Any],
        status_code: int,
        response_body: Optional[Dict[str, Any]],
        started_at: float,
        call_label: Optional[Dict[str, Any]],
        error_body: Optional[str] = None,
        attempt: int = 0,
        max_attempts: int = 1,
    ) -> None:
        self.api_call_log.append(
            {
                "call_index": len(self.api_call_log),
                "label": call_label or {},
                "attempt": attempt + 1,
                "max_attempts": max_attempts,
                "request": {
                    "url": f"{self.base_url}{path}",
                    "api_mode": self.api_mode,
                    "payload": payload,
                },
                "response": {
                    "status_code": status_code,
                    "body": response_body,
                    "error_body": error_body,
                },
                "timing": {
                    "started_at_unix": started_at,
                    "elapsed_seconds": time.time() - started_at,
                },
            }
        )

    @staticmethod
    def _extract_responses_text(response: Dict[str, Any]) -> str:
        if isinstance(response.get("output_text"), str):
            return response["output_text"]

        chunks: List[str] = []
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        if chunks:
            return "\n".join(chunks)
        raise RuntimeError(f"Could not extract text from response: {response}")

    @staticmethod
    def _parse_json(text: str) -> Dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start >= 0 and end > start:
                snippet = cleaned[start : end + 1]
                try:
                    return json.loads(snippet)
                except json.JSONDecodeError:
                    repaired = LLMClient._repair_common_json_issues(snippet)
                    try:
                        return json.loads(repaired)
                    except json.JSONDecodeError:
                        # Try repairing the full cleaned text as a fallback
                        repaired_full = LLMClient._repair_common_json_issues(cleaned)
                        start_full = repaired_full.find("{")
                        end_full = repaired_full.rfind("}")
                        if start_full >= 0 and end_full > start_full:
                            final_snippet = repaired_full[start_full : end_full + 1]
                            return json.loads(final_snippet)
                        raise
            # If we can't find JSON braces, try repairing the full text
            repaired_full = LLMClient._repair_common_json_issues(cleaned)
            try:
                return json.loads(repaired_full)
            except json.JSONDecodeError:
                # One more attempt: extract JSON from repaired text
                start_full = repaired_full.find("{")
                end_full = repaired_full.rfind("}")
                if start_full >= 0 and end_full > start_full:
                    final_snippet = repaired_full[start_full : end_full + 1]
                    return json.loads(final_snippet)
                raise

    @staticmethod
    def _repair_common_json_issues(text: str) -> str:
        # Handles the most common malformed judge response: unescaped newlines
        # inside strings. This is intentionally conservative and still raises if
        # the JSON is structurally broken in other ways.
        repaired = []
        in_string = False
        escaped = False
        for char in text:
            if escaped:
                repaired.append(char)
                escaped = False
                continue
            if char == "\\":
                repaired.append(char)
                escaped = True
                continue
            if char == '"':
                in_string = not in_string
                repaired.append(char)
                continue
            if in_string and char in {"\n", "\r"}:
                repaired.append("\\n")
                continue
            repaired.append(char)
        return "".join(repaired)
