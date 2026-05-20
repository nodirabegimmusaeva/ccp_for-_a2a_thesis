"""Schema validation for CCP auditability"""
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class CCPValidator:
    """Validates CCP payload structure at each agent hop"""
    
    REQUIRED_FIELDS = ["task_id", "agent_id", "timestamp", "context", "state_lineage"]
    
    @classmethod
    def validate(cls, payload: Dict) -> Tuple[bool, List[str]]:
        """
        Validate CCP payload structure
        
        Returns:
            (is_valid, violations_list)
        """
        violations = []
        
        # Check required fields
        for field in cls.REQUIRED_FIELDS:
            if field not in payload:
                violations.append(f"Missing required field: {field}")
        
        # Validate state lineage
        if "state_lineage" in payload:
            lineage = payload["state_lineage"]
            if not isinstance(lineage, list):
                violations.append("state_lineage must be a list")
            elif len(lineage) == 0:
                violations.append("state_lineage cannot be empty")
        
        # Validate timestamp format
        if "timestamp" in payload:
            try:
                datetime.fromisoformat(payload["timestamp"])
            except:
                violations.append("Invalid timestamp format")
        
        # Validate invariants vs preferences
        if "extended_context" in payload:
            for ext in payload["extended_context"]:
                if ext.get("criticality") == "invariant" and not ext.get("value"):
                    violations.append(f"Invariant {ext.get('key')} has no value")
        
        return len(violations) == 0, violations
    
    @classmethod
    def add_agent_to_lineage(cls, payload: Dict, agent_id: str) -> Dict:
        """Append agent to state lineage for tracking"""
        payload = payload.copy()
        
        if "state_lineage" not in payload:
            payload["state_lineage"] = []
        
        payload["state_lineage"].append({
            "agent_id": agent_id,
            "timestamp": datetime.now().isoformat(),
            "action": "processed"
        })
        
        return payload