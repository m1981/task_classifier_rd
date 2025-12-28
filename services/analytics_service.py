from typing import List, Optional
from datetime import datetime, timedelta
from models.entities import TaskItem, ProjectStatus
from models.ai_schemas import SmartFilterResult
from services.repository import YamlRepository
from services.services import PromptBuilder
from views.common import get_logger # Import logger

logger = get_logger("AnalyticsService")

class AnalyticsService:
    def __init__(self, repo: YamlRepository, client, prompt_builder: PromptBuilder):
        self.repo = repo
        self.client = client
        self.prompt_builder = prompt_builder

    def smart_filter_tasks(self, user_query: str) -> dict:
        """
        Filters active tasks based on a natural language query.
        Returns a dict with keys: 'tasks', 'prompt', 'raw_response'
        """
        logger.info(f"🚀 Starting Smart Filter for query: '{user_query}'")

        # 1. Gather Candidates
        candidates = []
        if not self.repo:
            logger.error("Repository is None! Cannot fetch tasks.")
            return {"tasks": [], "prompt": "Error: Repo not loaded", "raw_response": ""}

        for p in self.repo.data.projects:
            if p.status != ProjectStatus.ACTIVE: continue
            for item in p.items:
                if isinstance(item, TaskItem) and not item.is_completed:
                    candidates.append(item)

        logger.info(f"Found {len(candidates)} active candidate tasks across all projects.")

        if not candidates:
            logger.warning("No candidates found. Returning empty result.")
            return {"tasks": [], "prompt": "No candidates found", "raw_response": ""}

        # 2. Build Prompt Payload
        task_list_str = "\n".join([
            f"- ID: {t.id} | Name: {t.name} | Tags: {t.tags} | Duration: {t.duration}"
            for t in candidates
        ])

        # 3. Build Prompt
        prompt = self.prompt_builder.build_smart_filter_prompt(user_query, task_list_str)
        logger.debug("Prompt constructed successfully.")

        try:
            # 4. Call AI
            logger.info("Sending request to Anthropic API...")
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",
                max_tokens=1024,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=SmartFilterResult,
            )

            result: SmartFilterResult = response.parsed_output
            logger.info(f"AI Response received. Matching IDs: {len(result.matching_task_ids)}")
            logger.debug(f"AI Reasoning: {result.reasoning}")

            # 5. Re-hydrate Objects
            matching_tasks = [
                t for t in candidates
                if t.id in result.matching_task_ids
            ]

            logger.info(f"✅ Returning {len(matching_tasks)} hydrated task objects.")

            return {
                "tasks": matching_tasks,
                "prompt": prompt,
                "raw_response": result.model_dump_json(indent=2)
            }

        except Exception as e:
            logger.exception("❌ AI Processing Failed") # Logs full stack trace
            return {"tasks": [], "prompt": prompt, "raw_response": str(e)}

    def estimate_project_completion(self, project_id: int) -> str:
        """
        Estimate completion time for a project based on incomplete task durations.
        Returns a human-readable string like "2h 30min" or "Unknown".
        """
        if not self.repo:
            return "Unknown"
        
        project = self.repo.find_project(project_id)
        if not project:
            return "Project not found"
        
        # Sum up durations of incomplete tasks
        total_minutes = 0
        incomplete_tasks = [item for item in project.items if isinstance(item, TaskItem) and not item.is_completed]
        
        for task in incomplete_tasks:
            duration_str = task.duration.lower()
            # Parse duration strings like "15min", "1h", "2h 30min", etc.
            if "h" in duration_str or "hour" in duration_str:
                # Extract hours
                hours_part = duration_str.split("h")[0].split("hour")[0].strip()
                try:
                    hours = float(hours_part)
                    total_minutes += int(hours * 60)
                except ValueError:
                    pass
            
            if "min" in duration_str or "minute" in duration_str:
                # Extract minutes
                min_part = duration_str.split("min")[0].split("minute")[0].strip()
                # Handle cases like "2h 30min" where we need the part after "h"
                if "h" in duration_str:
                    parts = duration_str.split("h")
                    if len(parts) > 1:
                        min_part = parts[1].split("min")[0].strip()
                try:
                    minutes = float(min_part)
                    total_minutes += int(minutes)
                except ValueError:
                    pass
        
        if total_minutes == 0:
            return "Unknown"
        
        # Format as human-readable string
        hours = total_minutes // 60
        minutes = total_minutes % 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}min"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}min"

    def review_recent_work(self, goal_id: Optional[str] = None) -> str:
        """
        Analyze recently completed work and provide strategic review.
        If goal_id is provided, focuses on that goal's projects.
        """
        if not self.repo:
            return "No data available for review."
        
        # Get completed tasks from the last 7 days
        cutoff_date = datetime.now() - timedelta(days=7)
        completed_tasks = []
        
        projects_to_review = self.repo.data.projects
        if goal_id:
            projects_to_review = [p for p in projects_to_review if p.goal_id == goal_id]
        
        for project in projects_to_review:
            for item in project.items:
                if isinstance(item, TaskItem) and item.is_completed and item.completed_at:
                    # Parse completed_at if it's a string
                    if isinstance(item.completed_at, str):
                        try:
                            completed_dt = datetime.fromisoformat(item.completed_at.replace('Z', '+00:00'))
                        except:
                            continue
                    else:
                        completed_dt = item.completed_at
                    
                    if completed_dt >= cutoff_date:
                        completed_tasks.append({
                            'task': item.name,
                            'project': project.name,
                            'completed_at': completed_dt
                        })
        
        if not completed_tasks:
            return "No completed tasks in the last 7 days to review."
        
        # Build prompt for AI review
        tasks_summary = "\n".join([
            f"- {t['task']} (Project: {t['project']})"
            for t in completed_tasks
        ])
        
        goals_summary = ""
        if goal_id:
            goal = next((g for g in self.repo.data.goals if g.id == goal_id), None)
            if goal:
                goals_summary = f"\n\nGoal: {goal.name}\n{goal.description}"
        
        prompt = f"""You are a productivity coach reviewing a user's recent work.

Completed tasks in the last 7 days:
{tasks_summary}
{goals_summary}

Provide a brief strategic review (2-3 sentences) that:
1. Acknowledges what was accomplished
2. Notes any patterns or themes
3. Suggests if the work aligns with their goals

Be encouraging and constructive."""

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text
        except Exception as e:
            return f"Unable to generate review: {str(e)}"