"""Run a real-LLM CCP vs text comparison.

This script intentionally lives outside the main simulator so live API-backed
experiments do not change the deterministic thesis simulator.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.agent_a import AgentA  # noqa: E402
from core.task import Task, TaskManager  # noqa: E402


DETECTION_KEYS = {
    "vegetarian": False,
    "peanut_allergy": False,
    "window_seat": False,
    "knee_injury": False,
    "gaming": False,
    "food_interest": False,
}


TEXT_FORWARD_PROMPT = (
    "You are Agent B in a multi-agent workflow. Forward the message to the next "
    "agent in natural language. Keep it brief. Do not add new facts."
)

TEXT_PROCESS_PROMPT = (
    "You are Agent B in a multi-agent workflow. Process the message for the next "
    "agent by extracting the actionable request, key constraints, and next-step "
    "requirements. If there are safety-critical constraints such as allergies or "
    "injuries, preserve and emphasize them. Do not add new facts."
)

TEXT_SUMMARIZE_PROMPT = (
    "You are Agent B in a multi-agent workflow. Summarize the previous message "
    "concisely for the next agent. Keep only the main actionable point and avoid "
    "unnecessary detail. Do not add new facts."
)

CCP_FORWARD_PROMPT = (
    "You are Agent B in a multi-agent workflow. You receive a Canonical Context "
    "Payload JSON object and must forward valid JSON only. Do not add new facts. "
    "Do not change task_id, context, extended_context, constraints, request, or "
    "metadata. Do not invent timestamps. If you need to add processing information, "
    "put it in a processing_notes field. The system will record state_lineage."
)

CCP_PROCESS_PROMPT = (
    "You are Agent B in a multi-agent workflow. You receive a Canonical Context "
    "Payload JSON object and must output valid JSON only. Process the payload for "
    "the next agent, but do not change task_id, context, extended_context, "
    "constraints, request, or metadata. Preserve all invariant and preference "
    "fields exactly. Do not invent timestamps. If you need to add processing "
    "information, put it in a processing_notes field. The system will record "
    "state_lineage."
)

CCP_SUMMARIZE_PROMPT = (
    "You are Agent B in a multi-agent workflow. You receive a Canonical Context "
    "Payload JSON object and must output valid JSON only. You may summarize "
    "non-canonical processing notes, but do not change task_id, context, "
    "extended_context, constraints, request, or metadata. Preserve all invariant "
    "and preference fields exactly. Do not invent timestamps. The system will "
    "record state_lineage."
)

AGENT_C_PROMPT = (
    "You are Agent C, the final decision maker. Inspect the message from the "
    "previous agent and return JSON only with exactly these top-level keys: "
    "response, detected_constraints, protocol. detected_constraints must contain "
    "booleans for vegetarian, peanut_allergy, window_seat, knee_injury, gaming, "
    "food_interest. Mark a constraint true only if the previous agent's message "
    "preserves that meaning. The response must substantively complete the user's "
    "task using only detected data, not merely restate constraints. For recipe "
    "tasks, include a title, ingredients, and preparation steps. For workout "
    "tasks, include concrete exercises. For travel tasks, include concrete "
    "itinerary items. For laptop tasks, include concrete specs or model criteria. "
    "For flight tasks, include a concrete seat assignment or recommendation. The "
    "response must not contradict detected constraints; for example, never claim "
    "a recipe is peanut-free while listing peanuts or peanut products as "
    "ingredients. Warn if safety-critical constraints are missing."
)

JUDGE_PROMPT = (
    "You are a strict evaluation judge for a context-retention and task-completion "
    "experiment. Compare the original request and constraints with the full final "
    "response, including every ingredient, exercise, itinerary item, specification, "
    "and recommendation. Return JSON only with keys violations, score, notes, "
    "contradictions, and completion_issues. violations must be a list of violated "
    "or ignored constraint keys. contradictions must list any place where the "
    "response claims to satisfy a constraint but later violates it, such as saying "
    "peanut-free while including peanuts, peanut butter, peanut oil, satay, or "
    "other peanut products. completion_issues must list missing task deliverables, "
    "such as a recipe with no ingredients or steps. score must be a number from "
    "0.0 to 1.0 where 1.0 means the response respects all constraints, contains no "
    "contradictions, and substantively completes the user request."
)


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
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.api_mode = api_mode
        self.temperature = temperature
        self.timeout = timeout
        self.api_call_log: List[Dict[str, Any]] = []

    def complete_json(
        self, system: str, user: str, call_label: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        text = self.complete_text(system, user, call_label=call_label)
        return self._parse_json(text)

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
        response = self._post("/chat/completions", payload, call_label=call_label)
        return response["choices"][0]["message"]["content"]

    def _post(
        self,
        path: str,
        payload: Dict[str, Any],
        call_label: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
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
            )
            raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc

    def _log_api_call(
        self,
        path: str,
        payload: Dict[str, Any],
        status_code: int,
        response_body: Optional[Dict[str, Any]],
        started_at: float,
        call_label: Optional[Dict[str, Any]],
        error_body: Optional[str] = None,
    ) -> None:
        self.api_call_log.append(
            {
                "call_index": len(self.api_call_log),
                "label": call_label or {},
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
                return json.loads(cleaned[start : end + 1])
            raise


class RealLLMComparison:
    def __init__(
        self,
        client: LLMClient,
        trials: int,
        sleep_seconds: float,
        agent_b_mode: str,
        hops: int,
        judge: bool,
    ) -> None:
        self.client = client
        self.trials = trials
        self.sleep_seconds = sleep_seconds
        self.agent_b_mode = agent_b_mode
        self.hops = hops
        self.judge = judge
        self.agent_a = AgentA()

    def run(self, tasks: List[Task]) -> Dict[str, Any]:
        run_started_at_unix = time.time()
        run_started_at_local = local_timestamp()
        task_results = []
        for task in tasks:
            print(f"\nTask {task.task_id}: {task.category}")
            trials = []
            for trial in range(self.trials):
                print(f"  trial {trial + 1}/{self.trials}: text", end="", flush=True)
                text_result = self._run_protocol(task, "text", trial)
                self._pause()
                print(", ccp", end="", flush=True)
                ccp_result = self._run_protocol(task, "ccp", trial)
                print(" done")
                trials.append({"trial": trial, "text": text_result, "ccp": ccp_result})
                self._pause()
            task_results.append(
                {"task_id": task.task_id, "category": task.category, "trials": trials}
            )

        summary = aggregate_results(task_results)
        run_completed_at_unix = time.time()
        return {
            "metadata": {
                "model": self.client.model,
                "api_mode": self.client.api_mode,
                "temperature": self.client.temperature,
                "trials_per_task": self.trials,
                "agent_b_mode": self.agent_b_mode,
                "hops": self.hops,
                "judge_enabled": self.judge,
                "created_at_unix": run_started_at_unix,
                "created_at_local": run_started_at_local,
                "completed_at_unix": run_completed_at_unix,
                "completed_at_local": local_timestamp(),
                "prompts": self._prompt_manifest(),
            },
            "summary": summary,
            "tasks": task_results,
            "api_calls": self.client.api_call_log,
        }

    def _run_protocol(self, task: Task, protocol: str, trial: int) -> Dict[str, Any]:
        agent_a_output = self.agent_a.process(task.to_dict(), protocol=protocol)
        forwarded = agent_a_output
        hop_outputs = []
        raw_hop_outputs = []
        for hop_index in range(self.hops):
            forwarded, raw_forwarded = self._agent_b_forward(
                task, protocol, forwarded, hop_index, trial
            )
            hop_outputs.append(forwarded)
            raw_hop_outputs.append(raw_forwarded)
            self._pause()
        final_output = self._agent_c_decide(task, protocol, forwarded, trial)
        judge_output = (
            self._judge_response(task, protocol, final_output, trial)
            if self.judge
            else None
        )
        result = {
            "accuracy": calculate_accuracy(final_output, task.constraints),
            "crs": calculate_context_retention_score(task.constraints, final_output),
            "deterministic_violations": detect_response_violations(
                final_output, task.constraints
            ),
            "agent_a_output": agent_a_output,
            "agent_b_outputs": hop_outputs,
            "agent_b_raw_outputs": raw_hop_outputs,
            "agent_b_output": forwarded,
            "final_output": final_output,
        }
        if judge_output is not None:
            result["judge_output"] = judge_output
        return result

    def _agent_b_forward(
        self, task: Task, protocol: str, payload: Any, hop_index: int, trial: int
    ) -> Tuple[Any, Any]:
        system_prompt = self._agent_b_prompt(protocol)
        hop_agent_id = f"B{hop_index + 1}"
        hop_label = f"Forwarder {hop_index + 1}"
        call_label = {
            "task_id": task.task_id,
            "task_category": task.category,
            "trial": trial,
            "protocol": protocol,
            "agent": hop_label,
            "role": "agent_b_hop",
            "hop_index": hop_index,
            "hop_agent_id": hop_agent_id,
            "agent_b_mode": self.agent_b_mode,
        }
        if protocol == "text":
            output = self.client.complete_text(
                system=system_prompt,
                user=(
                    f"Current agent: {hop_label}\n"
                    f"Original task category: {task.category}\n"
                    f"Message from previous agent:\n{payload}"
                ),
                call_label=call_label,
            )
            return output, output

        raw_output = self.client.complete_json(
            system=system_prompt,
            user=(
                f"Current agent: {hop_label}\n"
                f"Original task category: {task.category}\n"
                f"Payload from previous agent:\n{json.dumps(payload, indent=2)}"
            ),
            call_label=call_label,
        )
        normalized_output = self._normalize_ccp_payload(payload, raw_output, hop_agent_id)
        return normalized_output, raw_output

    def _normalize_ccp_payload(
        self,
        previous_payload: Any,
        model_payload: Any,
        hop_agent_id: str,
    ) -> Dict[str, Any]:
        if not isinstance(previous_payload, dict):
            previous_payload = {}
        normalized = dict(model_payload) if isinstance(model_payload, dict) else {}

        for key in [
            "task_id",
            "context",
            "extended_context",
            "request",
            "constraints",
            "metadata",
        ]:
            if key in previous_payload:
                normalized[key] = previous_payload[key]

        timestamp = datetime.now().isoformat()
        normalized["agent_id"] = hop_agent_id
        normalized["timestamp"] = timestamp

        previous_lineage = previous_payload.get("state_lineage", [])
        if not isinstance(previous_lineage, list):
            previous_lineage = []
        normalized["state_lineage"] = [
            *previous_lineage,
            {
                "agent_id": hop_agent_id,
                "timestamp": timestamp,
                "action": self.agent_b_mode,
            },
        ]
        return normalized

    def _agent_c_decide(
        self, task: Task, protocol: str, payload: Any, trial: int
    ) -> Dict[str, Any]:
        payload_text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
        result = self.client.complete_json(
            system=AGENT_C_PROMPT,
            user=f"Protocol: {protocol}\nMessage from previous agent:\n{payload_text}",
            call_label={
                "task_id": task.task_id,
                "task_category": task.category,
                "trial": trial,
                "protocol": protocol,
                "agent": "Agent C",
                "role": "final_decision",
            },
        )
        detected = dict(DETECTION_KEYS)
        detected.update(result.get("detected_constraints", {}))
        return {
            "response": str(result.get("response", "")),
            "detected_constraints": {
                key: bool(detected.get(key, False)) for key in DETECTION_KEYS
            },
            "protocol": protocol,
        }

    def _judge_response(
        self, task: Task, protocol: str, final_output: Dict[str, Any], trial: int
    ) -> Dict[str, Any]:
        result = self.client.complete_json(
            system=JUDGE_PROMPT,
            user=(
                f"Protocol: {protocol}\n"
                f"Original constraints:\n{json.dumps(task.constraints, indent=2)}\n"
                f"Final output:\n{json.dumps(final_output, indent=2)}"
            ),
            call_label={
                "task_id": task.task_id,
                "task_category": task.category,
                "trial": trial,
                "protocol": protocol,
                "agent": "Judge",
                "role": "constraint_respect_judge",
            },
        )
        violations = result.get("violations", [])
        if not isinstance(violations, list):
            violations = [str(violations)]
        contradictions = result.get("contradictions", [])
        if not isinstance(contradictions, list):
            contradictions = [str(contradictions)]
        completion_issues = result.get("completion_issues", [])
        if not isinstance(completion_issues, list):
            completion_issues = [str(completion_issues)]
        try:
            score = float(result.get("score", 0.0))
        except (TypeError, ValueError):
            score = 0.0
        return {
            "violations": [str(violation) for violation in violations],
            "contradictions": [str(issue) for issue in contradictions],
            "completion_issues": [str(issue) for issue in completion_issues],
            "score": max(0.0, min(1.0, score)),
            "notes": str(result.get("notes", "")),
        }

    def _agent_b_prompt(self, protocol: str) -> str:
        if protocol == "text" and self.agent_b_mode == "forward":
            return TEXT_FORWARD_PROMPT
        if protocol == "text" and self.agent_b_mode == "process":
            return TEXT_PROCESS_PROMPT
        if protocol == "text":
            return TEXT_SUMMARIZE_PROMPT
        if self.agent_b_mode == "forward":
            return CCP_FORWARD_PROMPT
        if self.agent_b_mode == "process":
            return CCP_PROCESS_PROMPT
        return CCP_SUMMARIZE_PROMPT

    def _prompt_manifest(self) -> Dict[str, str]:
        return {
            "text_forward": TEXT_FORWARD_PROMPT,
            "text_process": TEXT_PROCESS_PROMPT,
            "text_summarize": TEXT_SUMMARIZE_PROMPT,
            "ccp_forward": CCP_FORWARD_PROMPT,
            "ccp_process": CCP_PROCESS_PROMPT,
            "ccp_summarize": CCP_SUMMARIZE_PROMPT,
            "agent_c": AGENT_C_PROMPT,
            "judge": JUDGE_PROMPT,
        }

    def _pause(self) -> None:
        if self.sleep_seconds > 0:
            time.sleep(self.sleep_seconds)


def select_tasks(category: Optional[str]) -> List[Task]:
    tasks = TaskManager.get_all_tasks()
    if not category:
        return tasks
    matches = [task for task in tasks if task.category.lower() == category.lower()]
    if not matches:
        available = ", ".join(task.category for task in tasks)
        raise SystemExit(f"Unknown task {category!r}. Available: {available}")
    return matches


def map_constraint_key(key: str) -> str:
    mapping = {
        "diet": "vegetarian",
        "allergy": "peanut_allergy",
        "seat": "window_seat",
        "injury": "knee_injury",
        "purpose": "gaming",
        "interest": "food_interest",
    }
    return mapping.get(key, key)


def calculate_context_retention_score(
    original_constraints: Dict[str, str], final_output: Dict[str, Any]
) -> float:
    if not original_constraints:
        return 1.0

    detected = final_output.get("detected_constraints", {})
    preserved = 0
    for constraint_key in original_constraints:
        detection_key = map_constraint_key(constraint_key)
        if detected.get(detection_key, False):
            preserved += 1
    return preserved / len(original_constraints)


def calculate_accuracy(
    final_output: Dict[str, Any], original_constraints: Dict[str, str]
) -> bool:
    detected = final_output.get("detected_constraints", {})
    response = final_output.get("response", "")
    for constraint_key in original_constraints:
        detection_key = map_constraint_key(constraint_key)
        if detected.get(detection_key, False):
            continue
        if constraint_key in {"allergy", "injury"}:
            return False
        if "Warning" in response or "warning" in response:
            return False
    return True


def detect_response_violations(
    final_output: Dict[str, Any], original_constraints: Dict[str, str]
) -> List[str]:
    response = str(final_output.get("response", "")).lower()
    violations = []

    if original_constraints.get("allergy") and "peanut" in original_constraints["allergy"].lower():
        peanut_terms = [
            "peanut butter",
            "peanut oil",
            "peanut sauce",
            "crushed peanuts",
            "roasted peanuts",
            "satay",
            "groundnut",
        ]
        if any(term in response for term in peanut_terms):
            violations.append("allergy")

    if original_constraints.get("diet") and "vegetarian" in original_constraints["diet"].lower():
        non_vegetarian_terms = [
            "chicken",
            "beef",
            "pork",
            "bacon",
            "ham",
            "fish",
            "shrimp",
            "anchovy",
        ]
        if any(term in response for term in non_vegetarian_terms):
            violations.append("diet")

    if original_constraints.get("injury") and "knee" in original_constraints["injury"].lower():
        knee_risk_terms = [
            "jump squats",
            "box jumps",
            "deep squats",
            "burpees",
            "running sprints",
        ]
        if any(term in response for term in knee_risk_terms):
            violations.append("injury")

    return sorted(set(violations))


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def std(values: List[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return (sum((value - avg) ** 2 for value in values) / len(values)) ** 0.5


def local_timestamp() -> str:
    """Return the machine's local datetime with timezone offset."""
    return datetime.now().astimezone().isoformat()


