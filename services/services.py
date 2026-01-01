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

    def build_triage_prompt(self, task_text: str, context_hierarchy: str, existing_tags: List[str] = None) -> str:
        # Use existing tags from the repo if available, otherwise fallback to config defaults
        if existing_tags:
            tags_str = ", ".join(existing_tags)
        else:
            tags_str = ", ".join(self.config.DEFAULT_TAGS)

        return f"""
        You are a GTD Triage Expert.
        
        INCOMING ITEM: "{task_text}"
        
        CONTEXT (Goals > Projects):
        
        {context_hierarchy}
        
        DECISION LOGIC:
        1. IS IT ACTIONABLE?
           - NO (Reference): Is it pure information (e.g. a URL, a fact) that requires NO further action to capture? -> Type: 'reference'.
           - NO (Someday): Actionable later? -> Type: 'incubate'.
           - NO (Junk): Ignore. (Do NOT return 'trash', user decides that).
           - YES (Action): Does it require time/effort (even just "writing it down" or "saving it")? -> Go to step 2.
           
        2. IS IT MULTI-STEP?
           - YES: Needs a new project? -> Type: 'new_project'.
           
        3. IS IT A SIMPLE ACTION?
           - YES (Do/Delegate): -> Type: 'task'.
           - YES (Buy): -> Type: 'resource'.

        INSTRUCTIONS:
        - Return the JSON classification.
        - If 'incubate', suggest a relevant project (e.g. "Someday/Maybe" or a generic one).
        - If 'task', try to match it to an existing Project under an active Goal.
        - If the project match is uncertain, provide up to 3 'alternative_projects'.
        """

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
        prompt = self.prompt_builder.build_triage_prompt(
            request.task_text,
            request.available_projects,
            request.existing_tags
        )
        try:
            # Use the .parse() method for automatic Pydantic validation
            response = self.client.beta.messages.parse(
                model="claude-sonnet-4-5",
                max_tokens=1024,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=ClassificationResult,  # Pass the Pydantic model class
            )

            # The SDK returns a parsed object directly
            parsed_result = response.parsed_output

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
                extracted_tags=[]
            )
            return ClassificationResponse(
                results=[error_result],
                prompt_used=prompt,
                raw_response=str(e)
            )