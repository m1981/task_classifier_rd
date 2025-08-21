from models import DatasetContent
from models.dtos import SaveDatasetRequest

class DatasetProjector:
    @staticmethod
    def from_ui_state(dataset: DatasetContent, name: str) -> SaveDatasetRequest:
        return SaveDatasetRequest(
            name=name,
            source_dataset="",
            projects=[p.name for p in dataset.projects],
            inbox_tasks=dataset.inbox_tasks
        )
    
    @staticmethod
    def project_for_save(dataset: DatasetContent, request: SaveDatasetRequest) -> DatasetContent:
        return dataset
