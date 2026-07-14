"""Context drift simulation for both protocols"""
import copy
import random
import logging
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Import from config
try:
    from config import (
        CCP_DRIFT_ENABLED,
        CCP_DRIFT_PROBABILITY,
        CCP_FAILURE_MODES,
        CONSTRAINT_DRIFT_PROBS,
        SEED,
        SEMANTIC_VARIATIONS,
    )
except ImportError:
    # Fallback config if import fails
    CONSTRAINT_DRIFT_PROBS = {
        "allergy": 0.12,
        "injury": 0.15,
        "diet": 0.25,
        "seat": 0.28,
        "purpose": 0.35,
        "interest": 0.38,
    }
    
    SEMANTIC_VARIATIONS = {
        "vegetarian": ["vegetarian", "veg meal", "no meat", "plant-based"],
        "peanut allergy": ["allergic to peanuts", "peanut allergy", "no peanuts"],
        "window seat": ["window seat", "seat by window", "prefer window"],
        "knee pain": ["knee injury", "bad knee", "knee pain"],
        "gaming": ["gaming", "for games", "gaming laptop"],
        "food": ["food tourism", "local cuisine", "food experiences"],
    }
    SEED = 42
    CCP_DRIFT_ENABLED = True
    CCP_DRIFT_PROBABILITY = 0.15
    CCP_FAILURE_MODES = {
        "constraint_value_alteration": 0.04,
        "constraint_omission": 0.03,
        "constraint_type_mismatch": 0.02,
        "schema_validation_failure": 0.02,
        "field_type_error": 0.02,
        "lineage_corruption": 0.01,
        "timestamp_error": 0.01,
    }


class TextDriftSimulator:
    """Simulates realistic context drift in unstructured communication"""
    
    def __init__(self, drift_mode: str = "realistic"):
        """
        Args:
            drift_mode: "realistic", "aggressive", or "none"
        """
        self.drift_mode = drift_mode
        self.drift_log = []
    
    def process(self, message: str, task_constraints: Dict[str, str]) -> Tuple[str, Dict]:
        """Simulate drift in text message"""
        if self.drift_mode == "none":
            return message, {"drift_occurred": False}
        
        processed_msg = message
        drift_events = []
        
        for constraint_type, constraint_value in task_constraints.items():
            drift_prob = CONSTRAINT_DRIFT_PROBS.get(constraint_type, 0.20)
            
            if random.random() < drift_prob:
                # Handle constraint_value if it's a string or list
                if isinstance(constraint_value, list):
                    value_str = constraint_value[0] if constraint_value else ""
                else:
                    value_str = constraint_value
                
                # Try to find matching semantic variations
                removed = False
                
                # Check exact match first
                if value_str in SEMANTIC_VARIATIONS:
                    original_phrases = SEMANTIC_VARIATIONS[value_str]
                else:
                    # Try to find partial match in keys
                    found = False
                    for key in SEMANTIC_VARIATIONS.keys():
                        if key.lower() in value_str.lower() or value_str.lower() in key.lower():
                            original_phrases = SEMANTIC_VARIATIONS[key]
                            found = True
                            break
                    if not found:
                        original_phrases = [value_str]
                
                for phrase in original_phrases:
                    if phrase.lower() in processed_msg.lower():
                        processed_msg = processed_msg.replace(phrase, "")
                        processed_msg = processed_msg.replace(phrase.capitalize(), "")
                        removed = True
                
                if removed:
                    drift_events.append({
                        "constraint_type": constraint_type,
                        "constraint_value": value_str,
                        "drift_probability": drift_prob
                    })
                    
                    if self.drift_mode == "aggressive":
                        processed_msg = self._add_noise(processed_msg)
        
        # Clean up artifacts
        processed_msg = ' '.join(processed_msg.split())
        # Clean up multiple separators
        processed_msg = processed_msg.replace("| |", "|").replace("  ", " ")
        
        drift_report = {
            "drift_occurred": len(drift_events) > 0,
            "drift_events": drift_events,
            "drift_mode": self.drift_mode
        }
        
        self.drift_log.append(drift_report)
        return processed_msg, drift_report
    
    def _add_noise(self, message: str) -> str:
        """Add grammatical artifacts"""
        noise_patterns = [("  ", " "), (", ,", ","), (" .", ".")]
        for old, new in noise_patterns:
            message = message.replace(old, new)
        return message
    
    def get_drift_statistics(self) -> Dict:
        """Calculate drift statistics"""
        if not self.drift_log:
            return {"total_drift_events": 0}
        
        total_events = sum(len(log["drift_events"]) for log in self.drift_log)
        events_by_type = {}
        
        for log in self.drift_log:
            for event in log["drift_events"]:
                ctype = event["constraint_type"]
                events_by_type[ctype] = events_by_type.get(ctype, 0) + 1
        
        return {
            "total_messages": len(self.drift_log),
            "total_drift_events": total_events,
            "avg_events_per_message": total_events / len(self.drift_log) if self.drift_log else 0,
            "events_by_constraint": events_by_type
        }


