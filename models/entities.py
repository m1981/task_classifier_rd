from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime


# --- ENUMS ---
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"


class GoalStatus(str, Enum):
    ACTIVE = "active"
    SOMEDAY = "someday"


# --- ABSTRACT BASE & CONCRETE ITEMS ---

class ProjectItem(BaseModel):
    """The Abstract Base Class for all things inside a project"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.now)
    # The discriminator field must be defined in subclasses


class TaskItem(ProjectItem):
    kind: Literal["task"] = "task"
    is_completed: bool = False
    tags: List[str] = Field(default_factory=list)
    duration: str = "unknown"
    notes: str = ""


class ResourceItem(ProjectItem):
    kind: Literal["resource"] = "resource"
    is_acquired: bool = False
    store: str = "General"
    link: Optional[str] = None


class ReferenceItem(ProjectItem):
    kind: Literal["reference"] = "reference"
    content: str = ""  # URL or Note text

# --- DEFINING THE POLYMORPHIC TYPE ---
# This tells Pydantic: "When you see this Union, look at the 'kind' field to decide which class to use."
ProjectItemUnion = Annotated[
    Union[TaskItem, ResourceItem, ReferenceItem],
    Field(discriminator='kind')
]

# --- CONTAINERS ---

class Project(BaseModel):
    id: int
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    goal_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # THE UNIFIED STREAM
    # We use the Annotated Union here inside the List
    items: List[ProjectItemUnion] = Field(default_factory=list)

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    status: GoalStatus = GoalStatus.ACTIVE


class DatasetContent(BaseModel):
    goals: List[Goal] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    inbox_tasks: List[str] = Field(default_factory=list)