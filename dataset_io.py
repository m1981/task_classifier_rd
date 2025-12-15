from abc import ABC, abstractmethod
from pathlib import Path
from typing import List
import yaml
from enum import Enum

# Import all entities to ensure we can instantiate them
from models.entities import (
    DatasetContent,
    Project,
    Task,
    ProjectResource,
    ReferenceItem,
    ResourceType,
    ProjectStatus,
    Goal
)

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
        goals = self._parse_goals(data.get('goals', []))

        return DatasetContent(
            projects=projects,
            inbox_tasks=inbox_tasks,
            goals=goals
        )
    
    def _parse_goals(self, goals_data: List[dict]) -> List[Goal]:
        goals = []
        for g in goals_data:
            goals.append(Goal(
                id=g.get('id'),
                name=g.get('name'),
                description=g.get('description', ''),
                status=g.get('status', 'active')
            ))
        return goals

    def _parse_projects(self, projects_data: dict) -> List[Project]:
        projects = []
        for project_data in projects_data.values():
            # Handle Status: Convert string back to Enum if possible, else default
            status_str = project_data.get('status', 'active')
            try:
                status_enum = ProjectStatus(status_str)
            except ValueError:
                # Fallback for legacy data like "ongoing"
                status_enum = ProjectStatus.ACTIVE

            # Parse Tasks
            tasks = self._parse_tasks(project_data.get('tasks', []))

            # Parse Resources (Shopping/Prep)
            resources = []
            for r in project_data.get('resources', []):
                # Handle ResourceType Enum
                try:
                    r_type = ResourceType(r.get('type', 'to_buy'))
                except ValueError:
                    r_type = ResourceType.TO_BUY

                resources.append(ProjectResource(
                    id=r.get('id'),
                    name=r.get('name'),
                    link=r.get('link'),
                    type=r_type,
                    is_acquired=r.get('is_acquired', False),
                    store=r.get('store', 'General')
                ))

            # Parse Reference Items
            refs = []
            for ref in project_data.get('reference_items', []):
                refs.append(ReferenceItem(
                    id=ref.get('id'),
                    name=ref.get('name'),
                    description=ref.get('description', '')
                ))

            projects.append(Project(
                id=project_data['id'],
                name=project_data['name'],
                status=status_enum,
                goal_id=project_data.get('goal_id'),
                tags=project_data.get('tags', []),
                tasks=tasks,
                resources=resources,
                reference_items=refs
            ))
        return projects
    
    def _parse_tasks(self, tasks_data: List[dict]) -> List[Task]:
        tasks = []
        for task_data in tasks_data:
            tasks.append(Task(
                id=str(task_data['id']),
                name=task_data['name'],
                duration=task_data.get('duration', 'unknown'),
                tags=task_data.get('tags', []),
                notes=task_data.get('notes', ''),
                is_completed=task_data.get('is_completed', False)
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
            'goals': self._format_goals(content.goals),
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

    def _format_goals(self, goals: List[Goal]) -> List[dict]:
        return [
            {
                'id': g.id,
                'name': g.name,
                'description': g.description,
                'status': g.status
            } for g in goals
        ]

    def _format_projects(self, projects: List[Project]) -> dict:
        """Format projects with consistent ordering"""
        projects_data = {}
        
        # Sort projects by ID for consistent ordering
        sorted_projects = sorted(projects, key=lambda p: p.id)
        
        for project in sorted_projects:
            # Use consistent key generation
            key = project.name.lower().replace(' ', '_').replace('/', '_')

            # FIX: Convert Enum to string value
            status_val = project.status.value if isinstance(project.status, Enum) else project.status

            projects_data[key] = {
                'id': project.id,
                'name': project.name,
                'status': status_val, # <--- FIXED HERE
                'goal_id': project.goal_id,
                'tags': sorted(project.tags),
                'tasks': self._format_tasks(project.tasks),

                # NEW: Save Resources
                'resources': [
                    {
                        'id': r.id,
                        'name': r.name,
                        'type': r.type.value if isinstance(r.type, Enum) else r.type, # Handle Enum
                        'store': r.store,
                        'is_acquired': r.is_acquired,
                        'link': r.link
                    } for r in project.resources
                ],

                # NEW: Save References
                'reference_items': [
                    {
                        'id': r.id,
                        'name': r.name,
                        'description': r.description
                    } for r in project.reference_items
                ]
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
                'tags': sorted(task.tags),
                'notes': task.notes,
                'is_completed': task.is_completed
            }
            for task in sorted_tasks
        ]

