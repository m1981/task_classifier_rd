from dataclasses import dataclass, field
from typing import List, Optional
from pydantic import BaseModel, Field

# --- CONFIGURATION ---
@dataclass(frozen=True)
class SystemConfig:
    """Central configuration for domain logic"""
    DEFAULT_TAGS: List[str] = field(default_factory=lambda: [
        "physical", "digital",
        "out", "need-material", "need-tools", "buy"
    ])

# --- DOMAIN ENTITIES (Internal Use) ---
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
    suggested_project: str = Field(...)
    confidence: float = Field(...)
    reasoning: str = Field(...)
    extracted_tags: List[str] = Field(...)
# --- AI MODELS (External/Validation Use) ---

# This MUST be a Pydantic BaseModel to work with Anthropic Structured Outputs
class ClassificationResult(BaseModel):
    suggested_project: str = Field(
        description="The exact name of the best matching project from the available list, or 'Unmatched' if none fit well."
    )
    confidence: float = Field(
        description="A confidence score between 0.0 and 1.0 indicating how certain the classification is."
    )
    reasoning: str = Field(
        description="A brief explanation (max 15 words) of why this project was chosen."
    )
    extracted_tags: List[str] = Field(
        default_factory=list,
        description="A list of relevant tags from the allowed tags list."
    )
    # Optional fields that might not always be present
    estimated_duration: Optional[str] = Field(
        default=None,
        description="An estimated duration string (e.g., '15min', '1h') if inferable."
    )
    alternative_projects: List[str] = Field(
        default_factory=list,
        description="Other projects that might be a close second match."
    )
    # We add this field to hold the input text, but exclude it from the AI generation
    # because the AI doesn't need to generate the text we just sent it.
    task: str = Field(
        default="",
        description="The original task text (internal use only)"
    )

    # --- NEW FIELD ---
    suggested_new_project_name: Optional[str] = Field(
        default=None,
        description="If the task does not fit ANY available project, suggest a short, concise name for a NEW project here."
    )

# --- SERVICE OBJECTS ---

@dataclass
class ClassificationRequest:
    """Batch request object"""
    dataset: DatasetContent
    prompt_variant: str = "basic"

@dataclass
class ClassificationResponse:
    """Standardized response wrapper"""
    results: List[ClassificationResult]
    prompt_used: str
    raw_response: str