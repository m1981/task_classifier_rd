from typing import List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum
from dataclasses import dataclass
from models.entities import SystemConfig

class ClassificationType(str, Enum):
    TASK = "task"
    SHOPPING = "resource"
    REFERENCE = "reference"
    NEW_PROJECT = "new_project"
    INCUBATE = "incubate"

class ClassificationResult(BaseModel):
    # --- CHAIN OF THOUGHT ---
    reasoning: str = Field(
        description="Step-by-step analysis of the item against GTD rules and the Project Hierarchy."
    )

    # --- THE DECISION ---
    classification_type: ClassificationType = Field(
        description="The category of the item based on the reasoning above."
    )
    suggested_project: str = Field(
        description=(
            "The exact name of the best matching EXISTING project. "
            "If the item is a Reference or Incubate and no project fits, use 'General'. "
            "Only use 'Unmatched' if it is a TASK that requires a NEW project."
        )
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )

    # --- METADATA ---
    extracted_tags: List[str] = Field(
        default_factory=list,
        description="Select tags STRICTLY from the 'AVAILABLE TAGS' list provided in the prompt context."
    )
    refined_text: str = Field(
        description="Cleaned up title. Try extract the page title. MUST be translated into clear, concise English"
    )
    suggested_new_project_name: Optional[str] = Field(
        default=None,
        description="Required ONLY if suggested_project is 'Unmatched'. Suggest a concise name."
    )
    estimated_duration: Optional[str] = Field(
        default=None,
        description=(
            f"Strictly one of: {SystemConfig.ALLOWED_DURATIONS}. "
            "MUST be null if classification_type is 'reference' or 'incubate'."
        )
    )
    alternative_projects: List[str] = Field(
        default_factory=list,
        description="Identify exactly 3 other existing projects from the context that could be valid destinations."
    )

    notes: str = Field(
        default="",
        description="If the input contains a URL, YOU MUST COPY THE FULL URL HERE. Then add your summary/context."
    )

# --- SERVICE OBJECTS ---

@dataclass
class ClassificationRequest:
    dataset: Any

@dataclass
class ClassificationResponse:
    results: List[ClassificationResult]
    prompt_used: str
    tool_schema: dict
    raw_response: str

class SmartFilterResult(BaseModel):
    matching_task_ids: List[str] = Field(
        description="The exact IDs of the tasks that fit the user's query constraints."
    )
    reasoning: str = Field(
        description="A brief explanation of why these tasks were selected."
    )
    estimated_total_time: str = Field(
        description="A rough sum of the duration of selected tasks."
    )

class EnrichmentResult(BaseModel):
    extracted_tags: List[str] = Field(
        description="Select tags STRICTLY from the 'AVAILABLE TAGS' list provided in the prompt context."
    )
    estimated_duration: Optional[str] = Field(
        description=f"Strictly one of: {SystemConfig.ALLOWED_DURATIONS}. Null if not a task."
    )
    notes: str = Field(
        default="",
        description="Add context, URL (if in title), or sub-steps. Keep empty if simple."
    )
    suggested_kind: ClassificationType = Field(
        description="Is this actually a Resource (Buy) or Reference? If so, suggest change."
    )