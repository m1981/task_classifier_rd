from pathlib import Path
from typing import List
from models import DatasetContent, Project, ClassificationResult, ClassificationRequest, ClassificationResponse
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
        self._dynamic_variants = {
            "basic": """Act as my personal advisor and assistant...""",
            "diy_renovation": """Act as an experienced DIY home renovation expert..."""
        }

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
        """Build dynamic prompt with injected data (for app)"""
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
    def parse(self, raw_response: str) -> List[ClassificationResult]:
        """Parse multiline text response into structured data"""
        print(f"🔍 DEBUG: Parsing response with {len(raw_response)} characters")
        print(f"🔍 DEBUG: First 200 chars: {repr(raw_response[:200])}")

        results = []
        current_task = {}

        for line_num, line in enumerate(raw_response.strip().split('\n'), 1):
            line = line.strip()
            if not line:
                continue

            print(f"🔍 DEBUG: Line {line_num}: {repr(line)}")

            if line == "---":
                if current_task:
                    print(f"🔍 DEBUG: Adding task: {current_task.get('task', 'UNKNOWN')}")
                    results.append(self._create_result(current_task))
                    current_task = {}
                continue

            # Parse key-value pairs
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()

                print(f"🔍 DEBUG: Parsed key='{key}', value='{value}'")

                if key == 'TASK':
                    current_task['task'] = value
                elif key == 'PROJECT':
                    current_task['suggested_project'] = value
                elif key == 'CONFIDENCE':
                    current_task['confidence'] = self._parse_confidence(value)
                elif key == 'TAGS':
                    current_task['extracted_tags'] = [tag.strip() for tag in value.split(',') if tag.strip()]
                elif key == 'DURATION':
                    current_task['estimated_duration'] = value
                elif key == 'REASONING':
                    current_task['reasoning'] = value
                elif key == 'ALTERNATIVES':
                    if value.lower() != 'none':
                        current_task['alternative_projects'] = [alt.strip() for alt in value.split(';') if alt.strip()]
            else:
                print(f"🔍 DEBUG: Skipping line without colon: {repr(line)}")

        # Add last task if exists
        if current_task:
            print(f"🔍 DEBUG: Adding final task: {current_task.get('task', 'UNKNOWN')}")
            results.append(self._create_result(current_task))

        print(f"🔍 DEBUG: Parsed {len(results)} total results")
        for i, result in enumerate(results):
            print(f"🔍 DEBUG: Result {i}: {result.task} -> {result.suggested_project}")

        return results

    def _parse_confidence(self, value: str) -> float:
        """Parse confidence value with error handling"""
        try:
            if '%' in value:
                return float(value.replace('%', '')) / 100
            return float(value)
        except ValueError:
            print(f"  -> Failed to parse confidence '{value}', using 0.5")
            return 0.5

    def _create_result(self, task_data: dict) -> ClassificationResult:
        """Create ClassificationResult with defaults for missing fields"""
        confidence = task_data.get('confidence', 0.5)
        project = task_data.get('suggested_project', 'unmatched')

        # Normalize project name and auto-mark low confidence as unmatched
        if project.lower() == 'unmatched' or confidence < 0.6:
            project = 'unmatched'  # Always lowercase

        print(
            f"🔍 DEBUG: Creating result - Task: {task_data.get('task', 'UNKNOWN')}, Project: {project}, Confidence: {confidence}")

        return ClassificationResult(
            task=task_data.get('task', ''),
            suggested_project=project,
            confidence=confidence,
            extracted_tags=task_data.get('extracted_tags', []),
            estimated_duration=task_data.get('estimated_duration'),
            reasoning=task_data.get('reasoning', ''),
            alternative_projects=task_data.get('alternative_projects', [])
        )

class TaskClassifier:
    def __init__(self, client, prompt_builder: PromptBuilder, parser: ResponseParser):
        self.client = client
        self.prompt_builder = prompt_builder
        self.parser = parser

    def classify(self, request: ClassificationRequest) -> ClassificationResponse:
        """Classify tasks using AI and return structured response"""
        prompt = self.prompt_builder.build_prompt(request)
        print(f"🔍 DEBUG: Sending prompt with {len(prompt)} characters")
        print(f"🔍 DEBUG: Classifying {len(request.dataset.inbox_tasks)} inbox tasks")

        raw_response = self._call_api(prompt)
        print(f"🔍 DEBUG: Received response with {len(raw_response)} characters")

        results = self.parser.parse(raw_response)
        print(f"🔍 DEBUG: Classification complete: {len(results)} results")

        return ClassificationResponse(
            results=results,
            prompt_used=prompt,
            raw_response=raw_response
        )

    def _call_api(self, prompt: str) -> str:
        """Call Anthropic API with error handling"""
        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-latest",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise RuntimeError(f"API call failed: {e}")
