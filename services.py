from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import json
from models import DatasetContent, UnifiedTask, ClassificationResult, ClassificationRequest, ClassificationResponse

class DatasetManager:
    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def load_dataset(self, name: str) -> DatasetContent:
        """Load dataset from files in data/datasets/{name}/"""
        dataset_path = self.base_path / name
        
        if not dataset_path.exists():
            raise FileNotFoundError(f"Dataset '{name}' not found at {dataset_path}")
        
        # Try unified format first
        unified_file = dataset_path / "unified_tasks.txt"
        if unified_file.exists():
            all_tasks = self._load_unified_tasks(unified_file)
            reference_tasks = [t for t in all_tasks if t.is_task()]
            projects = [t for t in all_tasks if t.is_project()]
        else:
            # Fallback to separate files
            reference_tasks = self._load_reference_tasks(dataset_path / "reference_tasks.txt")
            projects = self._load_projects(dataset_path / "projects.txt")
        
        inbox_tasks = self._load_inbox_tasks(dataset_path / "inbox_tasks.txt")
        
        return DatasetContent(
            reference_tasks=reference_tasks,
            projects=projects,
            inbox_tasks=inbox_tasks
        )
    
    def save_dataset(self, name: str, content: DatasetContent) -> None:
        """Save dataset to files in data/datasets/{name}/"""
        dataset_path = self.base_path / name
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        # Save reference tasks
        self._save_reference_tasks(dataset_path / "reference_tasks.txt", content.reference_tasks)
        
        # Save projects
        self._save_projects(dataset_path / "projects.txt", content.projects)
        
        # Save inbox tasks
        self._save_inbox_tasks(dataset_path / "inbox_tasks.txt", content.inbox_tasks)
    
    def list_datasets(self) -> List[str]:
        """List available dataset names"""
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]
    
    def _load_unified_tasks(self, file_path: Path) -> List[UnifiedTask]:
        """Parse unified format: id;name;pid;duration;tags"""
        if not file_path.exists():
            return []
        
        tasks = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    parts = line.split(';')
                    if len(parts) < 4:
                        raise ValueError(f"Line {line_num}: Expected at least 4 fields")
                    
                    task = UnifiedTask(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        pid=int(parts[2].strip()),  # 0 for projects, >0 for tasks, -1 for inbox
                        duration=parts[3].strip() or "unknown",
                        tags=[t.strip() for t in parts[4].split(',') if t.strip()] if len(parts) > 4 else []
                    )
                    tasks.append(task)
                    
                except (ValueError, IndexError) as e:
                    print(f"⚠️ Skipping invalid line {line_num}: {e}")
                    continue
        
        # Validate relationships
        self._validate_task_relationships(tasks)
        return tasks
    
    def _validate_task_relationships(self, tasks: List[UnifiedTask]) -> None:
        """Validate parent-child relationships"""
        task_ids = {t.id for t in tasks}
        project_ids = {t.id for t in tasks if t.is_project()}
        
        errors = []
        for task in tasks:
            if task.is_task() and task.pid not in project_ids:
                errors.append(f"Task '{task.name}' (id:{task.id}) references non-existent project (pid:{task.pid})")
        
        if errors:
            raise ValueError("Relationship validation failed:\n" + "\n".join(errors))
    
    def _load_reference_tasks(self, file_path: Path) -> List[UnifiedTask]:
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
                    tasks.append(UnifiedTask(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        pid=1,  # Assume they belong to project 1 for migration
                        duration=parts[3].strip() if len(parts) > 3 else "unknown",
                        tags=[t.strip() for t in parts[2].split(',')]
                    ))
        return tasks
    
    def _load_projects(self, file_path: Path) -> List[UnifiedTask]:
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
                    projects.append(UnifiedTask(
                        id=int(parts[0].strip()),
                        name=parts[1].strip(),
                        pid=0,  # Projects have pid=0
                        duration="ongoing",
                        tags=[]
                    ))
        return projects
    
    def _load_inbox_tasks(self, file_path: Path) -> List[str]:
        """Load inbox tasks, one per line"""
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    
    def _save_reference_tasks(self, file_path: Path, tasks: List[UnifiedTask]) -> None:
        """Save reference tasks in CSV-like format"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for task in tasks:
                tags_str = ','.join(task.tags)
                duration_str = task.duration or ''
                f.write(f"{task.id};{task.name};{tags_str};{duration_str}\n")
    
    def _save_projects(self, file_path: Path, projects: List[UnifiedTask]) -> None:
        """Save projects in CSV-like format"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for project in projects:
                f.write(f"{project.id};{project.name}\n")
    
    def _save_inbox_tasks(self, file_path: Path, tasks: List[str]) -> None:
        """Save inbox tasks, one per line"""
        with open(file_path, 'w', encoding='utf-8') as f:
            for task in tasks:
                f.write(f"{task}\n")