def aggregate_results(task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    text_accuracies: List[float] = []
    ccp_accuracies: List[float] = []
    text_crs: List[float] = []
    ccp_crs: List[float] = []
    text_judge_scores: List[float] = []
    ccp_judge_scores: List[float] = []
    text_hard_violations = 0
    ccp_hard_violations = 0

    for task_result in task_results:
        for trial in task_result.get("trials", []):
            text_accuracies.append(float(trial["text"]["accuracy"]))
            ccp_accuracies.append(float(trial["ccp"]["accuracy"]))
            text_crs.append(float(trial["text"]["crs"]))
            ccp_crs.append(float(trial["ccp"]["crs"]))
            if "judge_output" in trial["text"]:
                text_judge_scores.append(float(trial["text"]["judge_output"]["score"]))
            if "judge_output" in trial["ccp"]:
                ccp_judge_scores.append(float(trial["ccp"]["judge_output"]["score"]))
            if trial["text"].get("deterministic_violations"):
                text_hard_violations += 1
            if trial["ccp"].get("deterministic_violations"):
                ccp_hard_violations += 1

    summary = {
        "text": {
            "mean_accuracy": mean(text_accuracies),
            "std_accuracy": std(text_accuracies),
            "mean_crs": mean(text_crs),
            "std_crs": std(text_crs),
            "total_trials": len(text_accuracies),
            "hard_violation_trials": text_hard_violations,
            "hard_violation_rate": (
                text_hard_violations / len(text_accuracies) if text_accuracies else 0.0
            ),
        },
        "ccp": {
            "mean_accuracy": mean(ccp_accuracies),
            "std_accuracy": std(ccp_accuracies),
            "mean_crs": mean(ccp_crs),
            "std_crs": std(ccp_crs),
            "total_trials": len(ccp_accuracies),
            "hard_violation_trials": ccp_hard_violations,
            "hard_violation_rate": (
                ccp_hard_violations / len(ccp_accuracies) if ccp_accuracies else 0.0
            ),
        },
    }
    if text_judge_scores or ccp_judge_scores:
        summary["text"]["mean_judge_score"] = mean(text_judge_scores)
        summary["text"]["std_judge_score"] = std(text_judge_scores)
        summary["ccp"]["mean_judge_score"] = mean(ccp_judge_scores)
        summary["ccp"]["std_judge_score"] = std(ccp_judge_scores)
    return summary


def summarize_conditions(conditions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for condition in conditions:
        summary = condition["results"]["summary"]
        rows.append(
            {
                "model": condition.get("model")
                or condition.get("results", {}).get("metadata", {}).get("model"),
                "agent_b_mode": condition.get("agent_b_mode")
                or condition.get("results", {}).get("metadata", {}).get("agent_b_mode"),
                "hops": condition.get("hops")
                or condition.get("results", {}).get("metadata", {}).get("hops"),
                "temperature": condition["temperature"],
                "text_mean_crs": summary["text"]["mean_crs"],
                "ccp_mean_crs": summary["ccp"]["mean_crs"],
                "crs_delta": summary["ccp"]["mean_crs"] - summary["text"]["mean_crs"],
                "text_mean_accuracy": summary["text"]["mean_accuracy"],
                "ccp_mean_accuracy": summary["ccp"]["mean_accuracy"],
                "accuracy_delta": (
                    summary["ccp"]["mean_accuracy"] - summary["text"]["mean_accuracy"]
                ),
                "text_hard_violation_rate": summary["text"].get(
                    "hard_violation_rate", 0.0
                ),
                "ccp_hard_violation_rate": summary["ccp"].get(
                    "hard_violation_rate", 0.0
                ),
                "text_mean_judge_score": summary["text"].get("mean_judge_score"),
                "ccp_mean_judge_score": summary["ccp"].get("mean_judge_score"),
            }
        )
    return rows


def collect_api_calls(results: Dict[str, Any]) -> List[Dict[str, Any]]:
    if "api_calls" in results:
        return results["api_calls"]

    calls = []
    for condition in results.get("conditions", []):
        temperature = condition.get("temperature")
        for call in condition.get("results", {}).get("api_calls", []):
            call_with_condition = dict(call)
            call_with_condition["temperature_condition"] = temperature
            calls.append(call_with_condition)
    return calls


def dry_run(tasks: List[Task]) -> None:
    agent_a = AgentA()
    for task in tasks:
        print(f"\n=== {task.category} ===")
        print("Text payload:")
        print(agent_a.process(task.to_dict(), protocol="text"))
        print("\nCCP payload:")
        print(json.dumps(agent_a.process(task.to_dict(), protocol="ccp"), indent=2))


def run_temperature_condition(args: argparse.Namespace, temperature: Optional[float]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY or run with --dry-run.")

    client = LLMClient(
        api_key=api_key,
        model=args.model,
        base_url=args.base_url,
        api_mode=args.api_mode,
        temperature=temperature,
        timeout=args.timeout,
    )
    runner = RealLLMComparison(
        client,
        trials=args.trials,
        sleep_seconds=args.sleep,
        agent_b_mode=args.agent_b_mode,
        hops=args.hops,
        judge=args.judge,
    )
    return runner.run(select_tasks(args.task))


def run_batch_conditions(args: argparse.Namespace) -> Dict[str, Any]:
    run_started_at_unix = time.time()
    temperatures = args.temperatures or (
        [args.temperature] if args.temperature is not None else [None]
    )
    modes = args.agent_b_modes or [args.agent_b_mode]
    hops_values = args.hops_values or [args.hops]
    models = args.models or [args.model]

    results = {
        "metadata": {
            "models": models,
            "api_mode": args.api_mode,
            "temperature_conditions": temperatures,
            "agent_b_modes": modes,
            "hops_values": hops_values,
            "trials_per_task": args.trials,
            "judge_enabled": args.judge,
            "created_at_unix": run_started_at_unix,
            "created_at_local": local_timestamp(),
        },
        "conditions": [],
    }

    original_model = args.model
    original_mode = args.agent_b_mode
    original_hops = args.hops
    for model in models:
        args.model = model
        for mode in modes:
            args.agent_b_mode = mode
            for hops in hops_values:
                args.hops = hops
                for temperature in temperatures:
                    print(
                        "\n=== Condition: "
                        f"model={model}, mode={mode}, hops={hops}, "
                        f"temperature={temperature} ==="
                    )
                    results["conditions"].append(
                        {
                            "model": model,
                            "agent_b_mode": mode,
                            "hops": hops,
                            "temperature": temperature,
                            "results": run_temperature_condition(args, temperature),
                        }
                    )

    args.model = original_model
    args.agent_b_mode = original_mode
    args.hops = original_hops
    results["condition_summary"] = summarize_conditions(results["conditions"])
    results["metadata"]["completed_at_unix"] = time.time()
    results["metadata"]["completed_at_local"] = local_timestamp()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--task", help="Run one task category, e.g. Food")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-nano"))
    parser.add_argument(
        "--base-url",
        default=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    parser.add_argument(
        "--api-mode",
        choices=["responses", "chat_completions"],
        default=os.getenv("OPENAI_API_MODE", "responses"),
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Optional sampling temperature. Omitted by default because some models reject it.",
    )
    parser.add_argument(
        "--temperatures",
        nargs="+",
        type=float,
        help="Run multiple temperature conditions, e.g. --temperatures 0.1 0.7.",
    )
    parser.add_argument(
        "--models",
        nargs="+",
        help="Run multiple model conditions, e.g. --models gpt-4.1-nano gpt-4o-mini.",
    )
    parser.add_argument(
        "--agent-b-mode",
        choices=["forward", "process", "summarize"],
        default="forward",
        help="Forward is minimal; process extracts constraints; summarize increases drift pressure.",
    )
    parser.add_argument(
        "--agent-b-modes",
        nargs="+",
        choices=["forward", "process", "summarize"],
        help="Run multiple Agent B instruction modes.",
    )
    parser.add_argument(
        "--hops",
        type=int,
        default=1,
        help="Number of Agent-B-style hops before final Agent C scoring.",
    )
    parser.add_argument(
        "--hops-values",
        nargs="+",
        type=int,
        help="Run multiple hop-count conditions, e.g. --hops-values 1 3 5.",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Run the Cartesian product of models, temperatures, modes, and hop values.",
    )
    parser.add_argument(
        "--judge",
        action="store_true",
        help="Add an LLM-as-judge pass to evaluate whether the final response respects constraints.",
    )
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.hops < 1:
        raise SystemExit("--hops must be at least 1.")
    if args.hops_values and any(hops < 1 for hops in args.hops_values):
        raise SystemExit("--hops-values entries must be at least 1.")

    tasks = select_tasks(args.task)
    if args.dry_run:
        dry_run(tasks)
        return

    if args.batch or args.models or args.agent_b_modes or args.hops_values:
        results = run_batch_conditions(args)
    elif args.temperatures:
        run_started_at_unix = time.time()
        results = {
            "metadata": {
                "model": args.model,
                "api_mode": args.api_mode,
                "temperature_conditions": args.temperatures,
                "trials_per_task": args.trials,
                "agent_b_mode": args.agent_b_mode,
                "hops": args.hops,
                "judge_enabled": args.judge,
                "created_at_unix": run_started_at_unix,
                "created_at_local": local_timestamp(),
            },
            "conditions": [],
        }
        for temperature in args.temperatures:
            print(f"\n=== Temperature condition: {temperature} ===")
            results["conditions"].append(
                {
                    "temperature": temperature,
                    "results": run_temperature_condition(args, temperature),
                }
            )
        results["condition_summary"] = summarize_conditions(results["conditions"])
        results["metadata"]["completed_at_unix"] = time.time()
        results["metadata"]["completed_at_local"] = local_timestamp()
    else:
        results = run_temperature_condition(args, args.temperature)

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "real_llm_results.json"
    raw_output_path = output_dir / "raw_api_calls.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    raw_output_path.write_text(
        json.dumps(collect_api_calls(results), indent=2), encoding="utf-8"
    )

    print("\nSummary")
    if "summary" in results:
        print(json.dumps(results["summary"], indent=2))
    else:
        print(json.dumps(results["condition_summary"], indent=2))
    print(f"\nSaved: {output_path}")
    print(f"Raw API calls: {raw_output_path}")


if __name__ == "__main__":
    main()
