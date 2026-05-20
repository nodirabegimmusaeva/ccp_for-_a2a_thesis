
from typing import Dict, Any

class TextBuilder:
    """Builds natural language text from tasks"""
    
    def build(self, task: Dict[str, Any]) -> str:
        """
        Convert task to natural language text
        
        Args:
            task: Task with 'request' and 'constraints' fields
        
        Returns:
            Natural language string
        """
        request = task.get("request", "")
        constraints = task.get("constraints", {})
        
        text_parts = [f"User request: {request}"]
        
        # Add constraints as natural language
        if constraints.get("diet"):
            text_parts.append(f"Dietary restriction: {constraints['diet']}")
        if constraints.get("allergy"):
            text_parts.append(f"Allergy: {constraints['allergy']}")
        if constraints.get("seat"):
            text_parts.append(f"Seat preference: {constraints['seat']}")
        if constraints.get("injury"):
            text_parts.append(f"Injury: {constraints['injury']}")
        if constraints.get("purpose"):
            text_parts.append(f"Purpose: {constraints['purpose']}")
        if constraints.get("interest"):
            text_parts.append(f"Interest: {constraints['interest']}")
        
        return " | ".join(text_parts)