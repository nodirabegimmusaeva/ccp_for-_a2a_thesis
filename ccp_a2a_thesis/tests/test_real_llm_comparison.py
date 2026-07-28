"""Regression tests for the real LLM comparison harness."""

from __future__ import annotations

import unittest

from core.task import TaskManager
from real_llm_comparison.experiment import RealLLMComparison
from real_llm_comparison.metrics import (
    aggregate_results,
    calculate_context_retention_score,
)


class MalformedJsonClient:
    model = "fake-model"
    api_mode = "responses"
    temperature = 1.0
    api_call_log = []

    def complete_json_with_text(self, system, user, call_label=None):
        return None, '{"bad": "json\nwith broken " quote"}', "Expecting delimiter"


class RealLLMComparisonRegressionTests(unittest.TestCase):
    def test_ccp_hop_preserves_previous_payload_when_model_json_is_malformed(self):
        task = TaskManager.get_all_tasks()[0]
        previous_payload = {
            "task_id": task.task_id,
            "context": {"user": "test"},
            "constraints": {"allergy": "peanut allergy"},
            "metadata": {"source": "test"},
        }
        runner = RealLLMComparison(
            MalformedJsonClient(),
            trials=1,
            sleep_seconds=0,
            agent_b_mode="forward",
            hops=1,
            judge=False,
        )

        normalized, raw = runner._agent_b_forward(
            task, "ccp", previous_payload, hop_index=0, trial=0
        )

        self.assertEqual(normalized["task_id"], task.task_id)
        self.assertEqual(normalized["constraints"], previous_payload["constraints"])
        self.assertIn("parse_error", raw)
        self.assertEqual(normalized["state_lineage"][0]["agent_id"], "B1")

    def test_agent_c_malformed_json_becomes_parse_error_result(self):
        task = TaskManager.get_all_tasks()[0]
        runner = RealLLMComparison(
            MalformedJsonClient(),
            trials=1,
            sleep_seconds=0,
            agent_b_mode="forward",
            hops=1,
            judge=False,
        )

        result = runner._agent_c_decide(task, "text", "previous message", trial=0)

        self.assertIn("parse_error", result)
        self.assertEqual(result["protocol"], "text")
        self.assertFalse(any(result["detected_constraints"].values()))

    def test_context_retention_uses_detected_constraint_mapping(self):
        score = calculate_context_retention_score(
            {"allergy": "peanut allergy", "diet": "vegetarian"},
            {
                "detected_constraints": {
                    "peanut_allergy": True,
                    "vegetarian": False,
                }
            },
        )

        self.assertEqual(score, 0.5)

    def test_aggregate_results_counts_hard_violations(self):
        summary = aggregate_results(
            [
                {
                    "task_id": "001",
                    "category": "Food",
                    "trials": [
                        {
                            "text": {
                                "accuracy": False,
                                "crs": 0.5,
                                "deterministic_violations": ["allergy"],
                            },
                            "ccp": {
                                "accuracy": True,
                                "crs": 1.0,
                                "deterministic_violations": [],
                            },
                        }
                    ],
                }
            ]
        )

        self.assertEqual(summary["text"]["hard_violation_trials"], 1)
        self.assertEqual(summary["ccp"]["hard_violation_trials"], 0)
        self.assertEqual(summary["text"]["total_trials"], 1)


if __name__ == "__main__":
    unittest.main()
