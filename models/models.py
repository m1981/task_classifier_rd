from dataclasses import dataclass, field
from typing import List, Optional

# --- NEW CONFIGURATION CLASS ---
@dataclass(frozen=True)
class SystemConfig:
    """Central configuration for domain logic"""
    DEFAULT_TAGS: List[str] = field(default_factory=lambda: [
        "physical", "digital",
        "out", "need-material", "need-tools", "buy"
    ])

@dataclass
class Task:
    id: int
    name: str
    duration: str = "unknown"
    tags: List[str] = field(default_factory=list)
    notes: str = ""

@dataclass 
class Project:
    id: int
    name: str
    status: str = "ongoing"
    tags: List[str] = field(default_factory=list)
    tasks: List[Task] = field(default_factory=list)

@dataclass
class DatasetContent:
    projects: List[Project]
    inbox_tasks: List[str]

@dataclass
class ClassificationResult:
    task: str
    suggested_project: str
    confidence: float
    extracted_tags: List[str] = field(default_factory=list)
    estimated_duration: Optional[str] = None
    reasoning: str = ""
    alternative_projects: List[str] = field(default_factory=list)

@dataclass
class ClassificationRequest:
    dataset: DatasetContent
    prompt_variant: str = "basic"

@dataclass
class ClassificationResponse:
    results: List[ClassificationResult]
    prompt_used: str
    raw_response: str