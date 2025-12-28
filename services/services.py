from pathlib import Path
from typing import List
import anthropic
import json

# Import Domain Models and DTOs
from models import (
    DatasetContent,
    Project,
    ClassificationResult,
    ClassificationRequest,
    ClassificationResponse,
    SystemConfig,
    SingleTaskClassificationRequest
)

from models.ai_schemas import ClassificationType

# Import Infrastructure
from dataset_io import YamlDatasetLoader, YamlDatasetSaver

class DatasetManager:
    """
    Infrastructure Service: Handles File I/O for Datasets.
    """

    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._yaml_loader = YamlDatasetLoader()
        self._yaml_saver = YamlDatasetSaver()

    def load_dataset(self, name: str) -> DatasetContent:
        """Load dataset - try YAML first"""
        dataset_path = self.base_path / name
        yaml_file = dataset_path / "dataset.yaml"

        if yaml_file.exists():
            return self._yaml_loader.load(yaml_file)
        else:
            raise FileNotFoundError(f"Dataset '{name}' not found")

    def save_dataset(self, name: str, content: DatasetContent) -> dict:
        """Save dataset with validation and detailed result"""
        validation_error = self._validate_dataset_name(name)
        if validation_error:
            return {"success": False, "error": validation_error, "type": "validation"}

        try:
            self._yaml_saver.save(self.base_path / name, content)
            return {"success": True, "message": f"Dataset '{name}' saved successfully"}
        except PermissionError:
            return {"success": False, "error": "Permission denied - check folder permissions", "type": "permission"}
        except OSError as e:
            return {"success": False, "error": f"File system error: {str(e)}", "type": "filesystem"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}", "type": "unknown"}

    def _validate_dataset_name(self, name: str) -> str:
        if not name or not name.strip():
            return "Dataset name cannot be empty"
        if len(name) > 50:
            return "Dataset name too long (max 50 characters)"
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Dataset name can only contain letters, numbers, hyphens, and underscores"
        return ""

    def list_datasets(self) -> List[str]:
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]


class PromptBuilder:
    """
    Domain Service: Constructs prompts for the AI.
    Now simplified because we rely on Structured Outputs for formatting.
    """

    def __init__(self, prompts_dir: Path = Path("data/prompts")):
        self.prompts_dir = prompts_dir
        self.config = SystemConfig()
        self._dynamic_variants = {
            "basic": """Act as my personal advisor and assistant.""",
        }

    def build_single_task_prompt(self, request: SingleTaskClassificationRequest) -> str:
        project_list = ", ".join([f'"{p}"' for p in request.available_projects])
        tags_str = ", ".join(self.config.DEFAULT_TAGS)

        return f"""
        You are a task organization assistant.
        Task to classify: "{request.task_text}"
        Available Projects: [{project_list}]
        Allowed Tags: [{tags_str}]

        Analyze the task. 
        1. If it fits an existing project, set 'suggested_project' to that name.
        2. If it does NOT fit, set 'suggested_project' to "Unmatched" and provide a 'suggested_new_project_name'.
        """

    def build_prompt(self, request: ClassificationRequest) -> str:
        """Build prompt for batch processing"""
        # For batch processing, we might still need manual parsing if we want
        # multiple items in one response, OR we can use a List[Model] output format.
        # For simplicity in this refactor, we will focus on the single task flow
        # which is what the App uses.
        return self._build_dynamic_prompt(request)

    def build_smart_filter_prompt(self, query: str, tasks_str: str) -> str:
        return f"""
        You are a productivity assistant helping a user select tasks.

        USER QUERY: "{query}"

        CANDIDATE TASKS:
        {tasks_str}

        INSTRUCTIONS:
        1. Analyze the User Query for constraints (Time, Context, Energy, Tools).
        2. Select tasks from the Candidate List that strictly fit these constraints.
        3. Return the IDs of the matching tasks.
        4. If the query implies a time limit (e.g. "I have 1 hour"), try to fill that time with the highest priority/best fitting tasks without exceeding it significantly.
        5. Provide a brief reasoning.
        """

    def _build_dynamic_prompt(self, request: ClassificationRequest) -> str:
        guidance = self._get_dynamic_guidance(request.prompt_variant)
        projects_list = self._format_projects(request.dataset.projects)
        tasks_list = self._format_inbox_tasks(request.dataset.inbox_tasks)
        tags_list = "\n".join([f"  {t}" for t in self.config.DEFAULT_TAGS])

        return f"""{guidance}

Available projects:
{projects_list}

Classify these tasks:
{tasks_list}

Available tags:
{tags_list}
"""

    def _get_dynamic_guidance(self, variant: str) -> str:
        return self._dynamic_variants.get(variant, "Act as a helpful task organizer.")

    def _format_projects(self, projects: List[Project]) -> str:
        return '\n'.join([f"  - {p.name}" for p in projects])

    def _format_inbox_tasks(self, tasks: List[str]) -> str:
        if not tasks:
            return "  [NO TASKS TO CLASSIFY]"
        return '\n'.join([f"  - {task}" for task in tasks])


class TaskClassifier:
    """
    Application Service: Orchestrates the AI classification.
    Uses Anthropic Structured Outputs for reliability.
    """

    def __init__(self, client, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    def classify_single(self, request: SingleTaskClassificationRequest) -> ClassificationResponse:
        """
        Classify a single task using Pydantic validation (Structured Outputs).
        """
        prompt = self.prompt_builder.build_single_task_prompt(request)

        try:
            # Use the .parse() method for automatic Pydantic validation
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",
                max_tokens=1024,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=ClassificationResult,  # Pass the Pydantic model class
            )

            # The SDK returns a parsed object directly
            parsed_result = response.parsed_output

            # REMOVED: parsed_result.task = request.task_text  <-- DELETE THIS LINE
            # The 'task' field no longer exists on the model.
            # The original text is preserved in the DraftItem wrapper later.

            return ClassificationResponse(
                results=[parsed_result],
                prompt_used=prompt,
                raw_response=str(parsed_result.model_dump())
            )

        except Exception as e:
            # Fallback for API errors or Validation errors
            error_result = ClassificationResult(
                classification_type=ClassificationType.TASK,
                refined_text=request.task_text,
                suggested_project="Unmatched",
                confidence=0.0,
                reasoning=f"AI Error: {str(e)}",
                extracted_tags=[],
                # REMOVED: task=request.task_text  <-- DELETE THIS LINE
            )
            return ClassificationResponse(
                results=[error_result],
                prompt_used=prompt,
                raw_response=str(e)
            )

