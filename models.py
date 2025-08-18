from dataclasses import dataclass
from typing import List, Optional
from pathlib import Path

@dataclass
class ReferenceTask:
    id: str
    subject: str
    tags: List[str]
    duration: Optional[str] = None

@dataclass
class Project:
    pid: str
    subject: str

@dataclass
class ClassificationResult:
    task: str
    suggested_project: str
    confidence: float
    extracted_tags: List[str]
    estimated_duration: Optional[str] = None
    reasoning: str = ""

@dataclass
class DatasetContent:
    reference_tasks: List[ReferenceTask]
    projects: List[Project]
    inbox_tasks: List[str]

@dataclass
class ClassificationRequest:
    dataset: DatasetContent
    prompt_variant: str

@dataclass
class ClassificationResponse:
    results: List[ClassificationResult]
    prompt_used: str
    raw_response: str