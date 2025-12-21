from typing import List
from models.entities import TaskItem, ProjectStatus
from models.ai_schemas import SmartFilterResult
from services.repository import YamlRepository
from services.services import PromptBuilder


class AnalyticsService:
    def __init__(self, repo: YamlRepository, client, prompt_builder: PromptBuilder):
        self.repo = repo
        self.client = client
        self.prompt_builder = prompt_builder

    def smart_filter_tasks(self, user_query: str) -> List[TaskItem]:
        """
        Filters active tasks based on a natural language query.
        """
        # 1. Gather Candidates (All active tasks from active projects)
        candidates = []
        # Handle case where repo might be None during init
        if not self.repo:
            return []

        for p in self.repo.data.projects:
            if p.status != ProjectStatus.ACTIVE: continue
            for item in p.items:
                if isinstance(item, TaskItem) and not item.is_completed:
                    candidates.append(item)

        if not candidates:
            return []

        # 2. Build Prompt Payload
        # We create a lightweight string representation for the AI
        task_list_str = "\n".join([
            f"- ID: {t.id} | Name: {t.name} | Tags: {t.tags} | Duration: {t.duration}"
            for t in candidates
        ])

        # 3. Build Prompt
        prompt = self.prompt_builder.build_smart_filter_prompt(user_query, task_list_str)

        try:
            # 4. Call AI with Structured Output
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",  # Or your preferred model
                max_tokens=1024,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=SmartFilterResult,
            )

            result: SmartFilterResult = response.parsed_output

            # 5. Re-hydrate Objects
            # Map the returned IDs back to the actual TaskItem objects
            matching_tasks = [
                t for t in candidates
                if t.id in result.matching_task_ids
            ]

            return matching_tasks

        except Exception as e:
            print(f"AI Error: {e}")
            return []  # Fail gracefully