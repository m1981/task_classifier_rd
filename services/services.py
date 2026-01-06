from pathlib import Path
from typing import List, Optional
import anthropic
import json
from models.ai_schemas import ClassificationType, EnrichmentResult, BatchEnrichmentResponse
from models.entities import TagKnowledgeBase

# Import Domain Models and DTOs
from models import (
    DatasetContent,
    Project,
    ClassificationResult,
    ClassificationRequest,
    ClassificationResponse,
    SystemConfig,
    SingleTaskClassificationRequest,
    TagKnowledgeBase
)

from dataset_io import YamlDatasetLoader, YamlDatasetSaver

class DatasetManager:
    def __init__(self, base_path: Path = Path("data/datasets")):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._yaml_loader = YamlDatasetLoader()
        self._yaml_saver = YamlDatasetSaver()

    def load_dataset(self, name: str) -> DatasetContent:
        """Load dataset - try YAML first"""
        dataset_path = self.base_path / name
        yaml_file = dataset_path / "dataset.yaml"

        if yaml_file.exists():
            return self._yaml_loader.load(yaml_file)
        else:
            raise FileNotFoundError(f"Dataset '{name}' not found")

    def save_dataset(self, name: str, content: DatasetContent) -> dict:
        """Save dataset with validation and detailed result"""
        validation_error = self._validate_dataset_name(name)
        if validation_error:
            return {"success": False, "error": validation_error, "type": "validation"}

        try:
            self._yaml_saver.save(self.base_path / name, content)
            return {"success": True, "message": f"Dataset '{name}' saved successfully"}
        except PermissionError:
            return {"success": False, "error": "Permission denied - check folder permissions", "type": "permission"}
        except OSError as e:
            return {"success": False, "error": f"File system error: {str(e)}", "type": "filesystem"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}", "type": "unknown"}

    def _validate_dataset_name(self, name: str) -> str:
        if not name or not name.strip():
            return "Dataset name cannot be empty"
        if len(name) > 50:
            return "Dataset name too long (max 50 characters)"
        if not name.replace('_', '').replace('-', '').isalnum():
            return "Dataset name can only contain letters, numbers, hyphens, and underscores"
        return ""

    def list_datasets(self) -> List[str]:
        if not self.base_path.exists():
            return []
        return [d.name for d in self.base_path.iterdir() if d.is_dir()]


