"""Canonical Context Payload (CCP) protocol"""
from typing import Dict, Any, List, Optional
import json
from datetime import datetime

class CCPBuilder:
    """Builds structured CCP payloads"""
    
    def build(self, task: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """
        Convert task to structured CCP payload
        
        Args:
            task: Task with 'request', 'constraints', and optional 'task_id'
            agent_id: Current agent identifier
        
        Returns:
            Structured JSON payload
        """
        constraints = task.get("constraints", {})
        
        # Ensure constraints values are properly formatted
        formatted_context = {}
        for key, value in constraints.items():
            if isinstance(value, list):
                formatted_context[key] = value[0] if value else ""
            else:
                formatted_context[key] = str(value)
        
        return {
            "task_id": str(task.get("task_id", "unknown")),
            "agent_id": str(agent_id),
            "timestamp": datetime.now().isoformat(),
            "context": formatted_context,
            "request": str(task.get("request", "")),
            "constraints": self._extract_constraint_list(formatted_context),
            "metadata": {
                "version": "1.0",
                "priority": task.get("priority", "normal"),
                "trace_id": f"trace_{task.get('task_id', 'unknown')}"
            }
        }
    
    def _extract_constraint_list(self, constraints: Dict) -> List[str]:
        """Convert constraint dict to list format"""
        constraint_list = []
        for key, value in constraints.items():
            if value:
                constraint_list.append(f"{key}: {value}")
        return constraint_list

class CCPValidator:
    """Validates CCP payload structure"""
    
    @staticmethod
    def validate(payload: Dict) -> tuple[bool, Optional[str]]:
        """
        Validate CCP payload structure
        
        Returns:
            (is_valid, error_message)
        """
        required_fields = ["task_id", "agent_id", "context", "request"]
        
        for field in required_fields:
            if field not in payload:
                return False, f"Missing required field: {field}"
        
        if not isinstance(payload.get("context"), dict):
            return False, "Context must be a dictionary"
        
        return True, None
    
    @staticmethod
    def format_for_logging(payload: Dict) -> str:
        """Format payload for readable logging"""
        return json.dumps(payload, indent=2)