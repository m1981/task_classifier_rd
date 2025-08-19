from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

@dataclass
class DatasetContent:
    reference_tasks: List[UnifiedTask]
    projects: List[UnifiedTask]
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