class PromptBuilder:
    """
    Domain Service: Constructs prompts for the AI.
    Now simplified because we rely on Structured Outputs for formatting.
    """

    def __init__(self, prompts_dir: Path = Path("data/prompts")):
        self.prompts_dir = prompts_dir
        self.config = SystemConfig()

    def build_triage_prompt(self, task_text: str, context_hierarchy: str, existing_tags: List[str] = None) -> str:
        # 1. Get the Rich Markdown Table
        tag_knowledge_table = TagKnowledgeBase.get_markdown_table()

        # 2. Get simple list for validation
        defaults = TagKnowledgeBase.get_all_tags()
        available_tags_list = list(set(defaults + (existing_tags or [])))

        # --- FIX: Define tags_str ---
        tags_str = ", ".join(f'"{t}"' for t in available_tags_list)
        # ----------------------------

        return f"""
        Act as my personal advisor and Getting Things Done methodology expert.
        Please analzye my item from inbox and follow flowchart and help me decide wher to put it.
        Respond in JSON based on structure I prepered for you in tools.
        
        INCOMING ITEM: "{task_text}"
        
        INSTRUCTIONS:
        - Return ONLY the JSON object.
        - Use double quotes for JSON.
        - Apply tags strictly from the AVAILABLE TAGS list.
        - Select 'estimated_duration' STRICTLY from the ALLOWED DURATIONS list.
        
        - URL HANDLING:
          1. Extract the page title/topic into 'refined_text'.
          2. Copy the EXACT URL into 'notes'.
          3. Do not strip UTM parameters unless they are excessively long.

        CONTEXT (Goals > Projects > Existing Items):
        {context_hierarchy}
        
        AVAILABLE TAGS: [{tags_str}]
        ALLOWED DURATIONS: {self.config.ALLOWED_DURATIONS}

```mermaid
flowchart TD
    %% --- STYLES ---
    classDef input fill:#333,stroke:#fff,color:#fff,stroke-width:2px
    classDef ai fill:#E3F2FD,stroke:#1565C0,color:#0D47A1
    classDef logic fill:#FFF3E0,stroke:#EF6C00,color:#E65100
    classDef user fill:#E8F5E9,stroke:#2E7D32,color:#1B5E20
    classDef db fill:#F3E5F5,stroke:#7B1FA2,color:#4A148C

    %% --- START ---
    Start([📥 Inbox Item]) --> AI_Analysis
    class Start input

    %% --- AI BRAIN ---
    subgraph AI_Analysis ["🤖 AI Analysis (The Prompt)"]
        direction TB
        Parse["1. Analyze Intent"]
        Context["2. Scan Project Tree"]
        
        Parse --> Context
        Context --> Decision{{Actionable}}
    end
    class Parse,Context,Decision ai

    %% --- LOGIC BRANCHES ---
    Decision -- "NO (Info/URL)" --> RefLogic["Type: REFERENCE"]
    Decision -- "NO (Someday)" --> IncLogic["Type: INCUBATE"]
    Decision -- "YES (Do/Buy)" --> ActLogic["Type: TASK / RESOURCE"]

    class RefLogic,IncLogic,ActLogic logic

    %% --- ROUTING LOGIC (The Our Logic Part) ---
    subgraph Routing ["🧠 Project Routing Logic"]
        direction TB
        
        %% Reference Path
        RefLogic --> CheckRefMatch{{"Topic Matches<br/>Existing Project?"}}
        CheckRefMatch -- YES --> AssignRef["Target: Existing Project"]
        CheckRefMatch -- NO --> AssignGen["Target: 'General'"]
        
        %% Incubate Path
        IncLogic --> CheckIncMatch{{"Topic Matches<br/>Existing Project?"}}
        CheckIncMatch -- YES --> AssignInc["Target: Existing Project"]
        CheckIncMatch -- NO --> AssignSomeday["Target: 'Someday/Maybe'"]

        %% Actionable Path
        ActLogic --> CheckActMatch{{"Topic Matches<br/>Existing Project?"}}
        CheckActMatch -- YES --> AssignAct["Target: Existing Project"]
        CheckActMatch -- NO --> NewProjLogic{{"Is it Multi-step?"}}
        NewProjLogic -- YES --> AssignNew["Target: 'Unmatched'<br/>(Suggest New Project)"]
        NewProjLogic -- NO --> AssignMisc["Target: 'General'<br/>(Single Orphan Task)"]
    end

    class Commit,Rotate,Delete,CreateProj db

    %% --- CRITICAL LOGIC HIGHLIGHT ---
    note_ref["<b>CRITICAL LOGIC:</b><br/>References that don't fit<br/>a project go to 'General'.<br/>They NEVER trigger<br/>'New Project'."] -.-> AssignGen
    
    note_task["<b>CRITICAL LOGIC:</b><br/>Only Actionable items<br/>can trigger 'Unmatched'<br/>to prompt a New Project."] -.-> AssignNew
    
"""

    def build_enrichment_prompt(self, item_name: str, project_name: str, goal_name: str,
                                project_context_str: str, extra_tags: List[str]) -> str:

        # ENRICHMENT: Defaults + User Added Tags (Extra)
        defaults = TagKnowledgeBase.get_all_tags()
        # Merge and Deduplicate
        combined_tags = list(set(defaults + extra_tags))

        return f"""
        Please act GTD techniq expert. Please help me to enrich my item based on below instruction.
        
        ITEM TO ENRICH: "{item_name}"
        CURRENT PROJECT: "{project_name}"
        GOAL CONTEXT: "{goal_name}"
        
        PROJECT CONTEXT (Other items in this project for pattern matching):
        {project_context_str}
        
        AVAILABLE TAGS: {combined_tags}
        ALLOWED DURATIONS: {self.config.ALLOWED_DURATIONS}

        INSTRUCTIONS:
        1. Analyze the item in the context of its project.
        2. Assign appropriate tags (Context, Energy, Effort) ONLY from the AVAILABLE TAGS list.
        3. Estimate duration if it's a task.
        4. If the item name contains a URL, extract it to notes.
        5. Determine if this is really a Task, or if it should be a Resource (Shopping) or Reference.
        """

    def build_batch_enrichment_prompt(self, target_items_str: str, project_name: str, goal_name: str,
                                      project_context_str: str, extra_tags: List[str]) -> str:

        # 1. Get the Rich Markdown Table
        tag_knowledge_table = TagKnowledgeBase.get_markdown_table()

        # 2. Get simple list for validation
        defaults = TagKnowledgeBase.get_all_tags()
        combined_tags = list(set(defaults + extra_tags))

        return f"""
        Please help me as my GTD advisor. Please analzye my project and its goal and assign duration and tags to my project items.

        CURRENT PROJECT\n"{project_name}"
        GOAL CONTEXT\t"{goal_name}"

        PROJECT:
        {project_context_str}

        ITEMS TO ENRICH (Format: ID | Name):
        {target_items_str}
        
        TAGGING STRATEGY (COGNITIVE STATES):
        You must select tags based on the intersection of **Mode** and **Energy**.
        
        {tag_knowledge_table}
        
        INSTRUCTIONS:
        1. For each item, first determine the **Mode** (Where am I?) and **Energy** (How hard is it?).
        2. Use those determinations to select the single best **Tag** from the table.
        3. Example: If Mode="Computer" and Energy="Deep Logic", you MUST select "@Maker-Code".
        ...
        """

