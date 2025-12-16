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
# LEGACY: from dataset_io import YamlDatasetLoader, YamlDatasetSaver

class DatasetManager:
    """
    Infrastructure Service: Handles File I/O for Datasets.
    """

    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        # LEGACY: self._yaml_loader = YamlDatasetLoader()
        # LEGACY: self._yaml_saver = YamlDatasetSaver()

    def load_dataset(self, name: str) -> str:
        """
        Returns the path to the SQLite DB.
        The Repository will handle the actual connection.
        """
        # Ensure name ends with .db
        if not name.endswith(".db"):
            name = f"{name}.db"

        db_path = self.base_path / name
        return str(db_path)

    def save_dataset(self, name: str, content: DatasetContent) -> dict:
        """
        LEGACY: This was for YAML.
        In SQLite, saving happens via transactions in the Repository.
        We keep this for interface compatibility if needed, or deprecate.
        """
        return {"success": True, "message": "Auto-saved to SQLite"}

    def list_datasets(self) -> List[str]:
        if not self.base_path.exists():
            return []
        # Return .db files
        return [d.stem for d in self.base_path.glob("*.db")]

# ... PromptBuilder and TaskClassifier remain unchanged ...

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
        # FIX 1: Handle Empty List
        if not request.available_projects:
            project_section = "None"
        else:
            # FIX 2: Sanitize Quotes (Replace double quotes with single quotes)
            # This prevents prompt injection/syntax breaking
            sanitized_projects = [p.replace('"', "'") for p in request.available_projects]

            # Format as a clean list
            joined_projects = ", ".join([f'"{p}"' for p in sanitized_projects])
            project_section = f"[{joined_projects}]"

        tags_str = ", ".join(self.config.DEFAULT_TAGS)

        return f"""
        You are a task organization assistant.
        Task to classify: "{request.task_text}"
        Available Projects: {project_section}
        Allowed Tags: [{tags_str}]

        Analyze the task. 
        1. If it fits an existing project, set 'suggested_project' to that name.
        2. If it does NOT fit (or if Available Projects is None), set 'suggested_project' to "Unmatched" and provide a 'suggested_new_project_name'.
        """

    def build_prompt(self, request: ClassificationRequest) -> str:
        """Build prompt for batch processing"""
        # For batch processing, we might still need manual parsing if we want
        # multiple items in one response, OR we can use a List[Model] output format.
        # For simplicity in this refactor, we will focus on the single task flow
        # which is what the App uses.
        return self._build_dynamic_prompt(request)

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

            # We need to manually inject the original task text back into the result
            # because the LLM output doesn't necessarily repeat it.
            # (Assuming ClassificationResult has a 'task' field, we set it here)
            # Note: Pydantic models are mutable by default unless config=frozen
            parsed_result.task = request.task_text

            return ClassificationResponse(
                results=[parsed_result],
                prompt_used=prompt,
                raw_response=str(parsed_result.model_dump())  # Debug info
            )

        except Exception as e:
            # Fallback for API errors or Validation errors
            # We return a "safe" failure response
            error_result = ClassificationResult(
                task=request.task_text,
                suggested_project="Unmatched",
                confidence=0.0,
                reasoning=f"AI Error: {str(e)}",
                extracted_tags=[]
            )
            return ClassificationResponse(
                results=[error_result],
                prompt_used=prompt,
                raw_response=str(e)
            )

