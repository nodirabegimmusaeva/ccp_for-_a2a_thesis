
from typing import Any, Dict, Optional, Union
from .base_agent import BaseAgent
from protocols.drift_simulator import TextDriftSimulator, CCPDriftSimulator

class AgentB(BaseAgent):
    """Middle agent that introduces context drift based on protocol"""
    
    def __init__(
        self, 
        agent_id: str = "B", 
        name: str = "Context Forwarder",
        drift_mode: str = "realistic"
    ):
        super().__init__(agent_id, name)
        self.drift_mode = drift_mode
        self.text_drift = TextDriftSimulator(drift_mode)
        self.ccp_drift = CCPDriftSimulator()
        self.current_constraints = {}
    
    def process(
        self, 
        input_data: Union[str, Dict], 
        protocol: str = "text",
        original_constraints: Optional[Dict] = None
    ) -> Any:
        """
        Process input with appropriate drift simulation
        
        Args:
            input_data: Text string or CCP dictionary
            protocol: "text" or "ccp"
            original_constraints: Original constraints for drift tracking
        
        Returns:
            Processed output (potentially with drift)
        """
        self.current_constraints = original_constraints or {}
        
        if protocol == "text":
            output, drift_report = self.text_drift.process(
                input_data, 
                self.current_constraints
            )
        else:  # ccp
            output, drift_report = self.ccp_drift.process(input_data)
        
        self.log_interaction(
            input_data, 
            output, 
            {"protocol": protocol, "drift": drift_report}
        )
        
        return output
    
    def get_drift_stats(self) -> Dict:
        """Return drift statistics"""
        return {
            "text_drift": self.text_drift.get_drift_statistics(),
            "ccp_drift": self.ccp_drift.get_drift_statistics()
        }