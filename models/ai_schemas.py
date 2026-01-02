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
        description="First, think step-by-step about the item. Analyze the user's intent, the context hierarchy, and the GTD rules. Explain why it fits a specific type and project."
    )

    # --- THE DECISION ---
    classification_type: ClassificationType = Field(
        description="The category of the item based on the reasoning above."
    )
    suggested_project: str = Field(
        description="The exact name of the best matching project, or 'Unmatched' if none fit."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )

    # --- METADATA ---
    extracted_tags: List[str] = Field(
        default_factory=list,
        description="Relevant tags from the allowed list."
    )
    refined_text: str = Field(
        description="A cleaned-up version of the task text (e.g., removing 'I need to buy' from 'I need to buy milk')."
    )
    suggested_new_project_name: Optional[str] = Field(
        default=None,
        description="If Unmatched, suggest a concise name for a NEW project."
    )
    estimated_duration: Optional[str] = Field(
        default=None,
        description="An estimated duration string (e.g., '15min', '1h') if inferable."
    )
    alternative_projects: List[str] = Field(
        default_factory=list,
        description="Up to 2 other projects that might be a close second match."
    )

    notes: Optional[str] = Field(
        default="",
        description="Any secondary details, context, or descriptions extracted from the input text that shouldn't be in the main title."
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
    tool_schema: dict  # <--- NEW: To store the raw tool definition
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