"""Canonical Context Payload (CCP) protocol"""
from typing import Dict, Any, List, Optional, Tuple
import json
from datetime import datetime

class CCPBuilder:
    """Builds structured CCP payloads with extensible context"""
    
    def build(self, task: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        constraints = task.get("constraints", {})
        
        formatted_context = {}
        extended_context = []
        
        for key, value in constraints.items():
            # Handle if value is a list
            if isinstance(value, list):
                value_str = value[0] if value else ""
            else:
                value_str = str(value)
            
            # Known invariant fields go to context
            if key in ["diet", "allergy", "seat", "injury"]:
                formatted_context[key] = value_str
            else:
                # Unknown constraints go to extended_context (open world assumption)
                extended_context.append({
                    "key": key,
                    "value": value_str,
                    "criticality": self._determine_criticality(key, value_str),
                    "provenance": f"agent_{agent_id}"
                })
        
        return {
            "task_id": str(task.get("task_id", "unknown")),
            "agent_id": str(agent_id),
            "timestamp": datetime.now().isoformat(),
            "context": formatted_context,  # Known invariants
            "extended_context": extended_context,  # Open-ended bag
            "request": str(task.get("request", "")),
            "constraints": self._extract_constraint_list(formatted_context),
            "state_lineage": [{  # Track agent history
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat(),
                "action": "initialized"
            }],
            "metadata": {
                "version": "1.1",  # Upgraded for extensibility
                "priority": task.get("priority", "normal"),
                "trace_id": f"trace_{task.get('task_id', 'unknown')}"
            }
        }
    
    def _determine_criticality(self, key: str, value: str) -> str:
        """Determine if constraint is invariant or preference"""
        safety_keywords = ["allergy", "intolerance", "medical", "injury", "safety"]
        if any(kw in key.lower() or kw in value.lower() for kw in safety_keywords):
            return "invariant"  # Cannot be broken
        return "preference"  # Can be optimized/traded
    
    def _extract_constraint_list(self, constraints: Dict) -> List[str]:
        """Convert constraint dict to list format"""
        constraint_list = []
        for key, value in constraints.items():
            if value:
                constraint_list.append(f"{key}: {value}")
        return constraint_list


class CCPValidator:
    """Validates CCP payload structure for auditability"""
    
    REQUIRED_FIELDS = ["task_id", "agent_id", "timestamp", "context", "state_lineage"]
    
    @classmethod
    def validate(cls, payload: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate CCP payload structure
        
        Returns:
            (is_valid, error_message)
        """
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        # Check context is dict
        if not isinstance(payload.get("context"), dict):
            return False, "Context must be a dictionary"
        
        # Check state_lineage is list
        if not isinstance(payload.get("state_lineage"), list):
            return False, "state_lineage must be a list"
        
        # Validate timestamp format
        if "timestamp" in payload:
            try:
                datetime.fromisoformat(payload["timestamp"])
            except (ValueError, TypeError):
                return False, "Invalid timestamp format"
        
        return True, None
    
    @classmethod
    def validate_with_violations(cls, payload: Dict) -> Tuple[bool, List[str]]:
        """
        Validate and return all violations
        
        Returns:
            (is_valid, violations_list)
        """
        violations = []
        
        for field in cls.REQUIRED_FIELDS:
            if field not in payload:
                violations.append(f"Missing required field: {field}")
        
        if "context" in payload and not isinstance(payload["context"], dict):
            violations.append("Context must be a dictionary")
        
        if "state_lineage" in payload and not isinstance(payload["state_lineage"], list):
            violations.append("state_lineage must be a list")
        
        if "extended_context" in payload and isinstance(payload["extended_context"], list):
            for idx, ext in enumerate(payload["extended_context"]):
                if ext.get("criticality") == "invariant" and not ext.get("value"):
                    violations.append(f"Invariant at index {idx} has no value")
        
        return len(violations) == 0, violations
    
    @classmethod
    def add_agent_to_lineage(cls, payload: Dict, agent_id: str, action: str = "processed") -> Dict:
        """Append agent to state lineage for tracking"""
        payload = payload.copy()
        
        if "state_lineage" not in payload:
            payload["state_lineage"] = []
        
        payload["state_lineage"].append({
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "action": action
        })
        
        return payload
    
    @classmethod
    def format_for_logging(cls, payload: Dict) -> str:
        """Format payload for readable logging"""
        return json.dumps(payload, indent=2)