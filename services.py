from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import json
import yaml
from models import DatasetContent, ReferenceTask, Project, ClassificationResult, ClassificationRequest, ClassificationResponse

class DatasetManager:
    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def load_dataset(self, name: str) -> DatasetContent:
        """Load dataset - try YAML first, fallback to legacy format"""
        dataset_path = self.base_path / name

        # Try modern YAML format
        yaml_file = dataset_path / "dataset.yaml"
        if yaml_file.exists():
            return self._load_yaml_dataset(yaml_file)

        # Fallback to legacy separate files format
        return self._load_legacy_dataset(dataset_path)

    def save_dataset(self, name: str, content: DatasetContent) -> None:
        """Save dataset in YAML format"""
        self.save_yaml_dataset(name, content)

    def list_datasets(self) -> List[str]:
        """List available dataset names"""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]

    def _load_yaml_dataset(self, yaml_file: Path) -> DatasetContent:
        """Load dataset from YAML format"""
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert projects
        projects = []
        for project_key, project_data in data.get('projects', {}).items():
            projects.append(Project(
                id=project_data['id'],
                name=project_data['name'],
                status=project_data.get('status', 'ongoing'),
                tags=project_data.get('tags', [])
            ))

        # Convert reference tasks (from project tasks)
        reference_tasks = []
        for project_data in data.get('projects', {}).values():
            for task_data in project_data.get('tasks', []):
                reference_tasks.append(ReferenceTask(
                    id=task_data['id'],
                    name=task_data['name'],
                    pid=project_data['id'],
                    duration=task_data.get('duration', 'unknown'),
                    tags=task_data.get('tags', [])
                ))

        # Get inbox tasks
        inbox_tasks = data.get('inbox_tasks', [])

        return DatasetContent(
            reference_tasks=reference_tasks,
            projects=projects,
            inbox_tasks=inbox_tasks
        )

    def _load_legacy_dataset(self, dataset_path: Path) -> DatasetContent:
        """Load from legacy separate files format"""
        projects = self._load_projects(dataset_path / "projects.txt")
        reference_tasks = self._load_reference_tasks(dataset_path / "reference_tasks.txt")
        inbox_tasks = self._load_inbox_tasks(dataset_path / "inbox_tasks.txt")

        return DatasetContent(
            reference_tasks=reference_tasks,
            projects=projects,
            inbox_tasks=inbox_tasks
        )

    def _load_projects(self, file_path: Path) -> List[Project]:
        """Parse projects from CSV-like format: pid;subject"""
        if not file_path.exists():
            return []

        projects = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(';')
                if len(parts) >= 2:
                    projects.append(Project(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        status="ongoing",
                        tags=[]
                    ))
        return projects

    def _load_reference_tasks(self, file_path: Path) -> List[ReferenceTask]:
        """Parse reference tasks from CSV-like format: id;subject;tags;duration"""
        if not file_path.exists():
            return []

        tasks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                parts = line.split(';')
                if len(parts) >= 3:
                    tasks.append(ReferenceTask(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        pid=1,  # Assume they belong to project 1 for migration
                        duration=parts[3].strip() if len(parts) > 3 else "unknown",
                        tags=[t.strip() for t in parts[2].split(',') if t.strip()]
                    ))
        return tasks

    def _load_inbox_tasks(self, file_path: Path) -> List[str]:
        """Load inbox tasks, one per line"""
        if not file_path.exists():
            return []

        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]

    def save_yaml_dataset(self, name: str, content: DatasetContent) -> None:
        """Save dataset in YAML format"""
        dataset_path = self.base_path / name
        dataset_path.mkdir(parents=True, exist_ok=True)

        # Group tasks by project
        projects_data = {}
        for project in content.projects:
            project_tasks = [t for t in content.reference_tasks if t.pid == project.id]

            projects_data[project.name.lower().replace(' ', '_')] = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'tags': project.tags,
                'tasks': [
                    {
                        'id': task.id,
                        'name': task.name,
                        'duration': task.duration,
                        'tags': task.tags,
                        'notes': ''
                    }
                    for task in project_tasks
                ]
            }

        yaml_data = {
            'projects': projects_data,
            'inbox_tasks': content.inbox_tasks
        }

        yaml_file = dataset_path / "dataset.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, indent=2)

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
        
        print(f"🔍 DEBUG: Creating result - Task: {task_data.get('task', 'UNKNOWN')}, Project: {project}, Confidence: {confidence}")
        
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
