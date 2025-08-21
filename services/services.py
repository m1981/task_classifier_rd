from pathlib import Path
from typing import List
from models import DatasetContent, Project, ClassificationResult, ClassificationRequest, ClassificationResponse
from dataset_io import YamlDatasetLoader, YamlDatasetSaver
import anthropic

class DatasetManager:
    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.loader = YamlDatasetLoader()
        self.saver = YamlDatasetSaver()

    def load_dataset(self, name: str) -> DatasetContent:
        dataset_path = self.base_path / name / "dataset.yaml"
        return self.loader.load(dataset_path)

    def save_dataset(self, name: str, content: DatasetContent) -> dict:
        try:
            dataset_dir = self.base_path / name
            dataset_dir.mkdir(parents=True, exist_ok=True)
            dataset_path = dataset_dir / "dataset.yaml"
            self.saver.save(dataset_path, content)
            return {"success": True, "message": f"Dataset '{name}' saved successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_datasets(self) -> List[str]:
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
        if self._is_static_prompt(request.prompt_variant):
            return self._build_static_prompt(request.prompt_variant)
        else:
            return self._build_dynamic_prompt(request)

    def _is_static_prompt(self, variant: str) -> bool:
        return (self.prompts_dir / f"{variant}.md").exists()

    def _build_static_prompt(self, variant: str) -> str:
        prompt_file = self.prompts_dir / f"{variant}.md"
        return prompt_file.read_text()

    def _build_dynamic_prompt(self, request: ClassificationRequest) -> str:
        guidance = self._get_dynamic_guidance(request.prompt_variant)
        projects = self._format_projects(request.dataset.projects)
        tasks = self._format_inbox_tasks(request.dataset.inbox_tasks)
        
        return f"{guidance}\n\nProjects:\n{projects}\n\nInbox Tasks:\n{tasks}"

    def _get_dynamic_guidance(self, variant: str) -> str:
        return self._dynamic_variants.get(variant, self._dynamic_variants["basic"])

    def _format_projects(self, projects: List[Project]) -> str:
        return '\n'.join([f"  {p.id}. {p.name}" for p in projects])

    def _format_inbox_tasks(self, tasks: List[str]) -> str:
        if not tasks:
            return "  [NO TASKS TO CLASSIFY]"
        return '\n'.join([f"  - {task}" for task in tasks])

class ResponseParser:
    def parse(self, raw_response: str) -> List[ClassificationResult]:
        results = []
        current_task = {}

        for line in raw_response.strip().split('\n'):
            line = line.strip()
            if not line or line == "---":
                if current_task:
                    results.append(self._create_result(current_task))
                    current_task = {}
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().upper()
                value = value.strip()

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

        if current_task:
            results.append(self._create_result(current_task))

        return results

    def _parse_confidence(self, value: str) -> float:
        try:
            if '%' in value:
                return float(value.replace('%', '')) / 100
            return float(value)
        except:
            return 0.0

    def _create_result(self, task_data: dict) -> ClassificationResult:
        return ClassificationResult(
            task=task_data.get('task', ''),
            suggested_project=task_data.get('suggested_project', ''),
            confidence=task_data.get('confidence', 0.0),
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
        prompt = self.prompt_builder.build_prompt(request)
        raw_response = self._call_api(prompt)
        results = self.parser.parse(raw_response)

        return ClassificationResponse(
            results=results,
            prompt_used=prompt,
            raw_response=raw_response
        )

    def _call_api(self, prompt: str) -> str:
        try:
            response = self.client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            raise Exception(f"API call failed: {str(e)}")