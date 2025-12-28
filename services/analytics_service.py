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
        Filters active tasks based on a natural language query,
        providing GOAL context to the AI.
        """
        logger.info(f"🚀 Starting Smart Filter for query: '{user_query}'")

        if not self.repo:
            return {"tasks": [], "prompt": "Error: Repo not loaded", "raw_response": ""}

        # --- 1. BUILD HIERARCHY & CANDIDATE MAP ---
        # We need a map to retrieve objects later: {task_id: TaskItem}
        candidate_map = {}

        # We build a string that looks like a tree for the AI
        hierarchy_lines = []

        # A. Process Goals and their Projects
        for goal in self.repo.data.goals:
            hierarchy_lines.append(f"GOAL: {goal.name} (Status: {goal.status})")
            if goal.description:
                hierarchy_lines.append(f"   Description: {goal.description}")

            # Find projects for this goal
            goal_projects = [p for p in self.repo.data.projects if p.goal_id == goal.id and p.status == "active"]

            if not goal_projects:
                hierarchy_lines.append("   (No active projects)")

            for proj in goal_projects:
                self._append_project_tasks(proj, hierarchy_lines, candidate_map, indent="   ")

            hierarchy_lines.append("")  # Spacer

        # B. Process Orphaned Projects (Maintenance/Misc)
        orphaned_projects = [p for p in self.repo.data.projects if not p.goal_id and p.status == "active"]
        if orphaned_projects:
            hierarchy_lines.append("NO GOAL (Maintenance/Misc):")
            for proj in orphaned_projects:
                self._append_project_tasks(proj, hierarchy_lines, candidate_map, indent="   ")

        hierarchy_str = "\n".join(hierarchy_lines)

        # If no tasks found at all
        if not candidate_map:
            return {"tasks": [], "prompt": "No candidates found", "raw_response": ""}

        # --- 2. BUILD PROMPT ---
        prompt = self.prompt_builder.build_smart_filter_prompt(user_query, hierarchy_str)

        try:
            # --- 3. CALL AI ---
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",
                max_tokens=1024,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=SmartFilterResult,
            )

            result: SmartFilterResult = response.parsed_output

            # --- 4. RE-HYDRATE ---
            # Use the map to get the actual objects back
            matching_tasks = []
            for tid in result.matching_task_ids:
                if tid in candidate_map:
                    matching_tasks.append(candidate_map[tid])

            return {
                "tasks": matching_tasks,
                "prompt": prompt,
                "raw_response": result.model_dump_json(indent=2)
            }

        except Exception as e:
            logger.exception("AI Failed")
            return {"tasks": [], "prompt": prompt, "raw_response": str(e)}

    def _append_project_tasks(self, project, lines, candidate_map, indent):
        """Helper to format tasks and populate the map"""
        # Filter for active TaskItems
        tasks = [i for i in project.items if isinstance(i, TaskItem) and not i.is_completed]

        if not tasks:
            return

        lines.append(f"{indent}PROJECT: {project.name}")
        for t in tasks:
            # Add to map for later retrieval
            candidate_map[t.id] = t

            # Format for AI
            # We include ID so AI can return it
            lines.append(f"{indent}  - [ID: {t.id}] {t.name} | Tags: {t.tags} | Duration: {t.duration}")

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