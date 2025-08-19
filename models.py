from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

@dataclass
class UnifiedTask:
    id: int
    name: str
    pid: int  # 0 for root projects, >0 for tasks with parents
    duration: str  # "60m", "2h", "3d", "ongoing", "unknown"
    tags: List[str]
    
    def is_project(self) -> bool:
        return self.pid == 0
    
    def is_task(self) -> bool:
        return self.pid > 0
    
    def parse_duration_minutes(self) -> Optional[int]:
        """Convert duration string to minutes for calculations"""
        if not self.duration or self.duration in ['ongoing', 'unknown']:
            return None
        
        import re
        match = re.match(r'(\d+)([mhd])', self.duration.lower())
        if not match:
            return None
            
        value, unit = int(match.group(1)), match.group(2)
        multipliers = {'m': 1, 'h': 60, 'd': 1440}
        return value * multipliers.get(unit, 1)

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
