from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime, date

# --- DOMAIN CONFIGURATION (NEW) ---
class DomainType(str, Enum):
    SOFTWARE = "software"
    MAKER = "maker"      # Renovation, 3D Printing, Carpentry
    LIFESTYLE = "lifestyle" # Family, Health, Travel
    BUSINESS = "business"

# Configuration for each domain
DOMAIN_CONFIGS = {
    DomainType.SOFTWARE: [
        "Frontend", "Backend", "DevOps", "Bug", "Feature", "Refactor",
        "Python", "React", "Database", "Architecture", "API", "Testing",
        "@Computer", "Mental-Deep", "HighEnergy"
    ],
    DomainType.MAKER: [
        "Design", "Assembly", "Finishing", "Shopping",
        "Wood", "Electronics", "3D-Print", "Painting",
        "Measurements", "Safety", "@Garage", "Physical-Heavy"
    ],
    DomainType.LIFESTYLE: [
        "Errands", "Phone", "Email", "Finance", "Health",
        "Kids", "Social", "Travel", "Reading", "Household",
        "@Home", "@Anywhere", "LowEnergy"
    ],
    DomainType.BUSINESS: [
        "Strategy",  # For MVP Validation / Roadmap
        "Marketing",  # General promotion
        "Content",  # Writing posts, recording videos
        "Sales",  # Commercialization
        "Outreach",  # Finding partners/Co-founders
        "Hiring",  # Specifically for the Co-Founder search
        "Finance",  # Budgeting, Pricing
        "Legal",  # Contracts, Incorporation
        "Research",  # Competitor analysis
        "Admin",  # Taxes, paperwork
        "@Meeting",  # Calls with candidates/partners
        "@Computer",
        "HighEnergy",  # Sales/Pitching usually requires this
        "Mental-Deep"  # Strategy work
    ]
}
# --- SYSTEM CONFIGURATION ---
class SystemConfig:
    """Central configuration for domain logic"""

    # Static Lists (Durations)
    ALLOWED_DURATIONS: List[str] = ["5min", "15min", "30min", "1h", "2h", "4h", "1d"]

    # Default fallback tags (Legacy support)
    DEFAULT_TAGS: List[str] = DOMAIN_CONFIGS[DomainType.LIFESTYLE]

# --- ENUMS ---
class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"

class GoalStatus(str, Enum):
    ACTIVE = "active"
    SOMEDAY = "someday"

class ResourceType(str, Enum):
    TO_BUY = "to_buy"
    TO_GATHER = "to_gather"

# --- ABSTRACT BASE & CONCRETE ITEMS ---

class ProjectItem(BaseModel):
    """The Abstract Base Class for all things inside a project"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    notes: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)

class TaskItem(ProjectItem):
    kind: Literal["task"] = "task"
    is_completed: bool = False
    duration: str = "unknown"
    completed_at: Optional[datetime] = None
    due_date: Optional[date] = None


class ResourceItem(ProjectItem):
    kind: Literal["resource"] = "resource"
    type: ResourceType = ResourceType.TO_BUY
    is_acquired: bool = False
    store: str = "General"
    link: Optional[str] = None

class ReferenceItem(ProjectItem):
    kind: Literal["reference"] = "reference"
    content: str = ""

# --- DEFINING THE POLYMORPHIC TYPE ---
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
    # NEW: Optional domain override (defaults to Lifestyle if not set)
    domain: DomainType = DomainType.LIFESTYLE
    sort_order: float = Field(default=0.0)
    tags: List[str] = Field(default_factory=list)
    items: List[ProjectItemUnion] = Field(default_factory=list)

class Goal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    status: GoalStatus = GoalStatus.ACTIVE
    # NEW: Goal level domain
    domain: DomainType = DomainType.LIFESTYLE

class DatasetContent(BaseModel):
    goals: List[Goal] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    inbox_tasks: List[str] = Field(default_factory=list)

# --- REBUILD MODELS ---
Project.model_rebuild()
DatasetContent.model_rebuild()