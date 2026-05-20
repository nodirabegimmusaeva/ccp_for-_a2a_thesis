"""Logging utilities"""
import logging
import json
from datetime import datetime
from pathlib import Path
from config import LOGS_DIR

def setup_logger(name: str, log_file: str = None) -> logging.Logger:
    """Setup logger with file and console handlers"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        Path(LOGS_DIR).mkdir(exist_ok=True)
        file_handler = logging.FileHandler(f"{LOGS_DIR}/{log_file}")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger

class ExperimentLogger:
    """Log experiment results to file"""
    
    def __init__(self, experiment_name: str):
        self.experiment_name = experiment_name
        self.logger = setup_logger(experiment_name, f"{experiment_name}.log")
        self.results = []
    
    def log_trial(self, trial_data: dict):
        """Log a single trial result"""
        self.results.append(trial_data)
        self.logger.info(f"Trial {trial_data.get('trial')}: {trial_data.get('protocol')} - Accuracy: {trial_data.get('accuracy')}")
    
    def save_results(self):
        """Save all results to JSON"""
        output_file = Path(LOGS_DIR) / f"{self.experiment_name}_results.json"
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        self.logger.info(f"Results saved to {output_file}")