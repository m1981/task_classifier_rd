from pathlib import Path
import yaml
from typing import List, Dict, Any
import logging
from models.entities import (
    DatasetContent, Project, Goal,
    TaskItem, ResourceItem, ReferenceItem
)

# Setup Logger
logger = logging.getLogger("DatasetIO")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | DatasetIO | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


class YamlDatasetLoader:
    def load(self, yaml_file: Path) -> DatasetContent:
        logger.info(f"Loading dataset from: {yaml_file}")

        if not yaml_file.exists():
            logger.error(f"File not found: {yaml_file}")
            raise FileNotFoundError(f"File not found: {yaml_file}")

        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f) or {}
        except Exception as e:
            logger.exception("Failed to parse YAML file")
            raise e

        # 1. Parse Goals
        goals_data = raw_data.get('goals', [])
        logger.debug(f"Found {len(goals_data)} goals")
        goals = [Goal(**g) for g in goals_data]

        # 2. Parse Projects
        projects = []
        raw_projects = raw_data.get('projects', {})

        # Handle both Dict (legacy) and List formats
        if isinstance(raw_projects, dict):
            logger.debug("Projects format: Dict (Legacy)")
            project_iter = raw_projects.values()
        else:
            logger.debug("Projects format: List")
            project_iter = raw_projects

        for i, p_data in enumerate(project_iter):
            try:
                projects.append(self._parse_project(p_data))
            except Exception as e:
                logger.error(f"Failed to parse project index {i}: {p_data.get('name', 'Unknown')}")
                logger.exception(e)
                raise e

        logger.info(f"Successfully loaded {len(projects)} projects")

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
        # logger.debug(f"Parsing project: {data.get('name')}")

        unified_items = []

        # A. Load existing unified items if they exist
        if 'items' in data:
            unified_items.extend(data['items'])

        # B. MIGRATE LEGACY: 'tasks' list
        if 'tasks' in data:
            logger.debug(f"Migrating {len(data['tasks'])} legacy tasks for {data.get('name')}")
            for t in data['tasks']:
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
            logger.debug(f"Migrating {len(data['resources'])} legacy resources for {data.get('name')}")
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
            logger.debug(f"Migrating {len(data['reference_items'])} legacy refs for {data.get('name')}")
            for ref in data['reference_items']:
                unified_items.append({
                    "kind": "reference",
                    "id": str(ref.get('id')),
                    "name": ref.get('name'),
                    "content": ref.get('description', '')
                })

        # --- FIX: Handle sort_order collision ---
        # We extract sort_order manually so we don't pass it twice
        sort_order = data.get('sort_order', float(data.get('id', 0)))

        # Construct clean_data excluding keys we handle manually or want to drop
        exclude_keys = ['tasks', 'resources', 'reference_items', 'items', 'sort_order']
        clean_data = {k: v for k, v in data.items() if k not in exclude_keys}

        # Migrate legacy status values
        if 'status' in clean_data:
            status_value = clean_data['status']
            if status_value == 'ongoing':
                clean_data['status'] = 'active'

        return Project(
            **clean_data,
            sort_order=sort_order,  # Explicitly passed
            items=unified_items
        )


class YamlDatasetSaver:
    def save(self, path: Path, content: DatasetContent) -> None:
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / "dataset.yaml"

        logger.info(f"Saving dataset to {file_path}")

        # Sort projects by sort_order before dumping
        # Handle None sort_order gracefully just in case
        content.projects.sort(key=lambda p: (p.goal_id or "", getattr(p, 'sort_order', 0.0)))

        # Dump using Pydantic's built-in JSON-compatible dict dumper
        data_dict = content.model_dump(mode='json')

        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(
                data_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=1000
            )
        logger.info("Save complete.")