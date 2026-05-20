
import random
import logging
from typing import Dict, List, Tuple, Any, Union
from config import CONSTRAINT_DRIFT_PROBS, SEMANTIC_VARIATIONS

logger = logging.getLogger(__name__)

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
                    # If it's a list, take the first item or join them
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
    """Simulates realistic structured communication issues"""
    
    def __init__(self, drift_rate: float = 0.08):
        self.drift_rate = drift_rate
        self.drift_log = []
    
    def process(self, payload: Dict) -> Tuple[Dict, Dict]:
        """Simulate drift in CCP payload"""
        if random.random() > self.drift_rate:
            return payload, {"drift_occurred": False}
        
        processed = payload.copy()
        drift_events = []
        
        failure_mode = random.choice([
            "schema_mismatch", "constraint_dropped", "field_type_error"
        ])
        
        if failure_mode == "schema_mismatch" and "metadata" in processed:
            del processed["metadata"]
            drift_events.append({"type": "schema_mismatch"})
        
        elif failure_mode == "constraint_dropped" and "constraints" in processed:
            if processed["constraints"]:
                dropped = processed["constraints"].pop(0)
                drift_events.append({"type": "constraint_dropped", "constraint": dropped})
        
        elif failure_mode == "field_type_error" and "context" in processed:
            if isinstance(processed["context"].get("allergy"), str):
                processed["context"]["allergy"] = [processed["context"]["allergy"]]
                drift_events.append({"type": "type_coercion"})
        
        drift_report = {
            "drift_occurred": True,
            "failure_mode": failure_mode,
            "drift_events": drift_events
        }
        
        self.drift_log.append(drift_report)
        return processed, drift_report
    
    def get_drift_statistics(self) -> Dict:
        """Analyze CCP drift patterns"""
        if not self.drift_log:
            return {"total_processed": 0, "drift_rate": 0}
        
        drifted = len([l for l in self.drift_log if l.get("drift_occurred")])
        return {
            "total_processed": len(self.drift_log),
            "drift_rate": drifted / len(self.drift_log) if self.drift_log else 0,
            "drifted_count": drifted
        }