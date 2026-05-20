

# Drift probabilities by constraint type (realistic)
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
NUM_TRIALS = 50
CCP_DRIFT_RATE = 0.08  # 8% drift rate for CCP (realistic)
SEED = 42  # For reproducibility

# Task categories
TASK_CATEGORIES = ["Food", "Flight", "Workout", "Laptop", "Travel"]

# Output directories
RESULTS_DIR = "results"
LOGS_DIR = "logs"
PLOTS_DIR = "plots"