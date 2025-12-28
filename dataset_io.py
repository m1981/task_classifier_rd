from pathlib import Path
import yaml
from typing import List, Dict, Any
from models.entities import (
    DatasetContent, Project, Goal,
    TaskItem, ResourceItem, ReferenceItem
)


class YamlDatasetLoader:
    def load(self, yaml_file: Path) -> DatasetContent:
        if not yaml_file.exists():
            raise FileNotFoundError(f"File not found: {yaml_file}")

        with open(yaml_file, 'r', encoding='utf-8') as f:
            raw_data = yaml.safe_load(f) or {}

        # 1. Parse Goals (Simple)
        goals = [Goal(**g) for g in raw_data.get('goals', [])]

        # 2. Parse Projects (Complex Migration Logic)
        projects = []
        raw_projects = raw_data.get('projects', {})

        # Handle both Dict (legacy) and List formats if necessary
        project_iter = raw_projects.values() if isinstance(raw_projects, dict) else raw_projects

        for p_data in project_iter:
            projects.append(self._parse_project(p_data))

        return DatasetContent(
            goals=goals,
            projects=projects,
            inbox_tasks=raw_data.get('inbox_tasks', [])
        )

    def _parse_project(self, data: Dict[str, Any]) -> Project:
        """
        Parses a project and migrates legacy 'tasks/resources' lists
        into the unified 'items' stream.
        """
        unified_items = []

        # A. Load existing unified items if they exist
        if 'items' in data:
            # Pydantic will handle the polymorphism via discriminator
            # We just pass the raw dicts
            unified_items.extend(data['items'])

        # B. MIGRATE LEGACY: 'tasks' list
        if 'tasks' in data:
            for t in data['tasks']:
                # Convert legacy task dict to TaskItem dict
                unified_items.append({
                    "kind": "task",
                    "id": str(t.get('id')),
                    "name": t.get('name'),
                    "is_completed": t.get('is_completed', False),
                    "tags": t.get('tags', []),
                    "notes": t.get('notes', '')
                })

        # C. MIGRATE LEGACY: 'resources' list
        if 'resources' in data:
            for r in data['resources']:
                unified_items.append({
                    "kind": "resource",
                    "id": str(r.get('id')),
                    "name": r.get('name'),
                    "is_acquired": r.get('is_acquired', False),
                    "store": r.get('store', 'General'),
                    "link": r.get('link')
                })

        # D. MIGRATE LEGACY: 'reference_items' list
        if 'reference_items' in data:
            for ref in data['reference_items']:
                unified_items.append({
                    "kind": "reference",
                    "id": str(ref.get('id')),
                    "name": ref.get('name'),
                    "content": ref.get('description', '')  # Map description to content
                })

        # Construct the Project with the unified list
        # Note: We exclude the legacy keys so Pydantic doesn't complain
        clean_data = {k: v for k, v in data.items()
                      if k not in ['tasks', 'resources', 'reference_items', 'items']}

        # Migrate legacy status values
        if 'status' in clean_data:
            status_value = clean_data['status']
            # Map legacy 'ongoing' to 'active'
            if status_value == 'ongoing':
                clean_data['status'] = 'active'

        return Project(
            **clean_data,
            items=unified_items  # Pydantic will validate these against the Union
        )


class YamlDatasetSaver:
    def save(self, path: Path, content: DatasetContent) -> None:
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "dataset.yaml"

        # Dump using Pydantic's built-in JSON-compatible dict dumper
        # mode='json' ensures Enums and Datetimes are serialized correctly
        data_dict = content.model_dump(mode='json')

        # Custom YAML configuration for readability
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=1000
            )