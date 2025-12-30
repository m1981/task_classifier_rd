from pathlib import Path
import yaml
from typing import List, Dict, Any
import logging
from models.entities import (
    DatasetContent, Project, Goal
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
        raw_projects = raw_data.get('projects', [])

        # Strict List format
        if not isinstance(raw_projects, list):
            logger.warning(f"Projects data is not a list (got {type(raw_projects)}). Resetting to empty list.")
            raw_projects = []

        logger.debug("Projects format: List")

        for i, p_data in enumerate(raw_projects):
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
        Parses a project using the Unified Stream architecture.
        """
        # 1. Extract Unified Items
        # Pydantic will handle the polymorphism via the 'kind' discriminator
        unified_items = data.get('items', [])

        # 2. Handle sort_order collision
        # We extract sort_order manually so we don't pass it twice
        sort_order = data.get('sort_order', float(data.get('id', 0)))

        # 3. Prepare data for Pydantic
        # Exclude keys we handle manually or legacy keys we want to ignore
        exclude_keys = {'items', 'sort_order', 'tasks', 'resources', 'reference_items'}
        clean_data = {k: v for k, v in data.items() if k not in exclude_keys}

        return Project(
            **clean_data,
            sort_order=sort_order,
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