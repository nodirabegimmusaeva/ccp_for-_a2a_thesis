"""Fuzzy semantic matching for text protocol to ensure fair comparison"""
from typing import Dict, List, Set
import re

class FuzzyConstraintMatcher:
    """Semantic-aware matcher that prevents strawman bias"""
    
    # Semantic synonym sets for fair comparison
    SEMANTIC_SETS = {
        "vegetarian": {
            "vegetarian", "veg meal", "plant-based", "meatless", 
            "no meat", "veggie", "herbivore", "meat-free"
        },
        "peanut_allergy": {
            "peanut allergy", "allergic to peanuts", "no peanuts", 
            "peanut-free", "cannot eat peanuts", "anaphylaxis peanuts"
        },
        "window_seat": {
            "window seat", "seat by window", "prefer window", 
            "want to see outside", "window side"
        },
        "knee_injury": {
            "knee injury", "bad knee", "knee pain", "injured knee",
            "knee problems", "weak knee", "knee condition"
        },
        "gaming": {
            "gaming", "for games", "game development", "high gpu",
            "plays games", "gaming laptop", "gaming purpose"
        },
        "food_interest": {
            "food tourism", "local cuisine", "food experiences",
            "culinary interest", "food exploration", "gastronomy"
        }
    }
    
    @classmethod
    def detect_constraint(cls, text: str, constraint_type: str) -> bool:
        """Detect constraint using semantic matching, not exact strings"""
        text_lower = text.lower()
        
        if constraint_type not in cls.SEMANTIC_SETS:
            return False
        
        for phrase in cls.SEMANTIC_SETS[constraint_type]:
            if phrase in text_lower:
                return True
        
        return False
    
    @classmethod
    def extract_all_constraints(cls, text: str) -> Dict[str, bool]:
        """Extract all constraints using semantic matching"""
        return {
            "vegetarian": cls.detect_constraint(text, "vegetarian"),
            "peanut_allergy": cls.detect_constraint(text, "peanut_allergy"),
            "window_seat": cls.detect_constraint(text, "window_seat"),
            "knee_injury": cls.detect_constraint(text, "knee_injury"),
            "gaming": cls.detect_constraint(text, "gaming"),
            "food_interest": cls.detect_constraint(text, "food_interest")
        }