class CCPDriftSimulator:
    """Simulates realistic structured communication issues."""

    VALUE_ALTERNATIVES = {
        "vegetarian": ["vegan", "plant-based preference"],
        "peanut allergy": ["nut sensitivity", "shellfish allergy"],
        "window seat": ["aisle seat", "exit row"],
        "knee pain": ["back pain", "shoulder pain"],
        "gaming": ["professional work", "software development"],
        "food": ["museum", "architecture"],
    }

    REQUIRED_FIELDS = ["task_id", "agent_id", "request", "context", "extended_context"]

    def __init__(self, drift_rate: float = CCP_DRIFT_PROBABILITY):
        self.drift_rate = drift_rate
        self.drift_log = []

    def process(
        self,
        payload: Dict,
        trial_id: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> Tuple[Dict, Dict]:
        """Simulate reproducible CCP drift in payload fields Agent C reads."""
        rng = self._rng_for_trial(trial_id, task_id)

        if not CCP_DRIFT_ENABLED or rng.random() >= self.drift_rate:
            report = {"drift_occurred": False, "trial_id": trial_id, "task_id": task_id}
            self.drift_log.append(report)
            return payload, report

        processed = copy.deepcopy(payload)
        failure_mode = self._select_failure_mode(rng)
        processed, drift_events = self._apply_failure_mode(processed, failure_mode, rng)

        drift_report = {
            "drift_occurred": True,
            "failure_mode": failure_mode,
            "drift_events": drift_events,
            "trial_id": trial_id,
            "task_id": task_id,
        }

        self.drift_log.append(drift_report)
        return processed, drift_report

    def _rng_for_trial(self, trial_id: Optional[int], task_id: Optional[str]) -> random.Random:
        """Build deterministic RNG so an individual task/trial is reproducible."""
        if trial_id is None:
            return random

        try:
            task_component = int(task_id or 0)
        except (TypeError, ValueError):
            task_component = sum(ord(char) for char in str(task_id))

        return random.Random(SEED + task_component * 10000 + trial_id)

    def _select_failure_mode(self, rng: random.Random) -> str:
        """Select a failure mode using configured absolute probabilities."""
        total = sum(CCP_FAILURE_MODES.values())
        cutoff = rng.random() * total
        cumulative = 0.0

        for mode, probability in CCP_FAILURE_MODES.items():
            cumulative += probability
            if cutoff <= cumulative:
                return mode

        return next(reversed(CCP_FAILURE_MODES))

    def _apply_failure_mode(
        self,
        payload: Dict,
        failure_mode: str,
        rng: random.Random,
    ) -> Tuple[Dict, List[Dict]]:
        """Apply one auditable CCP failure mode."""
        handlers = {
            "constraint_value_alteration": self._alter_constraint_value,
            "constraint_omission": self._omit_constraint,
            "constraint_type_mismatch": self._mismatch_constraint_type,
            "schema_validation_failure": self._break_schema,
            "field_type_error": self._field_type_error,
            "lineage_corruption": self._corrupt_lineage,
            "timestamp_error": self._timestamp_error,
        }
        handler = handlers.get(failure_mode)
        if not handler:
            return payload, [{"type": failure_mode, "description": "Unknown failure mode"}]
        return handler(payload, rng)

    def _iter_constraint_locations(self, payload: Dict) -> List[Dict]:
        """Return constraint locations that Agent C uses for detection."""
        locations = []

        context = payload.get("context", {})
        if isinstance(context, dict):
            for key, value in context.items():
                locations.append({"container": "context", "key": key, "value": value})

        extended_context = payload.get("extended_context", [])
        if isinstance(extended_context, list):
            for index, entry in enumerate(extended_context):
                if isinstance(entry, dict) and entry.get("value"):
                    locations.append({
                        "container": "extended_context",
                        "index": index,
                        "key": entry.get("key"),
                        "value": entry.get("value"),
                    })

        return locations

    def _alter_constraint_value(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        locations = self._iter_constraint_locations(payload)
        if not locations:
            return payload, [{"type": "constraint_value_alteration", "description": "No constraint field available"}]

        location = rng.choice(locations)
        original_value = str(location["value"])
        alternatives = self.VALUE_ALTERNATIVES.get(original_value.lower(), ["unspecified"])
        replacement = rng.choice(alternatives)

        if location["container"] == "context":
            payload["context"][location["key"]] = replacement
            self._refresh_constraint_list(payload)
        else:
            payload["extended_context"][location["index"]]["value"] = replacement

        return payload, [{
            "type": "constraint_value_alteration",
            "field": location["key"],
            "old_value": original_value,
            "new_value": replacement,
        }]

    def _omit_constraint(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        locations = self._iter_constraint_locations(payload)
        if not locations:
            return payload, [{"type": "constraint_omission", "description": "No constraint field available"}]

        location = rng.choice(locations)
        if location["container"] == "context":
            removed = payload["context"].pop(location["key"], None)
            self._refresh_constraint_list(payload)
        else:
            removed = payload["extended_context"].pop(location["index"])

        return payload, [{
            "type": "constraint_omission",
            "field": location["key"],
            "removed": removed,
        }]

    def _mismatch_constraint_type(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        locations = self._iter_constraint_locations(payload)
        if not locations:
            return payload, [{"type": "constraint_type_mismatch", "description": "No constraint field available"}]

        location = rng.choice(locations)
        wrong_key = self._wrong_key_for(location["key"])

        misclassified = payload.setdefault("misclassified_context", [])

        if location["container"] == "context":
            value = payload["context"].pop(location["key"])
            misclassified.append({"key": wrong_key, "value": value})
            self._refresh_constraint_list(payload)
        else:
            entry = payload["extended_context"].pop(location["index"])
            entry["key"] = wrong_key
            misclassified.append(entry)

        return payload, [{
            "type": "constraint_type_mismatch",
            "old_field": location["key"],
            "new_field": wrong_key,
            "value": location["value"],
        }]

    def _break_schema(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        present_required = [field for field in self.REQUIRED_FIELDS if field in payload]
        if not present_required:
            return payload, [{"type": "schema_validation_failure", "description": "No required field available"}]

        if isinstance(payload.get("context"), dict) and payload["context"]:
            field = "context"
        elif isinstance(payload.get("extended_context"), list) and payload["extended_context"]:
            field = "extended_context"
        else:
            field = rng.choice(present_required)
        removed = payload.pop(field)
        if field in {"context", "extended_context"}:
            payload["constraints"] = []
        return payload, [{
            "type": "schema_validation_failure",
            "removed_field": field,
            "removed_value": removed,
        }]

    def _field_type_error(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        if isinstance(payload.get("extended_context"), list) and payload["extended_context"]:
            payload["extended_context"] = str(payload["extended_context"])
            payload["constraints"] = []
            return payload, [{
                "type": "field_type_error",
                "field": "extended_context",
                "description": "List converted to string",
            }]

        if isinstance(payload.get("context"), dict) and payload["context"]:
            payload["context"] = list(payload["context"].items())
            payload["constraints"] = str(payload.get("constraints", []))
            return payload, [{
                "type": "field_type_error",
                "field": "context",
                "description": "Dict converted to list",
            }]

        return payload, [{"type": "field_type_error", "description": "No convertible field available"}]

    def _corrupt_lineage(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        lineage = payload.setdefault("state_lineage", [])
        if isinstance(lineage, list):
            lineage.append({
                "timestamp": "corrupted",
                "agent_id": "error_mode",
                "action": "lineage_corruption",
            })

        return payload, [{
            "type": "lineage_corruption",
            "field": "state_lineage",
        }]

    def _timestamp_error(self, payload: Dict, rng: random.Random) -> Tuple[Dict, List[Dict]]:
        payload["timestamp"] = "INVALID_TIMESTAMP"
        return payload, [{
            "type": "timestamp_error",
            "field": "timestamp",
        }]

    def _refresh_constraint_list(self, payload: Dict) -> None:
        context = payload.get("context", {})
        if not isinstance(context, dict):
            return
        payload["constraints"] = [f"{key}: {value}" for key, value in context.items() if value]

    def _wrong_key_for(self, key: Any) -> str:
        mismatches = {
            "allergy": "diet",
            "diet": "allergy",
            "seat": "purpose",
            "injury": "preference",
            "purpose": "seat",
            "interest": "purpose",
        }
        return mismatches.get(str(key), "miscategorized")
    
    def get_drift_statistics(self) -> Dict:
        """Analyze CCP drift patterns"""
        if not self.drift_log:
            return {"total_processed": 0, "drift_rate": 0}
        
        drifted = len([l for l in self.drift_log if l.get("drift_occurred")])
        return {
            "total_processed": len(self.drift_log),
            "drift_rate": drifted / len(self.drift_log) if self.drift_log else 0,
            "drifted_count": drifted,
            "failure_modes": [l.get("failure_mode") for l in self.drift_log if l.get("drift_occurred")]
        }


# Semantic Mutation Simulator for realistic drift (optional enhancement)
class SemanticMutationSimulator:
    """Simulates realistic semantic mutation instead of random deletion"""
    
    MUTATION_PATTERNS = {
        "vegetarian": [
            ("vegetarian", "meatless"),
            ("vegetarian dinner", "meal without meat"),
            ("strict vegetarian", "vegetarian preferred")
        ],
        "peanut allergy": [
            ("peanut allergy", "nut sensitivity"),
            ("allergic to peanuts", "prefers no peanuts"),
            ("severe peanut allergy", "peanut-free preferred")
        ],
        "window seat": [
            ("window seat", "seat with view"),
            ("prefer window", "like window if available")
        ]
    }
    
    @classmethod
    def mutate(cls, text: str, constraint: str, value: str) -> str:
        """Apply semantic mutation rather than deletion"""
        constraint_lower = constraint.lower()
        if constraint_lower in cls.MUTATION_PATTERNS:
            for original, mutated in cls.MUTATION_PATTERNS[constraint_lower]:
                if original.lower() in text.lower():
                    # Mutate meaning instead of deleting
                    return text.replace(original, mutated)
        
        # Fallback: soften the constraint instead of deleting
        return text.replace(value, f"preferably {value} if possible")
