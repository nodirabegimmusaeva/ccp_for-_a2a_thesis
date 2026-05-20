
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseAgent(ABC):
    """Base agent with common functionality"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.history = []
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input and return output"""
        pass
    
    def log_interaction(self, input_data: Any, output_data: Any, metadata: Optional[Dict] = None):
        """Log agent interaction for audit trail"""
        self.history.append({
            "agent_id": self.agent_id,
            "input": input_data,
            "output": output_data,
            "metadata": metadata or {}
        })
    
    def get_history(self):
        """Return interaction history"""
        return self.history