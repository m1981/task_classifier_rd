from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import yaml
from models import DatasetContent, Project

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
            projects.append(Project(
                id=project_data['id'],
                name=project_data['name'],
                status=project_data.get('status', 'ongoing'),
                tags=project_data.get('tags', [])
            ))
        return projects

class YamlDatasetSaver(DatasetSaver):
    def save(self, dataset_path: Path, content: DatasetContent) -> None:
        dataset_path.mkdir(parents=True, exist_ok=True)
        
        yaml_data = {
            'projects': self._format_projects(content.projects),
            'inbox_tasks': content.inbox_tasks
        }
        
        yaml_file = dataset_path / "dataset.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            yaml.dump(yaml_data, f, default_flow_style=False, allow_unicode=True, indent=2)
    
    def _format_projects(self, projects: List[Project]) -> dict:
        projects_data = {}
        for project in projects:
            key = project.name.lower().replace(' ', '_')
            projects_data[key] = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
                'tags': project.tags
            }
        return projects_data

class LegacyDatasetLoader(DatasetLoader):
    def load(self, dataset_path: Path) -> DatasetContent:
        projects = self._load_projects(dataset_path / "projects.txt")
        inbox_tasks = self._load_inbox_tasks(dataset_path / "inbox_tasks.txt")
        return DatasetContent(projects=projects, inbox_tasks=inbox_tasks)
    
    def _load_projects(self, file_path: Path) -> List[Project]:
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
    
    def _load_inbox_tasks(self, file_path: Path) -> List[str]:
        if not file_path.exists():
            return []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]