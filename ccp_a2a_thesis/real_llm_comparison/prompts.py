"""Prompt constants for the real LLM comparison harness."""

from __future__ import annotations

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
