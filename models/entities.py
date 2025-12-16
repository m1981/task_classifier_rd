from dataclasses import dataclass, field
from typing import List, Optional, NewType
from enum import Enum
from datetime import date
import uuid

# --- CONFIGURATION (Moved from models.py) ---
@dataclass(frozen=True)
class SystemConfig:
    """Central configuration for domain logic"""
    DEFAULT_TAGS: List[str] = field(default_factory=lambda: [
        "physical", "digital",
        "out", "need-material", "need-tools", "buy"
    ])

# --- TYPE ALIASES ---
GoalID = NewType("GoalID", str)
ProjectID = NewType("ProjectID", int)
TaskID = NewType("TaskID", str)

# --- ENUMS ---
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"

class ResourceType(str, Enum):
    TO_BUY = "to_buy"
    TO_GATHER = "to_gather"

# --- DOMAIN ENTITIES ---

@dataclass
class ProjectResource:
    """Replaces ShoppingItem to handle both Shopping and Prep"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    link: Optional[str] = None
    type: ResourceType = ResourceType.TO_BUY
    is_acquired: bool = False
    store: str = "General"

@dataclass
class ReferenceItem:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

@dataclass
class Task:
    name: str
    id: TaskID = field(default_factory=lambda: str(uuid.uuid4()))
    is_completed: bool = False
    tags: List[str] = field(default_factory=list)
    deadline: Optional[date] = None
    duration: str = "unknown"
    notes: str = ""

@dataclass
class Project:
    id: ProjectID
    name: str
    description: str = ""
    goal_id: Optional[GoalID] = None
    status: ProjectStatus = ProjectStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)
    resources: List[ProjectResource] = field(default_factory=list)
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