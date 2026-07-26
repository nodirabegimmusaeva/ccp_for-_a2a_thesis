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
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    def complete_json(self, system: str, user: str) -> Dict[str, Any]:
        text = self.complete_text(system, user)
        return self._parse_json(text)

    def complete_text(self, system: str, user: str) -> str:
        if self.api_mode == "responses":
            payload = {
                "model": self.model,
                "instructions": system,
                "input": user,
            }
            if self.temperature is not None:
                payload["temperature"] = self.temperature
            response = self._post("/responses", payload)
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
        response = self._post("/chat/completions", payload)
        return response["choices"][0]["message"]["content"]

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
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
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"API request failed ({exc.code}): {detail}") from exc

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
    def __init__(self, client: LLMClient, trials: int, sleep_seconds: float) -> None:
        self.client = client
        self.trials = trials
        self.sleep_seconds = sleep_seconds
        self.agent_a = AgentA()

    def run(self, tasks: List[Task]) -> Dict[str, Any]:
        task_results = []
        for task in tasks:
            print(f"\nTask {task.task_id}: {task.category}")
            trials = []
            for trial in range(self.trials):
                print(f"  trial {trial + 1}/{self.trials}: text", end="", flush=True)
                text_result = self._run_protocol(task, "text")
                self._pause()
                print(", ccp", end="", flush=True)
                ccp_result = self._run_protocol(task, "ccp")
                print(" done")
                trials.append({"trial": trial, "text": text_result, "ccp": ccp_result})
                self._pause()
            task_results.append(
                {"task_id": task.task_id, "category": task.category, "trials": trials}
            )

        summary = aggregate_results(task_results)
        return {
            "metadata": {
                "model": self.client.model,
                "api_mode": self.client.api_mode,
                "trials_per_task": self.trials,
                "created_at_unix": time.time(),
            },
            "summary": summary,
            "tasks": task_results,
        }

    def _run_protocol(self, task: Task, protocol: str) -> Dict[str, Any]:
        agent_a_output = self.agent_a.process(task.to_dict(), protocol=protocol)
        forwarded = self._agent_b_forward(task, protocol, agent_a_output)
        final_output = self._agent_c_decide(protocol, forwarded)
        return {
            "accuracy": calculate_accuracy(final_output, task.constraints),
            "crs": calculate_context_retention_score(task.constraints, final_output),
            "agent_a_output": agent_a_output,
            "agent_b_output": forwarded,
            "final_output": final_output,
        }

    def _agent_b_forward(self, task: Task, protocol: str, payload: Any) -> Any:
        if protocol == "text":
            return self.client.complete_text(
                system=(
                    "You are Agent B in a three-agent workflow. Forward the user's "
                    "request to Agent C as concise natural language. Do not add new "
                    "facts. Preserve any safety constraints, preferences, and task "
                    "requirements that you believe are relevant."
                ),
                user=f"Original task category: {task.category}\nMessage from Agent A:\n{payload}",
            )

        return self.client.complete_json(
            system=(
                "You are Agent B in a three-agent workflow. You receive a Canonical "
                "Context Payload JSON object and must forward valid JSON only. Keep "
                "the same schema when possible. Do not add new facts. Preserve "
                "context, extended_context, constraints, request, metadata, and "
                "state_lineage. Append a lineage entry for agent B."
            ),
            user=json.dumps(payload, indent=2),
        )

    def _agent_c_decide(self, protocol: str, payload: Any) -> Dict[str, Any]:
        payload_text = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
        result = self.client.complete_json(
            system=(
                "You are Agent C, the final decision maker. Inspect the message from "
                "Agent B and return JSON only with exactly these top-level keys: "
                "response, detected_constraints, protocol. detected_constraints must "
                "contain booleans for vegetarian, peanut_allergy, window_seat, "
                "knee_injury, gaming, food_interest. Mark a constraint true only if "
                "the Agent B message preserves that meaning. The response should be "
                "a short final recommendation or warning based only on detected data."
            ),
            user=f"Protocol: {protocol}\nMessage from Agent B:\n{payload_text}",
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


def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def std(values: List[float]) -> float:
    if not values:
        return 0.0
    avg = mean(values)
    return (sum((value - avg) ** 2 for value in values) / len(values)) ** 0.5


def aggregate_results(task_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    text_accuracies: List[float] = []
    ccp_accuracies: List[float] = []
    text_crs: List[float] = []
    ccp_crs: List[float] = []

    for task_result in task_results:
        for trial in task_result.get("trials", []):
            text_accuracies.append(float(trial["text"]["accuracy"]))
            ccp_accuracies.append(float(trial["ccp"]["accuracy"]))
            text_crs.append(float(trial["text"]["crs"]))
            ccp_crs.append(float(trial["ccp"]["crs"]))

    return {
        "text": {
            "mean_accuracy": mean(text_accuracies),
            "std_accuracy": std(text_accuracies),
            "mean_crs": mean(text_crs),
            "std_crs": std(text_crs),
            "total_trials": len(text_accuracies),
        },
        "ccp": {
            "mean_accuracy": mean(ccp_accuracies),
            "std_accuracy": std(ccp_accuracies),
            "mean_crs": mean(ccp_crs),
            "std_crs": std(ccp_crs),
            "total_trials": len(ccp_accuracies),
        },
    }


def dry_run(tasks: List[Task]) -> None:
    agent_a = AgentA()
    for task in tasks:
        print(f"\n=== {task.category} ===")
        print("Text payload:")
        print(agent_a.process(task.to_dict(), protocol="text"))
        print("\nCCP payload:")
        print(json.dumps(agent_a.process(task.to_dict(), protocol="ccp"), indent=2))


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
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--sleep", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    tasks = select_tasks(args.task)
    if args.dry_run:
        dry_run(tasks)
        return

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set OPENAI_API_KEY or run with --dry-run.")

    client = LLMClient(
        api_key=api_key,
        model=args.model,
        base_url=args.base_url,
        api_mode=args.api_mode,
        temperature=args.temperature,
        timeout=args.timeout,
    )
    results = RealLLMComparison(client, trials=args.trials, sleep_seconds=args.sleep).run(tasks)

    output_dir = Path(__file__).resolve().parent / "results"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "real_llm_results.json"
    output_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("\nSummary")
    print(json.dumps(results["summary"], indent=2))
    print(f"\nSaved: {output_path}")


if __name__ == "__main__":
    main()
