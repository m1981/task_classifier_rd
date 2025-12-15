from models import DatasetContent
from models.dtos import SaveDatasetRequest

class DatasetProjector:
    @staticmethod
    def from_ui_state(dataset: DatasetContent, current_name: str, source_name: str) -> SaveDatasetRequest:
        """
        Projects UI state to a Save Request DTO.
        :param dataset: The actual data objects
        :param current_name: The name currently in the input box (target name)
        :param source_name: The name of the file originally loaded (source name)
        """
        return SaveDatasetRequest(
            name=current_name,
            source_dataset=source_name, # Populated correctly now
            projects=[p.name for p in dataset.projects],
            inbox_tasks=dataset.inbox_tasks
        )
    
    @staticmethod
    def project_for_save(dataset: DatasetContent, request: SaveDatasetRequest) -> DatasetContent:
        return dataset