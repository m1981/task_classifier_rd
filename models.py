from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
from datetime import datetime

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
    alternative_projects: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.alternative_projects is None:
            self.alternative_projects = []

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

@dataclass
class TaskBatch:
    name: str
    task_type: str
    task_ids: List[str]  # Store task text for simplicity
    estimated_hours: float
    created_date: str = field(default_factory=lambda: datetime.now().isoformat())
    suggested_sequence: List[str] = field(default_factory=list)

@dataclass
class BatchSummary:
    materials: List[str]
    tools: List[str]
    projects_involved: List[str]
    total_tasks: int

@dataclass
class BatchAnalysis:
    task_type: str
    matching_tasks: List[ClassificationResult]
    total_time_estimate: str
    consolidated_materials: List[str]
    consolidated_tools: List[str]
    cross_project_count: int