class TaskClassifier:
    def __init__(self, client, prompt_builder: PromptBuilder):
        self.client = client
        self.prompt_builder = prompt_builder

    def classify_single(self, request: SingleTaskClassificationRequest) -> ClassificationResponse:
        prompt = self.prompt_builder.build_triage_prompt(
            request.task_text,
            request.available_projects,
            request.existing_tags
        )

        # Capture the "Form" definition we are sending
        tool_schema = ClassificationResult.model_json_schema()

        try:
            # Use the .parse() method for automatic Pydantic validation
            response = self.client.beta.messages.parse(
                model="claude-haiku-4-5",
                max_tokens=8024,
                temperature=0,
                betas=["structured-outputs-2025-11-13"],
                messages=[{"role": "user", "content": prompt}],
                output_format=ClassificationResult,
            )

            # The SDK returns a parsed object directly
            parsed_result = response.parsed_output

            return ClassificationResponse(
                results=[parsed_result],
                prompt_used=prompt,
                tool_schema=tool_schema,
                raw_response=parsed_result.model_dump_json(indent=2)
            )

        except Exception as e:
            error_result = ClassificationResult(
                reasoning=f"AI Error: {str(e)}",
                classification_type=ClassificationType.TASK,
                refined_text=request.task_text,
                suggested_project="Unmatched",
                confidence=0.0,
                extracted_tags=[]
            )
            return ClassificationResponse(
                results=[error_result],
                prompt_used=prompt,
                tool_schema=tool_schema,
                raw_response=str(e)
            )

    def enrich_single_item(self, item_name: str, project_name: str, goal_name: str,
                           project_context_str: str, extra_tags: List[str]) -> EnrichmentResult:

        # Pass new context arguments to prompt builder
        prompt = self.prompt_builder.build_enrichment_prompt(
            item_name, project_name, goal_name, project_context_str, extra_tags
        )
        tool_schema = EnrichmentResult.model_json_schema()

        response = self.client.beta.messages.parse(
            model="claude-haiku-4-5",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
            output_format=EnrichmentResult,
        )

        debug_data = {
            "prompt": prompt,
            "response": response.parsed_output.model_dump_json(indent=2),
            "schema": tool_schema
        }

        return response.parsed_output, debug_data

    def enrich_batch_items(self, target_items_str: str, project_name: str, goal_name: str,
                           project_context_str: str, extra_tags: List[str]) -> BatchEnrichmentResponse:

        prompt = self.prompt_builder.build_batch_enrichment_prompt(
            target_items_str, project_name, goal_name, project_context_str, extra_tags
        )

        tool_schema = BatchEnrichmentResponse.model_json_schema()

        response = self.client.beta.messages.parse(
            model="claude-haiku-4-5",
            max_tokens=4096,  # Increased token limit for batch
            messages=[{"role": "user", "content": prompt}],
            output_format=BatchEnrichmentResponse,
        )

        return response.parsed_output, {
            "prompt": prompt,
            "response": response.parsed_output.model_dump_json(),
            "schema": tool_schema
        }