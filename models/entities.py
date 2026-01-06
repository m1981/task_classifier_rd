from typing import List, Optional, Union, Literal, Annotated
from pydantic import BaseModel, Field
from enum import Enum
import uuid
from datetime import datetime, date


# --- TAG KNOWLEDGE BASE (NEW SOURCE OF TRUTH) ---
class TagDefinition(BaseModel):
    tag: str
    state: str
    example: str


class TagKnowledgeBase:
    """
    Defines the Cognitive Tagging System.
    Used to generate prompts for AI and validation lists for Pydantic.
    """

    # 1. COMPUTER (Deep Logic & Creative)
    COMPUTER = [
        TagDefinition(tag="@Maker-Code", state="🧠 Logic & Syntax", example="Fix stream error, Refactor API"),
        TagDefinition(tag="@Maker-Creative", state="🎨 Visual & Story", example="Draft Pitch Deck, Design UI"),
        TagDefinition(tag="@Outreach", state="🗣️ Social & Sales",
                      example="Message LinkedIn prospects, Reply to emails"),
        TagDefinition(tag="@Analytical", state="📊 Data & Money", example="Update Budget Excel, Analyze Metrics"),
        TagDefinition(tag="@Research", state="👀 Passive Input", example="Watch Tutorial, Read Documentation"),
    ]

    # 2. WORKSHOP (Physical & Focused)
    WORKSHOP = [
        TagDefinition(tag="@Heavy-Duty", state="👷‍♂️ Dirty & Sweaty", example="Paint kitchen, Grout tiles, Plumbing"),
        TagDefinition(tag="@Precision-Bench", state="🔬 Focused & Seated",
                      example="Solder electronics, Assemble 3D Printer"),
        TagDefinition(tag="@Quick-Fix", state="🔧 Casual & Fast", example="Tighten screw, Glue strip, Oil hinge"),
        TagDefinition(tag="@Logistics", state="📏 Measuring & Planning", example="Measure wall, Count screws needed"),
    ]

    # 3. FAMILY (Roles)
    FAMILY = [
        TagDefinition(tag="@Family-Admin", state="📋 Logistics Manager", example="Pay school fees, Book dentist"),
        TagDefinition(tag="@Kids-Growth", state="🌱 Patient Coach", example="Teach math, Explain emotions"),
        TagDefinition(tag="@Quality-Time", state="❤️ Phone Off", example="Board games, Walk in park"),
    ]

    # 4. HOBBY (Growth)
    HOBBY = [
        TagDefinition(tag="@Skill-Up", state="🎓 Learning", example="Practice guitar scales, Duolingo"),
        TagDefinition(tag="@Play-Mode", state="🎮 Enjoying", example="Gaming, Free riding"),
    ]

    # 5. LEGACY / ESSENTIALS (To ensure we don't break basic GTD flows)
    ESSENTIALS = [
        TagDefinition(tag="@Errands", state="🚗 Out & About", example="Post office, Shopping"),
        TagDefinition(tag="@Buy", state="🛒 Resource/Shopping", example="Buy Milk, Order parts"),
        TagDefinition(tag="@WaitingFor", state="⏳ Blocked", example="Waiting for reply"),
    ]

    @classmethod
    def get_all_definitions(cls) -> List[TagDefinition]:
        return cls.COMPUTER + cls.WORKSHOP + cls.FAMILY + cls.HOBBY + cls.ESSENTIALS

    @classmethod
    def get_all_tags(cls) -> List[str]:
        return [t.tag for t in cls.get_all_definitions()]

    @classmethod
    def get_markdown_table(cls) -> str:
        """Generates the Markdown table for the AI Prompt"""
        rows = []
        rows.append("| Tag | Cognitive/Physical State | Example Task |")
        rows.append("|---|---|---|")

        for group_name, items in [
            ("COMPUTER", cls.COMPUTER),
            ("WORKSHOP", cls.WORKSHOP),
            ("FAMILY", cls.FAMILY),
            ("HOBBY", cls.HOBBY),
            ("ESSENTIALS", cls.ESSENTIALS)
        ]:
            for item in items:
                rows.append(f"| `{item.tag}` | {item.state} | {item.example} |")

        return "\n".join(rows)


# --- SYSTEM CONFIGURATION ---
class SystemConfig:
    """Central configuration for domain logic"""

    # Static Lists (Durations)
    ALLOWED_DURATIONS: List[str] = ["5min", "15min", "30min", "1h", "2h", "4h", "1d"]

    # Default fallback tags
    DEFAULT_TAGS: List[str] = TagKnowledgeBase.get_all_tags()

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
    cost_estimate: Optional[float] = None
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
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    status: ProjectStatus = ProjectStatus.ACTIVE
    goal_id: Optional[str] = None
    sort_order: float = Field(default=0.0)
    tags: List[str] = Field(default_factory=list)
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


# --- REBUILD MODELS ---
Project.model_rebuild()
DatasetContent.model_rebuild()