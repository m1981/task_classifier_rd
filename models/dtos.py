from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SingleTaskClassificationRequest:
    task_text: str
    available_projects: List[str]
    prompt_variant: str = "basic"

@dataclass
class SaveDatasetRequest:
    name: str
    source_dataset: str
    projects: List[str]
    inbox_tasks: List[str]
    
    def validate(self) -> Optional[str]:
        if not self.name.strip():
            return "Dataset name cannot be empty"
        if len(self.name) > 50:
            return "Dataset name too long"
        return None

@dataclass
class SaveDatasetResponse:
    success: bool
    message: str
    dataset_name: Optional[str] = None
    error_type: Optional[str] = None