class PromptBuilder:
    def __init__(self, prompts_dir: Path = Path("data/prompts")):
        self.prompts_dir = prompts_dir
        self._guidance_variants = {
            "basic": """Act as my personal advisor and assistant...""",
            "diy_renovation": """Act as an experienced DIY home renovation expert..."""
        }
    
    def build_prompt(self, request: ClassificationRequest) -> str:
        """Build complete prompt from request"""
        guidance = self._get_guidance(request.prompt_variant)
        projects_list = self._format_projects(request.dataset.projects)
        tasks_list = self._format_inbox_tasks(request.dataset.inbox_tasks)
        
        return f"""{guidance}"""

    #     return f"""{guidance}
    #
    # Available projects:
    # {projects_list}
    #
    # Classify these tasks:
    # {tasks_list}
    #
    # Available tags:
    #   physical, digial
    #   out, out  - (if physical)
    #   need-material (if I migh have to buy material, ingredients, etc.)
    #   need-tools (if not bare handed then require tools)
    #   buy (item goes to buy list)
    #
    # Response format:
    #
    # For each task, provide on separate lines:
    # TASK: [original task]
    # PROJECT: [best matching project OR unmatched]
    # CONFIDENCE: [0.0-1.0]
    # TAGS: [comma-separated tags]
    # DURATION: [time estimate]
    # REASONING: [brief explanation]
    # ALTERNATIVES: [semicolon-separated list of other potential projects, or 'none']
    # ---
    # TASK: ...
    # PROJECT: ..."""

    def _get_guidance(self, variant: str) -> str:
        """Get guidance text for prompt variant - load from file or fallback to hardcoded"""
        # Try to load from file first
        prompt_file = self.prompts_dir / f"{variant}.md"
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8').strip()
        
        # Fallback to hardcoded variants
        return self._guidance_variants.get(variant, "Act as a helpful task organizer.")
    
    def _format_projects(self, projects: List[UnifiedTask]) -> str:
        """Format projects list for prompt"""
        return '\n'.join([f"  - {p.name}" for p in projects])
    
    def _format_inbox_tasks(self, tasks: List[str]) -> str:
        """Format inbox tasks for prompt"""
        return '\n'.join([f"  - {task}" for task in tasks])

class ResponseParser:
    def parse(self, raw_response: str) -> List[ClassificationResult]:
        """Parse multiline text response into structured data"""
        print(f"🔍 DEBUG: Parsing response with {len(raw_response)} characters")
        results = []
        current_task = {}

        for line in raw_response.strip().split('\n'):
            line = line.strip()
            if not line:
                continue

            if line == "---":
                if current_task:
                    print(f"🔍 DEBUG: Adding task: {current_task.get('task', 'UNKNOWN')}")
                    results.append(self._create_result(current_task))
                    current_task = {}
                continue

            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()

                if key == "task":
                    current_task['task'] = value
                elif key == "project":
                    current_task['suggested_project'] = value
                elif key == "confidence":
                    current_task['confidence'] = self._parse_confidence(value)
                elif key == "tags":
                    current_task['extracted_tags'] = [tag.strip() for tag in value.split(',') if tag.strip()]
                elif key == "duration":
                    current_task['estimated_duration'] = value
                elif key == "reasoning":
                    current_task['reasoning'] = value
                elif key == "alternatives":
                    if value.lower() != 'none':
                        current_task['alternative_projects'] = [alt.strip() for alt in value.split(';') if alt.strip()]
                    else:
                        current_task['alternative_projects'] = []

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
