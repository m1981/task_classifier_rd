from typing import List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class ClassificationType(str, Enum):
    TASK = "task"
    SHOPPING = "resource"
    REFERENCE = "reference"
    NEW_PROJECT = "new_project"
    TRASH = "trash"


class ClassificationResult(BaseModel):
    classification_type: ClassificationType = Field(
        description="The category of the item. Use 'resource' for things to buy/acquire, 'reference' for URLs/notes, 'task' for actions."
    )
    suggested_project: str = Field(
        description="The exact name of the best matching project, or 'Unmatched' if none fit."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0."
    )
    reasoning: str = Field(
        description="Brief explanation (max 15 words) of why this project and type were chosen."
    )
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
        description="An estimated duration string (e.g., '15min', '1h') if inferable from the task complexity."
    )
    alternative_projects: List[str] = Field(
        default_factory=list,
        description="Up to 2 other projects that might be a close second match."
    )