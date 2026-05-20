"""Main experiment runner"""
from typing import Dict, List, Any
import random
from tqdm import tqdm
from agents import AgentA, AgentB, AgentC
from core.metrics import MetricsCalculator
from core.validator import OutputValidator
from experiments.dataset import ExperimentDataset
from config import NUM_TRIALS, SEED

class ExperimentRunner:
    """Orchestrates the entire experiment"""
    
    def __init__(self):
        random.seed(SEED)
        self.dataset = ExperimentDataset()
        self.metrics = MetricsCalculator()
        self.validator = OutputValidator()
        self.results = []
    
    def run_full_experiment(self) -> Dict:
        """Run complete experiment across all tasks and trials"""
        print("=" * 60)
        print("Starting CCP vs Text Protocol Experiment")
        print("=" * 60)
        
        tasks = self.dataset.get_all_tasks()
        
        for task in tqdm(tasks, desc="Processing tasks"):
            print(f"\n📋 Task: {task.category} (ID: {task.task_id})")
            
            task_results = {
                "task_id": task.task_id,
                "category": task.category,
                "trials": []
            }
            
            for trial in range(NUM_TRIALS):
                trial_result = self.run_single_trial(task, trial)
                task_results["trials"].append(trial_result)
            
            self.results.append(task_results)
            
            # Print intermediate results
            self._print_task_summary(task_results)
        
        return self.metrics.aggregate_results(self.results)
    
    def run_single_trial(self, task, trial_num: int) -> Dict:
        """Run single trial for both protocols"""
        
        # Text protocol
        text_result = self._run_text_protocol(task)
        
        # CCP protocol
        ccp_result = self._run_ccp_protocol(task)
        
        return {
            "trial": trial_num,
            "text": text_result,
            "ccp": ccp_result
        }
    
    def _run_text_protocol(self, task) -> Dict:
        """Execute text-based communication"""
        # Initialize agents
        agent_a = AgentA()
        agent_b = AgentB(drift_mode="realistic")
        agent_c = AgentC()
        
        # Process through agents
        agent_a_output = agent_a.process(task.to_dict(), protocol="text")
        agent_b_output = agent_b.process(
            agent_a_output, 
            protocol="text",
            original_constraints=task.constraints
        )
        agent_c_output = agent_c.process(agent_b_output, protocol="text")
        
        # Calculate metrics
        crs = self.metrics.calculate_context_retention_score(
            task.constraints, 
            agent_c_output
        )
        accuracy = self.metrics.calculate_accuracy(
            agent_c_output, 
            task.constraints
        )
        is_safe, violations = self.validator.validate_safety(agent_c_output)
        
        return {
            "accuracy": accuracy,
            "crs": crs,
            "is_safe": is_safe,
            "violations": violations,
            "final_output": agent_c_output,
            "drift_report": agent_b.get_drift_stats()
        }
    
    def _run_ccp_protocol(self, task) -> Dict:
        """Execute CCP-based communication"""
        agent_a = AgentA()
        agent_b = AgentB(drift_mode="realistic")
        agent_c = AgentC()
        
        agent_a_output = agent_a.process(task.to_dict(), protocol="ccp")
        agent_b_output = agent_b.process(
            agent_a_output, 
            protocol="ccp",
            original_constraints=task.constraints
        )
        agent_c_output = agent_c.process(agent_b_output, protocol="ccp")
        
        crs = self.metrics.calculate_context_retention_score(
            task.constraints, 
            agent_c_output
        )
        accuracy = self.metrics.calculate_accuracy(
            agent_c_output, 
            task.constraints
        )
        is_safe, violations = self.validator.validate_safety(agent_c_output)
        
        return {
            "accuracy": accuracy,
            "crs": crs,
            "is_safe": is_safe,
            "violations": violations,
            "final_output": agent_c_output,
            "drift_report": agent_b.get_drift_stats()
        }
    
    def _print_task_summary(self, task_results: Dict):
        """Print summary for a task"""
        if not task_results["trials"]:
            return
            
        text_acc = [t["text"]["accuracy"] for t in task_results["trials"]]
        ccp_acc = [t["ccp"]["accuracy"] for t in task_results["trials"]]
        text_crs = [t["text"]["crs"] for t in task_results["trials"]]
        ccp_crs = [t["ccp"]["crs"] for t in task_results["trials"]]
        
        print(f"  📊 Text Protocol  - Accuracy: {sum(text_acc)/len(text_acc):.1%}, CRS: {sum(text_crs)/len(text_crs):.3f}")
        print(f"  📊 CCP Protocol   - Accuracy: {sum(ccp_acc)/len(ccp_acc):.1%}, CRS: {sum(ccp_crs)/len(ccp_crs):.3f}")
        print(f"  📈 Improvement    - Accuracy: +{(sum(ccp_acc)-sum(text_acc))/len(text_acc):.1%}")