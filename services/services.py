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
        # 1. Merge Tags
        all_tags = list(set(self.config.DEFAULT_TAGS + (existing_tags or [])))
        tags_str = ", ".join(all_tags)
        durations_str = ", ".join(self.config.ALLOWED_DURATIONS)

        # 2. Dynamic Category Examples (DRY)
        # We filter the config tags to provide relevant examples dynamically
        context_ex = ", ".join([t for t in self.config.DEFAULT_TAGS if t.startswith("@")][:3])
        effort_ex = ", ".join([t for t in self.config.DEFAULT_TAGS if "Mental" in t or "Physical" in t][:3])
        energy_ex = ", ".join([t for t in self.config.DEFAULT_TAGS if "Energy" in t or "Morning" in t][:3])

        return f"""
        You are a GTD Triage Expert.
        
        INCOMING ITEM: "{task_text}"
        
        CONTEXT (Goals > Projects):
        {context_hierarchy}
        
        AVAILABLE TAGS: [{tags_str}]
        
        ALLOWED DURATIONS: [{durations_str}]

        TAGGING RULES:
        - Select 3-5 tags that best describe the task.
        - Categorize by:
          1. CONTEXT (Where? e.g. {context_ex})
          2. EFFORT (How hard? e.g. {effort_ex})
          3. ENERGY (When? e.g. {energy_ex})
        
        DECISION LOGIC:
        1. IS IT ACTIONABLE?
           - NO (Reference): Is it pure info (URL, fact) needing no action? -> Type: "reference"
           - NO (Someday): Is it for "someday" or "maybe"? -> Type: "incubate"
           - YES (Action): Does it require time/effort? -> Go to step 2.
           
        2. MATCHING:
           - Match to an existing PROJECT name (do NOT select a GOAL name).
           - If no project fits, set suggested_project to "Unmatched" and suggest a new name.
            - CRITICAL: You MUST identify 3 "alternative_projects" from the list. Even if the primary match is obvious, provide the next 3 most logical destinations

        OUTPUT FORMAT (Strict JSON):
        {{
            "classification_type": "task",
            "suggested_project": "Project Name",
            "confidence": 0.9,
            "reasoning": "Explanation...",
            "extracted_tags": ["@Computer", "Mental-Deep", "HighEnergy"],
            "refined_text": "Actionable Verb Task Name",
            "suggested_new_project_name": null,
            "estimated_duration": "30min",
            "alternative_projects": []
        }}
        
        INSTRUCTIONS:
        - Return ONLY the JSON object.
        - Use double quotes for JSON.
        - Apply tags strictly from the AVAILABLE TAGS list if possible.
        - TRANSLATION RULE: If the INCOMING ITEM is not in English, the 'refined_text' MUST be translated into clear, concise English.
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
    def __init__(self, client, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    def classify_single(self, request: SingleTaskClassificationRequest) -> ClassificationResponse:
        prompt = self.prompt_builder.build_triage_prompt(
            request.task_text,
            request.available_projects,
            request.existing_tags
        )

        # Capture the "Form" definition we are sending
        tool_schema = ClassificationResult.model_json_schema()

        try:
            # Use the .parse() method for automatic Pydantic validation
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",
                max_tokens=8024,
                temperature=0,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=ClassificationResult,
            )

            # The SDK returns a parsed object directly
            parsed_result = response.parsed_output

            return ClassificationResponse(
                results=[parsed_result],
                prompt_used=prompt,
                tool_schema=tool_schema,
                raw_response=parsed_result.model_dump_json(indent=2)
            )

        except Exception as e:
            error_result = ClassificationResult(
                reasoning=f"AI Error: {str(e)}",
                classification_type=ClassificationType.TASK,
                refined_text=request.task_text,
                suggested_project="Unmatched",
                confidence=0.0,
                extracted_tags=[]
            )
            return ClassificationResponse(
                results=[error_result],
                prompt_used=prompt,
                tool_schema=tool_schema,
                raw_response=str(e)
            )