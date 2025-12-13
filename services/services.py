from pathlib import Path
from typing import List
import json
from models import DatasetContent, Project, ClassificationResult, ClassificationRequest, ClassificationResponse
from models.models import SystemConfig  # Import Config
from models.dtos import SingleTaskClassificationRequest  # Import DTO
from dataset_io import YamlDatasetLoader, YamlDatasetSaver
import anthropic

class DatasetManager:
    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._yaml_loader = YamlDatasetLoader()
        self._yaml_saver = YamlDatasetSaver()

    def load_dataset(self, name: str) -> DatasetContent:
        """Load dataset - try YAML first, fallback to legacy format"""
        dataset_path = self.base_path / name
        yaml_file = dataset_path / "dataset.yaml"
        
        if yaml_file.exists():
            return self._yaml_loader.load(yaml_file)
        else:
            raise FileNotFoundError(f"Dataset '{name}' not found")

    def save_dataset(self, name: str, content: DatasetContent) -> dict:
        """Save dataset with validation and detailed result"""
        # Validate name
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
        """Validate dataset name, return error message or empty string"""
        if not name or not name.strip():
            return "Dataset name cannot be empty"
        if len(name) > 50:
            return "Dataset name too long (max 50 characters)"
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Dataset name can only contain letters, numbers, hyphens, and underscores"
        return ""

    def list_datasets(self) -> List[str]:
        """List available dataset names"""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]

class PromptBuilder:
    def __init__(self, prompts_dir: Path = Path("data/prompts")):
        self.prompts_dir = prompts_dir
        self.config = SystemConfig()  # Load Config
        self._dynamic_variants = {
            "basic": """Act as my personal advisor and assistant...""",
        }

    # --- UPDATED: Accepts DTO now ---
    def build_single_task_prompt(self, request: SingleTaskClassificationRequest) -> str:
        project_list = ", ".join([f'"{p}"' for p in request.available_projects])

        # Use tags from Config
        tags_str = ", ".join(self.config.DEFAULT_TAGS)

        return f"""
        You are a task organization assistant.
        Task to classify: "{request.task_text}"

        Available Projects: [{project_list}]
        Allowed Tags: [{tags_str}]

        Analyze the task and return a JSON object (no markdown, just raw JSON) with these keys:
        {{
            "suggested_project": "Exact name of best matching project or 'Unmatched'",
            "confidence": 0.65,
            "reasoning": "Short explanation why",
            "tags": ["tag1", "tag2"]
        }}
        """

    def build_prompt(self, request: ClassificationRequest) -> str:
        """Build prompt - auto-detect static vs dynamic based on variant name"""
        if self._is_static_prompt(request.prompt_variant):
            return self._build_static_prompt(request.prompt_variant)
        else:
            return self._build_dynamic_prompt(request)

    def _is_static_prompt(self, variant: str) -> bool:
        """Check if this is a static prompt file"""
        return (self.prompts_dir / f"{variant}.md").exists()

    def _build_static_prompt(self, variant: str) -> str:
        """Load complete prompt from file (for testing)"""
        prompt_file = self.prompts_dir / f"{variant}.md"
        content = prompt_file.read_text(encoding='utf-8').strip()
        return content

    def _build_dynamic_prompt(self, request: ClassificationRequest) -> str:
        guidance = self._get_dynamic_guidance(request.prompt_variant)
        projects_list = self._format_projects(request.dataset.projects)
        tasks_list = self._format_inbox_tasks(request.dataset.inbox_tasks)

        return f"""{guidance}

Available projects:
{projects_list}

Classify these tasks:
{tasks_list}

Available tags:
  physical, digital
  out - (if physical)
  need-material (if I might have to buy material, ingredients, etc.)
  need-tools (if not bare handed then require tools)
  buy (item goes to buy list)

Response format:

For each task, provide on separate lines:
TASK: [original task]
PROJECT: [best matching project OR unmatched]
CONFIDENCE: [0.0-1.0]
TAGS: [comma-separated tags]
DURATION: [time estimate]
REASONING: [brief explanation]
ALTERNATIVES: [semicolon-separated list of other potential projects, or 'none']
---"""

    def _get_dynamic_guidance(self, variant: str) -> str:
        """Get guidance for dynamic prompts"""
        return self._dynamic_variants.get(variant, "Act as a helpful task organizer.")

    def _format_projects(self, projects: List[Project]) -> str:
        """Format projects list for prompt"""
        return '\n'.join([f"  - {p.name}" for p in projects])

    def _format_inbox_tasks(self, tasks: List[str]) -> str:
        """Format inbox tasks for prompt"""
        if not tasks:
            return "  [NO TASKS TO CLASSIFY]"
        return '\n'.join([f"  - {task}" for task in tasks])

class ResponseParser:
    def parse_single_json(self, raw_response: str, task_text: str) -> ClassificationResult:
        try:
            # 1. Robust Extraction: Find the first '{' and last '}'
            start_idx = raw_response.find('{')
            end_idx = raw_response.rfind('}')

            if start_idx == -1 or end_idx == -1:
                raise ValueError("No JSON object found in response")

            clean_json = raw_response[start_idx:end_idx + 1]

            # 2. Parse
            data = json.loads(clean_json)

            return ClassificationResult(
                task=task_text,
                suggested_project=data.get("suggested_project", "Unmatched"),
                confidence=float(data.get("confidence", 0.0)),
                reasoning=data.get("reasoning", ""),
                extracted_tags=data.get("tags", [])
            )
        except Exception as e:
            return ClassificationResult(
                task=task_text,
                suggested_project="Unmatched",
                confidence=0.0,
                reasoning=f"Parsing error: {str(e)}"  # This was being hidden!
            )


class TaskClassifier:
    def __init__(self, client, prompt_builder: PromptBuilder, parser: ResponseParser):
        self.client = client
        self.prompt_builder = prompt_builder
        self.parser = parser

    # --- NEW METHOD: Handles Single Task via DTO ---
    def classify_single(self, request: SingleTaskClassificationRequest) -> ClassificationResponse:
        """Classify a single task using the JSON strategy"""
        prompt = self.prompt_builder.build_single_task_prompt(request)

        raw_response = self._call_api(prompt)

        # Use the specific JSON parser for single tasks
        result = self.parser.parse_single_json(raw_response, request.task_text)

        return ClassificationResponse(
            results=[result],
            prompt_used=prompt,
            raw_response=raw_response
        )

    def classify(self, request: ClassificationRequest) -> ClassificationResponse:
        # ... [Existing batch logic] ...
        prompt = self.prompt_builder.build_prompt(request)
        raw_response = self._call_api(prompt)
        results = self.parser.parse(raw_response)
        return ClassificationResponse(results=results, prompt_used=prompt, raw_response=raw_response)

    def _call_api(self, prompt: str) -> str:
        # ... [Remains unchanged] ...
        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")