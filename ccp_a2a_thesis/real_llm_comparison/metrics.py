"""Metrics, summaries, and deterministic checks for real LLM comparison results."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

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
