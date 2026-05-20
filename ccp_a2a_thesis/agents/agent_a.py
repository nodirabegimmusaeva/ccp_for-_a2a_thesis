
from typing import Dict, Any
from .base_agent import BaseAgent
from protocols.text_protocol import TextBuilder
from protocols.ccp_protocol import CCPBuilder

class AgentA(BaseAgent):
    """First agent that receives user request and formats it for next agent"""
    
    def __init__(self, agent_id: str = "A", name: str = "Request Processor"):
        super().__init__(agent_id, name)
        self.text_builder = TextBuilder()
        self.ccp_builder = CCPBuilder()
    
    def process(self, task: Dict[str, Any], protocol: str = "text") -> Any:
        """
        Process initial user task into appropriate protocol format
        
        Args:
            task: Task dictionary with 'request' and 'constraints'
            protocol: "text" or "ccp"
        
        Returns:
            Formatted output for Agent B
        """
        if protocol == "text":
            output = self.text_builder.build(task)
        else:  # ccp
            output = self.ccp_builder.build(task, self.agent_id)
        
        self.log_interaction(task, output, {"protocol": protocol})
        return output