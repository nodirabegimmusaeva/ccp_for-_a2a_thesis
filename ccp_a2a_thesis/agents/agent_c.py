from typing import Dict, Any, List
from .base_agent import BaseAgent
from protocols.fuzzy_matcher import FuzzyConstraintMatcher

class AgentC(BaseAgent):
    """Final agent that produces output and validates constraints"""
    
    def __init__(self, agent_id: str = "C", name: str = "Decision Maker"):
        super().__init__(agent_id, name)
    
    def process(self, input_data: Any, protocol: str = "text") -> Dict[str, Any]:
        """
        Generate final output based on input and protocol
        
        Args:
            input_data: Text string or CCP dictionary
            protocol: "text" or "ccp"
        
        Returns:
            Dictionary with output and validation results
        """
        if protocol == "text":
            output = self._process_text(input_data)
        else:
            output = self._process_ccp(input_data)
        
        self.log_interaction(input_data, output, {"protocol": protocol})
        return output
    
    def _process_text(self, text: str) -> Dict[str, Any]:
        """Process unstructured text input with semantic matching"""
        # Use fuzzy semantic matching instead of rigid keywords
        detected = FuzzyConstraintMatcher.extract_all_constraints(text)
        
        response = self._generate_response(detected, "text")
        
        return {
            "response": response,
            "detected_constraints": detected,
            "protocol": "text",
            "semantic_matching_used": True  # Flag for fairness
        }
    
    
        """Process structured CCP input"""
        # Handle different possible payload structures
        if isinstance(payload, str):
            # Try to parse as JSON
            import json
            try:
                payload = json.loads(payload)
            except:
                return self._process_text(payload)
        
        # Extract constraints from different possible locations
        detected = {
            "vegetarian": False,
            "peanut_allergy": False,
            "window_seat": False,
            "knee_injury": False,
            "gaming": False,
            "food_interest": False
        }
        
        # Check context field
        context = payload.get("context", {})
        if isinstance(context, dict):
            # Diet constraint
            diet = context.get("diet", "")
            if isinstance(diet, str) and "vegetarian" in diet.lower():
                detected["vegetarian"] = True
            
            # Allergy constraint
            allergy = context.get("allergy", "")
            if isinstance(allergy, str):
                if "peanut" in allergy.lower() or "nut" in allergy.lower():
                    detected["peanut_allergy"] = True
            elif isinstance(allergy, list):
                for a in allergy:
                    if "peanut" in str(a).lower():
                        detected["peanut_allergy"] = True
                        break
            
            # Seat preference
            seat = context.get("seat", "")
            if isinstance(seat, str) and "window" in seat.lower():
                detected["window_seat"] = True
            
            # Injury
            injury = context.get("injury", "")
            if isinstance(injury, str) and ("knee" in injury.lower() or "pain" in injury.lower()):
                detected["knee_injury"] = True
            
            # Purpose
            purpose = context.get("purpose", "")
            if isinstance(purpose, str) and ("game" in purpose.lower() or "gaming" in purpose.lower()):
                detected["gaming"] = True
            
            # Interest
            interest = context.get("interest", "")
            if isinstance(interest, str) and ("food" in interest.lower() or "cuisine" in interest.lower()):
                detected["food_interest"] = True
        
        # Also check constraints list
        constraints = payload.get("constraints", [])
        if isinstance(constraints, list):
            for constraint in constraints:
                constraint_lower = str(constraint).lower()
                if "vegetarian" in constraint_lower:
                    detected["vegetarian"] = True
                if "peanut" in constraint_lower or "nut" in constraint_lower:
                    detected["peanut_allergy"] = True
                if "window" in constraint_lower and "seat" in constraint_lower:
                    detected["window_seat"] = True
                if "knee" in constraint_lower:
                    detected["knee_injury"] = True
                if "game" in constraint_lower:
                    detected["gaming"] = True
                if "food" in constraint_lower:
                    detected["food_interest"] = True
        
        # Also check the request field
        request = payload.get("request", "")
        if isinstance(request, str):
            request_lower = request.lower()
            if "vegetarian" in request_lower:
                detected["vegetarian"] = True
            if "peanut" in request_lower:
                detected["peanut_allergy"] = True
            if "window" in request_lower and "seat" in request_lower:
                detected["window_seat"] = True
        
        response = self._generate_response(detected, "ccp")
        
        return {
            "response": response,
            "detected_constraints": detected,
            "protocol": "ccp",
            "original_payload": payload
        }
    
    def _generate_response(self, detected: Dict, protocol: str) -> str:
        """Generate final response based on detected constraints"""
        # Check for safety-critical constraints first
        if detected.get("peanut_allergy") and detected.get("vegetarian"):
            return "✅ Valid: Vegetarian peanut-free pasta with roasted vegetables"
        elif detected.get("peanut_allergy"):
            if protocol == "text":
                return "⚠️ Warning: Peanut allergy detected but vegetarian constraint not verified - please confirm dietary requirements"
            else:
                return "⚠️ Warning: Peanut allergy noted - vegetarian constraint missing from structured data"
        elif detected.get("vegetarian"):
            if protocol == "text":
                return "⚠️ Warning: Vegetarian preference noted but allergy information missing - please verify safety"
            else:
                return "⚠️ Warning: Vegetarian diet noted - allergy information not in structured payload"
        
        # Non-critical constraints
        if detected.get("window_seat"):
            return "✅ Seat preference noted: Window seat assigned"
        elif detected.get("knee_injury"):
            return "✅ Modified workout: Low-impact exercises recommended (swimming, cycling, upper body focus)"
        elif detected.get("gaming"):
            return "✅ Gaming laptop: RTX 4060 GPU, 16GB RAM, 144Hz display recommended"
        elif detected.get("food_interest"):
            return "✅ Food tour: Local cuisine recommendations included (street food tour, cooking class)"
        else:
            return "⚠️ Warning: No constraints detected in communication - please verify all requirements"