# models/ai_schemas.py
from typing import List, Optional, Any
from pydantic import BaseModel, Field
from dataclasses import dataclass

# --- AI MODELS (Pydantic) ---

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
    estimated_duration: Optional[str] = Field(
        default=None,
        description="An estimated duration string (e.g., '15min', '1h') if inferable."
    )
    alternative_projects: List[str] = Field(
        default_factory=list,
        description="Other projects that might be a close second match."
    )
    # Internal use field
    task: str = Field(
        default="",
        description="The original task text (internal use only)"
    )
    suggested_new_project_name: Optional[str] = Field(
        default=None,
        description="If the task does not fit ANY available project, suggest a short, concise name for a NEW project here."
    )

# --- SERVICE OBJECTS (Dataclasses) ---

@dataclass
class ClassificationRequest:
    """
    Batch request object.
    Note: We use Any for dataset to avoid circular imports with entities.py
    if this file is imported there. Ideally, pass specific lists, not the whole dataset object.
    """
    dataset: Any
    prompt_variant: str = "basic"

@dataclass
class ClassificationResponse:
    """Standardized response wrapper"""
    results: List[ClassificationResult]
    prompt_used: str
    raw_response: str