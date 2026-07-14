"""Fuzzy semantic matching for text protocol to ensure fair comparison"""
from typing import Dict, List, Set
import re

try:
    from config import CONSTRAINT_SYNONYMS
except ImportError:
    CONSTRAINT_SYNONYMS = {
        "vegetarian": ["vegetarian", "plant-based", "veggie", "no meat", "meat-free", "meatless"],
        "peanut allergy": ["peanut allergy", "peanut", "allergy to peanuts", "allergic to peanuts", "nut allergy", "peanut-free", "no peanuts"],
        "window seat": ["window seat", "window", "by the window", "window side", "window seating", "seat by window"],
        "knee pain": ["knee pain", "knee injury", "knee", "bad knee", "hurt knee", "knee problem"],
        "gaming": ["gaming", "for gaming", "gaming laptop", "play games", "plays games", "game"],
        "food": ["food", "food interest", "interest food", "foodie", "culinary", "restaurant", "local food", "local cuisine"],
    }

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
            "culinary interest", "food exploration", "gastronomy",
            "food", "interest food", "food interest", "foodie",
            "culinary", "restaurant", "local food"
        }
    }

    DETECTION_TO_CANONICAL_VALUE = {
        "vegetarian": "vegetarian",
        "peanut_allergy": "peanut allergy",
        "window_seat": "window seat",
        "knee_injury": "knee pain",
        "gaming": "gaming",
        "food_interest": "food",
    }

    @staticmethod
    def normalize_constraint_value(constraint_type: str, value: str) -> str:
        """
        Normalize extracted constraint values to canonical experiment values.

        This is intentionally small and auditable: each mapping corresponds to
        a constraint type in the experimental dataset.
        """
        value_lower = value.lower().strip()

        if constraint_type == "interest":
            return {
                "food": "food",
                "food_interest": "food",
                "culinary": "food",
                "foodie": "food",
                "local food": "food",
                "local cuisine": "food",
                "restaurant": "food",
            }.get(value_lower, value)

        if constraint_type == "diet":
            return {
                "vegetarian": "vegetarian",
                "veggie": "vegetarian",
                "plant-based": "vegetarian",
                "no meat": "vegetarian",
                "meat-free": "vegetarian",
                "meatless": "vegetarian",
            }.get(value_lower, value)

        return value
    
    @classmethod
    def detect_constraint(cls, text: str, constraint_type: str) -> bool:
        """Detect constraint using semantic matching, not exact strings"""
        text_lower = text.lower()
        
        if constraint_type not in cls.SEMANTIC_SETS:
            return False
        
        phrases = set(cls.SEMANTIC_SETS[constraint_type])
        canonical_value = cls.DETECTION_TO_CANONICAL_VALUE.get(constraint_type)
        if canonical_value:
            phrases.update(CONSTRAINT_SYNONYMS.get(canonical_value, [canonical_value]))

        for phrase in phrases:
            if phrase in text_lower:
                return True
        
        return False

    @classmethod
    def detect_constraints(cls, text: str, expected_constraints: Dict[str, str]) -> Dict[str, str]:
        """
        Detect expected constraints in free text and return canonical values.

        Args:
            text: Text to search.
            expected_constraints: Mapping of constraint type to canonical value.

        Returns:
            Mapping of constraint type to the detected canonical value, or None.
        """
        detected = {}
        text_lower = text.lower()

        for constraint_type, expected_value in expected_constraints.items():
            detected_value = None
            synonyms = CONSTRAINT_SYNONYMS.get(expected_value, [expected_value])

            for synonym in synonyms:
                if synonym.lower() in text_lower:
                    detected_value = expected_value
                    break

            if constraint_type == "interest" and not detected_value:
                for word in re.findall(r"\b[\w-]+\b", text_lower):
                    normalized = cls.normalize_constraint_value("interest", word)
                    if normalized == expected_value:
                        detected_value = expected_value
                        break

            detected[constraint_type] = detected_value

        return detected
    
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
