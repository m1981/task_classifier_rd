from dataclasses import dataclass, field
from typing import List, Optional, NewType
from enum import Enum
from datetime import date
import uuid

# Type Aliases for clarity
GoalID = NewType("GoalID", str)
ProjectID = NewType("ProjectID", int)
TaskID = NewType("TaskID", int)


class ProjectStatus(Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"

class ResourceType(Enum):
    TO_BUY = "to_buy"
    TO_GATHER = "to_gather"

@dataclass
class ProjectResource:
    """Replaces ShoppingItem to handle both Shopping and Prep"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    link: Optional[str] = None
    type: ResourceType = ResourceType.TO_BUY
    is_acquired: bool = False
    store: str = "General"  # Added for the Shopping View

@dataclass
class ReferenceItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""


@dataclass
class Task:
    id: TaskID
    name: str
    is_completed: bool = False
    tags: List[str] = field(default_factory=list) # Standardized to 'tags'
    deadline: Optional[date] = None
    duration: str = "unknown" # Kept for backward compatibility
    notes: str = ""

@dataclass
class Project:
    id: ProjectID
    name: str
    description: str = ""
    goal_id: Optional[GoalID] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    tags: List[str] = field(default_factory=list) # Kept for backward compatibility

    # Composition (SRP: Project holds its own data)
    tasks: List[Task] = field(default_factory=list)
    resources: List[ProjectResource] = field(default_factory=list) # Replaces shopping_list
    reference_items: List[ReferenceItem] = field(default_factory=list)


@dataclass
class Goal:
    id: GoalID
    name: str
    description: str = ""
    status: str = "active"

@dataclass
class DatasetContent:
    """The Root Aggregate"""
    projects: List[Project] = field(default_factory=list)
    inbox_tasks: List[str] = field(default_factory=list)
    goals: List[Goal] = field(default_factory=list)