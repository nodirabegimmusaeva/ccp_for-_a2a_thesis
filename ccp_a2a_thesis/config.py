

# Assumed drift probabilities by constraint type; not calibrated to real workflows
CONSTRAINT_DRIFT_PROBS = {
    # Safety-critical (low drift)
    "allergy": 0.12,
    "injury": 0.15,
    
    # Preference-based (medium drift)
    "diet": 0.25,
    "seat": 0.28,
    
    # Nice-to-have (high drift)
    "purpose": 0.35,
    "interest": 0.38,
}

# Semantic variations for text drift simulation
# IMPORTANT: Keys must match possible constraint values
SEMANTIC_VARIATIONS = {
    "vegetarian": ["vegetarian", "veg meal", "no meat", "plant-based", "doesn't eat meat"],
    "peanut allergy": ["allergic to peanuts", "peanut allergy", "no peanuts", "can't have peanuts", "peanut-free"],
    "peanuts": ["peanuts", "peanut", "groundnuts"],  # Added for allergy value
    "window": ["window seat", "seat by window", "prefer window", "want to see outside"],
    "window seat": ["window seat", "seat by window", "prefer window", "want to see outside"],
    "knee pain": ["knee injury", "bad knee", "knee pain", "injured knee", "can't strain knee"],
    "knee injury": ["knee injury", "bad knee", "knee pain", "injured knee", "can't strain knee"],
    "gaming": ["gaming", "for games", "game development", "high GPU", "gaming laptop"],
    "food": ["food tourism", "local cuisine", "food experiences", "culinary interest"],
}

# Experiment parameters
NUM_TRIALS = 100
CCP_DRIFT_ENABLED = True
CCP_DRIFT_RATE = 0.15
CCP_DRIFT_PROBABILITY = CCP_DRIFT_RATE
SEED = 42  # For reproducibility

# Structured protocol failure model. Probabilities are absolute per-trial
# rates and intentionally sum to CCP_DRIFT_PROBABILITY.
CCP_FAILURE_MODES = {
    "constraint_value_alteration": 0.04,
    "constraint_omission": 0.03,
    "constraint_type_mismatch": 0.02,
    "schema_validation_failure": 0.02,
    "field_type_error": 0.02,
    "lineage_corruption": 0.01,
    "timestamp_error": 0.01,
}
assert abs(sum(CCP_FAILURE_MODES.values()) - CCP_DRIFT_PROBABILITY) < 1e-9

# Canonical synonyms used by the text-protocol baseline matcher. This keeps
# the baseline fair by detecting literal and common paraphrased constraint
# values, including Travel's interest=food case.
CONSTRAINT_SYNONYMS = {
    "vegetarian": ["vegetarian", "plant-based", "veggie", "no meat", "meat-free", "meatless"],
    "peanut allergy": ["peanut allergy", "peanut", "allergy to peanuts", "allergic to peanuts", "nut allergy", "peanut-free", "no peanuts"],
    "window seat": ["window seat", "window", "by the window", "window side", "window seating", "seat by window"],
    "knee pain": ["knee pain", "knee injury", "knee", "bad knee", "hurt knee", "knee problem"],
    "gaming": ["gaming", "for gaming", "gaming laptop", "play games", "plays games", "game"],
    "food": ["food", "food interest", "interest food", "foodie", "culinary", "restaurant", "local food", "local cuisine"],
}

# Task categories
TASK_CATEGORIES = ["Food", "Flight", "Workout", "Laptop", "Travel"]

# Output directories
RESULTS_DIR = "results"
LOGS_DIR = "logs"
PLOTS_DIR = "plots"
