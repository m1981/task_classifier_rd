# models/__init__.py

# Import from the NEW locations
from .entities import (
    DatasetContent,
    Project,
    TaskItem,
    Goal,
    ReferenceItem,
    ProjectStatus
)
from .ai_schemas import (
    ClassificationResult,
    ClassificationResponse,
    ClassificationRequest
)
from .dtos import SaveDatasetRequest, SaveDatasetResponse, SingleTaskClassificationRequest

__all__ = [
    'DatasetContent', 
    'Project', 
    'Task', 
    'Goal',
    'ProjectResource',
    'ReferenceItem',
    'SystemConfig',
    'ResourceType',
    'ProjectStatus',
    'ClassificationRequest',
    'ClassificationResult', 
    'ClassificationResponse',
    'SaveDatasetRequest', 
    'SaveDatasetResponse',
    SingleTaskClassificationRequest
]