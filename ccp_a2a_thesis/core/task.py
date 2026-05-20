"""Task definitions and management"""
from typing import Dict, List, Any
import uuid
from dataclasses import dataclass, field

@dataclass
class Task:
    """Represents a single task in the experiment"""
    task_id: str
    category: str
    request: str
    constraints: Dict[str, str]  # Ensure values are strings, not lists
    priority: str = "normal"
    
    def __post_init__(self):
        """Ensure all constraint values are strings"""
        for key, value in self.constraints.items():
            if isinstance(value, list):
                self.constraints[key] = value[0] if value else ""
            elif not isinstance(value, str):
                self.constraints[key] = str(value)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "category": self.category,
            "request": self.request,
            "constraints": self.constraints,
            "priority": self.priority
        }

class TaskManager:
    """Manages task creation and retrieval"""
    
    @staticmethod
    def create_food_task() -> Task:
        return Task(
            task_id="001",
            category="Food",
            request="Recommend a dinner recipe",
            constraints={
                "diet": "vegetarian",
                "allergy": "peanut allergy"  # String, not list
            }
        )
    
    @staticmethod
    def create_flight_task() -> Task:
        return Task(
            task_id="002",
            category="Flight",
            request="Book a flight seat",
            constraints={
                "seat": "window seat"  # String
            }
        )
    
    @staticmethod
    def create_workout_task() -> Task:
        return Task(
            task_id="003",
            category="Workout",
            request="Plan a workout routine",
            constraints={
                "injury": "knee pain"  # String
            }
        )
    
    @staticmethod
    def create_laptop_task() -> Task:
        return Task(
            task_id="004",
            category="Laptop",
            request="Recommend a laptop",
            constraints={
                "purpose": "gaming"  # String
            }
        )
    
    @staticmethod
    def create_travel_task() -> Task:
        return Task(
            task_id="005",
            category="Travel",
            request="Plan a travel itinerary",
            constraints={
                "interest": "food"  # String
            }
        )
    
    @classmethod
    def get_all_tasks(cls) -> List[Task]:
        """Return all tasks"""
        return [
            cls.create_food_task(),
            cls.create_flight_task(),
            cls.create_workout_task(),
            cls.create_laptop_task(),
            cls.create_travel_task()
        ]