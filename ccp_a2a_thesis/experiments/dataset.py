"""Experiment dataset management"""
from typing import List, Dict
from core.task import TaskManager, Task

class ExperimentDataset:
    """Manages the experimental dataset"""
    
    def __init__(self):
        self.tasks = TaskManager.get_all_tasks()
        self.current_task_index = 0
    
    def get_task_by_category(self, category: str) -> Task:
        """Get task by category"""
        for task in self.tasks:
            if task.category == category:
                return task
        raise ValueError(f"Task not found for category: {category}")
    
    def get_all_tasks(self) -> List[Task]:
        """Return all tasks"""
        return self.tasks
    
    def get_task_count(self) -> int:
        """Return number of tasks"""
        return len(self.tasks)
    
    def get_summary(self) -> Dict:
        """Get dataset summary"""
        categories = [task.category for task in self.tasks]
        return {
            "total_tasks": len(self.tasks),
            "categories": categories,
            "constraint_types": list(set(
                key for task in self.tasks 
                for key in task.constraints.keys()
            ))
        }