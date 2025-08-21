from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import yaml
from models import DatasetContent, Project, Task

class DatasetLoader(ABC):
    @abstractmethod
    def load(self, path: Path) -> DatasetContent:
        pass

class DatasetSaver(ABC):
    @abstractmethod
    def save(self, path: Path, content: DatasetContent) -> None:
        pass

class YamlDatasetLoader(DatasetLoader):
    def load(self, yaml_file: Path) -> DatasetContent:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        projects = self._parse_projects(data.get('projects', {}))
        inbox_tasks = data.get('inbox_tasks', [])
        
        return DatasetContent(projects=projects, inbox_tasks=inbox_tasks)
    
    def _parse_projects(self, projects_data: dict) -> List[Project]:
        projects = []
        for project_data in projects_data.values():
            tasks = self._parse_tasks(project_data.get('tasks', []))
            projects.append(Project(
                id=project_data['id'],
                name=project_data['name'],
                status=project_data.get('status', 'ongoing'),
                tags=project_data.get('tags', []),
                tasks=tasks
            ))
        return projects
    
    def _parse_tasks(self, tasks_data: List[dict]) -> List[Task]:
        tasks = []
        for task_data in tasks_data:
            tasks.append(Task(
                id=task_data['id'],
                name=task_data['name'],
                duration=task_data.get('duration', 'unknown'),
                tags=task_data.get('tags', []),
                notes=task_data.get('notes', '')
            ))
        return tasks


class YamlDatasetSaver(DatasetSaver):
    def __init__(self):
        # Configure YAML dumper for consistent output
        self._setup_yaml_representer()

    def _setup_yaml_representer(self):
        """Configure YAML for VCS-friendly, consistent output"""
        
        def represent_list(dumper, data):
            # Always use block style for lists
            return dumper.represent_sequence('tag:yaml.org,2002:seq', data, flow_style=False)

        def represent_dict(dumper, data):
            # Always use block style for dicts
            return dumper.represent_mapping('tag:yaml.org,2002:map', data, flow_style=False)

        def represent_str(dumper, data):
            # Never quote strings unless absolutely necessary
            if data and any(char in data for char in ':#@[]{}|>'):
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='"')
            return dumper.represent_scalar('tag:yaml.org,2002:str', data)

        yaml.add_representer(list, represent_list)
        yaml.add_representer(dict, represent_dict) 
        yaml.add_representer(str, represent_str)

    def save(self, dataset_path: Path, content: DatasetContent) -> None:
        dataset_path.mkdir(parents=True, exist_ok=True)

        # Create the full data structure with consistent ordering
        yaml_data = {
            'projects': self._format_projects(content.projects),
            'inbox_tasks': sorted(content.inbox_tasks)  # Sort inbox tasks
        }

        yaml_file = dataset_path / "dataset.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                yaml_data,
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                width=1000,
                sort_keys=True  # Sort keys at top level
            )

    def _format_projects(self, projects: List[Project]) -> dict:
        """Format projects with consistent ordering"""
        projects_data = {}
        
        # Sort projects by ID for consistent ordering
        sorted_projects = sorted(projects, key=lambda p: p.id)
        
        for project in sorted_projects:
            # Use consistent key generation
            key = project.name.lower().replace(' ', '_').replace('/', '_')
            projects_data[key] = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'tags': sorted(project.tags),  # Sort tags for consistency
                'tasks': self._format_tasks(project.tasks)
            }
        return projects_data

    def _format_tasks(self, tasks: List[Task]) -> List[dict]:
        """Format tasks with consistent ordering"""
        # Sort tasks by ID for consistent ordering
        sorted_tasks = sorted(tasks, key=lambda t: t.id)
        
        return [
            {
                'id': task.id,
                'name': task.name,
                'duration': task.duration,
                'tags': sorted(task.tags),  # Sort tags for consistency
                'notes': task.notes
            }
            for task in sorted_tasks
        ]

