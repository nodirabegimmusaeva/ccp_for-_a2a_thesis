"""Metrics calculation for experiment evaluation"""
from typing import Dict, List, Any
import numpy as np

class MetricsCalculator:
    """Calculate and aggregate experiment metrics"""
    
    def __init__(self):
        self.results = []
    
    def calculate_context_retention_score(
        self, 
        original_constraints: Dict[str, str], 
        final_output: Dict[str, Any]
    ) -> float:
        """
        Calculate Context Retention Score (CRS)
        
        Returns:
            Score between 0.0 and 1.0
        """
        if not original_constraints:
            return 1.0
        
        detected = final_output.get("detected_constraints", {})
        
        preserved = 0
        for constraint_key, constraint_value in original_constraints.items():
            # Map constraint keys to detection keys
            detection_key = self._map_constraint_key(constraint_key)
            if detection_key and detected.get(detection_key, False):
                preserved += 1
        
        return preserved / len(original_constraints) if original_constraints else 1.0
    
    def calculate_accuracy(
        self, 
        final_output: Dict[str, Any], 
        original_constraints: Dict[str, str]
    ) -> bool:
        """
        Calculate if task was completed successfully
        
        Returns:
            True if all critical constraints are satisfied
        """
        detected = final_output.get("detected_constraints", {})
        
        # Critical constraints must be preserved
        for constraint_key in original_constraints.keys():
            detection_key = self._map_constraint_key(constraint_key)
            if detection_key and not detected.get(detection_key, False):
                # Check if it's a safety-critical constraint
                if constraint_key in ["allergy", "injury"]:
                    return False  # Safety violation
                # For non-critical, check response warnings
                response = final_output.get("response", "")
                if "⚠️ Warning" in response:
                    return False
        
        return True
    
    def _map_constraint_key(self, key: str) -> str:
        """Map constraint key to detection key"""
        mapping = {
            "diet": "vegetarian",
            "allergy": "peanut_allergy",
            "seat": "window_seat",
            "injury": "knee_injury",
            "purpose": "gaming",
            "interest": "food_interest"
        }
        return mapping.get(key, key)
    
    def aggregate_results(self, trial_results: List[Dict]) -> Dict:
        """Aggregate results across trials"""
        if not trial_results:
            return {}
        
        text_accuracies = []
        ccp_accuracies = []
        text_crs = []
        ccp_crs = []
        
        for task_result in trial_results:
            for trial in task_result.get("trials", []):
                text_accuracies.append(trial["text"]["accuracy"])
                ccp_accuracies.append(trial["ccp"]["accuracy"])
                text_crs.append(trial["text"]["crs"])
                ccp_crs.append(trial["ccp"]["crs"])
        
        if not text_accuracies:
            return {}
        
        return {
            "text": {
                "mean_accuracy": np.mean(text_accuracies),
                "std_accuracy": np.std(text_accuracies),
                "mean_crs": np.mean(text_crs),
                "std_crs": np.std(text_crs),
                "total_trials": len(text_accuracies)
            },
            "ccp": {
                "mean_accuracy": np.mean(ccp_accuracies),
                "std_accuracy": np.std(ccp_accuracies),
                "mean_crs": np.mean(ccp_crs),
                "std_crs": np.std(ccp_crs),
                "total_trials": len(ccp_accuracies)
            }
        }