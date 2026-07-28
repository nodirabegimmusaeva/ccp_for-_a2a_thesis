"""Experiment runner for CCP vs unstructured text real LLM trials."""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

from agents.agent_a import AgentA
from core.task import Task

from real_llm_comparison.llm_client import LLMClient
from real_llm_comparison.metrics import aggregate_results, calculate_accuracy, calculate_context_retention_score, detect_response_violations, local_timestamp
from real_llm_comparison.prompts import AGENT_C_PROMPT, CCP_FORWARD_PROMPT, CCP_PROCESS_PROMPT, CCP_SUMMARIZE_PROMPT, DETECTION_KEYS, JUDGE_PROMPT, TEXT_FORWARD_PROMPT, TEXT_PROCESS_PROMPT, TEXT_SUMMARIZE_PROMPT

class RealLLMComparison:
    def __init__(
        self,
        client: LLMClient,
        trials: int,
        sleep_seconds: float,
        agent_b_mode: str,
        hops: int,
        judge: bool,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.client = client
        self.trials = trials
        self.sleep_seconds = sleep_seconds
        self.agent_b_mode = agent_b_mode
        self.hops = hops
        self.judge = judge
        self.progress_callback = progress_callback
        self.agent_a = AgentA()

    def run(self, tasks: List[Task]) -> Dict[str, Any]:
        run_started_at_unix = time.time()
        run_started_at_local = local_timestamp()
        task_results = []
        result = {
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
                "prompts": self._prompt_manifest(),
            },
            "summary": aggregate_results(task_results),
            "tasks": task_results,
            "api_calls": self.client.api_call_log,
        }
        for task in tasks:
            print(f"\nTask {task.task_id}: {task.category}")
            task_result = {"task_id": task.task_id, "category": task.category, "trials": []}
            task_results.append(task_result)
            for trial in range(self.trials):
                print(f"  trial {trial + 1}/{self.trials}: text", end="", flush=True)
                text_result = self._run_protocol(task, "text", trial)
                self._pause()
                print(", ccp", end="", flush=True)
                ccp_result = self._run_protocol(task, "ccp", trial)
                print(" done")
                task_result["trials"].append(
                    {"trial": trial, "text": text_result, "ccp": ccp_result}
                )
                result["summary"] = aggregate_results(task_results)
                result["metadata"]["last_checkpoint_at_unix"] = time.time()
                result["metadata"]["last_checkpoint_at_local"] = local_timestamp()
                result["api_calls"] = self.client.api_call_log
                if self.progress_callback is not None:
                    self.progress_callback(result)
                self._pause()

        summary = aggregate_results(task_results)
        run_completed_at_unix = time.time()
        result["summary"] = summary
        result["metadata"]["completed_at_unix"] = run_completed_at_unix
        result["metadata"]["completed_at_local"] = local_timestamp()
        result["api_calls"] = self.client.api_call_log
        if self.progress_callback is not None:
            self.progress_callback(result)
        return result

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

        raw_output, raw_text, parse_error = self.client.complete_json_with_text(
            system=system_prompt,
            user=(
                f"Current agent: {hop_label}\n"
                f"Original task category: {task.category}\n"
                f"Payload from previous agent:\n{json.dumps(payload, indent=2)}"
            ),
            call_label=call_label,
        )
        if raw_output is None:
            raw_output = {
                "parse_error": parse_error,
                "raw_model_output": raw_text,
                "processing_notes": (
                    "Model returned malformed JSON. The harness preserved the "
                    "previous valid CCP payload for downstream evaluation."
                ),
            }
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
        result, raw_text, parse_error = self.client.complete_json_with_text(
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
        if result is None:
            return {
                "response": raw_text,
                "detected_constraints": dict(DETECTION_KEYS),
                "protocol": protocol,
                "parse_error": parse_error,
                "raw_agent_c_output": raw_text,
            }
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
        result, raw_text, parse_error = self.client.complete_json_with_text(
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
        if result is None:
            return {
                "violations": ["judge_parse_error"],
                "contradictions": [],
                "completion_issues": ["judge returned malformed JSON"],
                "score": 0.0,
                "notes": "Judge output could not be parsed as JSON.",
                "parse_error": parse_error,
                "raw_judge_output": raw_text,
            }
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
