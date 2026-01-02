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
    # --- CHAIN OF THOUGHT (Moved to Top) ---
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
        description=f"Select tags STRICTLY from this list: {SystemConfig.DEFAULT_TAGS}"
    )
    refined_text: str = Field(
        description="Cleaned up title. For URLs, extract the page title."
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
        description="Identify exactly 3 other existing projects from the context that could be valid destinations, sorted by relevance. If fewer than 3 make sense, list as many as possible."
    )

    notes: Optional[str] = Field(
        default="",
        description="Summary, context, or URL description. Empty string if none."
    )

# --- SERVICE OBJECTS ---

@dataclass
class ClassificationRequest:
    """Batch request object (Legacy/Future use)"""
    dataset: Any

@dataclass
class ClassificationResponse:
    """Standardized response wrapper used by TaskClassifier"""
    results: List[ClassificationResult]
    prompt_used: str
    tool_schema: dict
    raw_response: str

class SmartFilterResult(BaseModel):
    """
    The AI's response to a 'Smart Context' query.
    It returns the IDs of tasks that fit the user's constraints.
    """
    matching_task_ids: List[str] = Field(
        description="The exact IDs of the tasks that fit the user's query constraints."
    )
    reasoning: str = Field(
        description="A brief explanation of why these tasks were selected (e.g., 'These tasks are short and computer-based')."
    )
    estimated_total_time: str = Field(
        description="A rough sum of the duration of selected tasks (e.g., '45 mins')."
    )