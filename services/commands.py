from models.dtos import SaveDatasetRequest, SaveDatasetResponse
from models import DatasetContent

class SaveDatasetCommand:
    def __init__(self, dataset_manager, projector):
        self.dataset_manager = dataset_manager
        self.projector = projector
    
    def execute(self, request: SaveDatasetRequest, source_dataset: DatasetContent) -> SaveDatasetResponse:
        # 1. Validate
        validation_error = request.validate()
        if validation_error:
            return SaveDatasetResponse(
                success=False, 
                message=validation_error,
                error_type="validation"
            )
        
        # 2. Project data (if needed)
        dataset_to_save = self.projector.project_for_save(source_dataset, request)
        
        # 3. Persist
        result = self.dataset_manager.save_dataset(request.name, dataset_to_save)
        
        # 4. Return structured response
        return SaveDatasetResponse(
            success=result["success"],
            message=result.get("message", result.get("error", "")),
            dataset_name=request.name if result["success"] else None,
            error_type=result.get("type")
        )
