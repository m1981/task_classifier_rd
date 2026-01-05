# models/__init__.py

# Import from the NEW locations
from .entities import (
    DatasetContent,
    Project,
    TaskItem,
    ResourceItem,
    ReferenceItem,
    ProjectItem,
    ProjectItemUnion,
    Goal,
    SystemConfig,
    ProjectStatus,
    ResourceType,
    GoalStatus,
    TagDimensions
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
    'TaskItem',
    'ResourceItem',
    'ReferenceItem',
    'ProjectItem',
    'ProjectItemUnion',
    'Goal',
    'SystemConfig',
    'ResourceType',
    'ProjectStatus',
    'GoalStatus',
    'ClassificationRequest',
    'ClassificationResult', 
    'ClassificationResponse',
    'SaveDatasetRequest', 
    'SaveDatasetResponse',
    'SingleTaskClassificationRequest',
]