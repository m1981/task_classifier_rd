## UI Layout & Navigation

### 1. The Sidebar (System Control)
The sidebar persists across all modes and handles the "Meta" application state.

*   **Dataset Selector:** A Dropdown menu listing files found in `./data/*.yaml`.
    *   *Options:* `home_renovation.yaml`, `coding_projects.yaml`, `test_edge_cases.yaml`.
*   **Status Indicator:**
    *   🟢 Saved
    *   🔴 Unsaved Changes (Dirty)
*   **Global Actions:**
    *   [Save Changes] (Enabled only when Dirty)
    *   [Reload/Revert] (Reloads from disk, discarding changes)

### 2. Main Content Area
Changes based on the selected Mode (Inbox / Planning / Engage).

```mermaid
graph RL
    %% Nodes
    User((User))
    YAML[("📂 dataset.yaml\n(Hard Drive)")]
    App["🖥️ Streamlit App\n(Session State)"]
    AI["🤖 Anthropic API\n(Claude Haiku)"]
    
    %% Flow
    YAML -- "1. Load Data" --> App
    App -- "2. Show Current Task" --> User
    
    subgraph "The Triage Loop"
        App -- "3. Send Task + Project List" --> AI
        AI -- "4. Return ClassificationResult\n(Type: Task/Shop/Ref)" --> App
        User -- "5. Add, Skip, Edit, Create project" --> App
    end
    
    App -- "6. Mutate Session State\n(Mark Dirty)" --> App
    User -- "7. Click Save" --> App
    App -- "8. Write to Disk" --> YAML

    %% Styling
    style YAML fill:#f9f,stroke:#333,stroke-width:2px
    style App fill:#bbf,stroke:#333,stroke-width:2px
    style AI fill:#bfb,stroke:#333,stroke-width:2px
```

```mermaid

classDiagram
    class App_UI {
        +st.session_state
        +is_dirty : bool
        +render_inbox()
        +handle_confirm_click()
    }

    class TaskClassifier {
        +classify_single(text, project_list) ClassificationResult
    }

    class ClassificationResult {
        +Enum type (Task|Shop|Ref|NewProj)
        +str target_project
        +str refined_text
        +str reasoning
    }

    class DatasetManager {
        +load()
        +save()
    }

    %% Relationships
    App_UI --> TaskClassifier : Calls
    TaskClassifier ..> ClassificationResult : Returns
    App_UI --> DatasetManager : Persists
```

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as app.py
    participant TC as TaskClassifier
    participant AI as Claude (API)
    participant DM as DatasetManager

    %% 1. Analysis
    User->>UI: Opens Inbox Item: "Buy white paint"
    UI->>TC: classify("Buy white paint", ["Home Reno", "Work"])
    TC->>AI: Prompt (JSON Schema)
    AI-->>TC: {type: "SHOPPING", project: "Home Reno"}
    TC-->>UI: ClassificationResult
    UI->>User: Display Card: "Add to Home Reno / Shopping?"

    %% 2. Mutation (Memory Only)
    User->>UI: Click "Confirm"
    UI->>UI: Projects["Home Reno"].shopping.append("White paint")
    UI->>UI: Inbox.remove("Buy white paint")
    UI->>UI: session_state.is_dirty = True
    UI->>UI: st.rerun()

    %% 3. Persistence (Explicit)
    User->>UI: Click "Save Changes (1)"
    UI->>DM: save(session_state.data)
    DM->>Disk: Write YAML
    UI->>UI: session_state.is_dirty = False
    UI->>User: Toast "Saved!"
```

```mermaid

sequenceDiagram
    autonumber
    actor User
    participant UI as app.py
    participant TC as TaskClassifier
    participant AI as Claude (API)
    participant DM as DatasetManager
    participant Disk as dataset.yaml

    %% 1. Initialization
    User->>UI: Click "Load Dataset"
    UI->>DM: load_dataset("home_renovation")
    DM->>Disk: Read YAML
    Disk-->>DM: Raw Data
    DM-->>UI: Returns DatasetContent
    note right of UI: Inbox: ["Fix faucet", ...]

    %% 2. The Analysis Loop (Single Item)
    UI->>UI: Get current_task = inbox_tasks[0]
    UI->>TC: classify_single(SingleTaskClassificationRequest)
    TC->>AI: messages.parse(prompt, response_model=ClassificationResult)
    AI-->>TC: Parsed Pydantic Object
    TC-->>UI: ClassificationResponse
    UI->>User: Show Card [Add to Plumbing]

    %% 3. The Mutation (In-Memory)
    User->>UI: Click "Add"
    UI->>UI: Project("Plumbing").tasks.append("Fix faucet")
    UI->>UI: Inbox.remove("Fix faucet")
    UI->>UI: st.rerun()

    %% 4. Persistence
    User->>UI: Click "Save"
    UI->>DM: save_command.execute()
    DM->>Disk: Overwrite dataset.yaml
```


```mermaid

classDiagram
    %% --- ACTIVE CLASSES (Green) ---
    class DatasetManager {
        +load_dataset()
        +save_dataset()
    }

    class TaskClassifier {
        +classify_single(request)
    }

    class PromptBuilder {
        +build_single_task_prompt()
    }

    class SaveDatasetCommand {
        +execute()
    }

    class DatasetProjector {
        +from_ui_state()
    }

    class SingleTaskClassificationRequest {
        +str task_text
        +List~str~ available_projects
    }

    class ClassificationResult {
        <<Pydantic Model>>
        +str suggested_project
        +float confidence
        +str reasoning
    }

    %% --- REMOVED/UNUSED CLASSES (Red) ---
    class ResponseParser {
        %% Replaced by Anthropic Structured Outputs
    }

    class BatchClassificationRequest {
        %% Replaced by SingleTaskClassificationRequest
    }

    %% --- RELATIONSHIPS ---
    
    %% Active Flow
    TaskClassifier --> PromptBuilder : Uses
    TaskClassifier ..> SingleTaskClassificationRequest : Consumes
    TaskClassifier ..> ClassificationResult : Returns (via Pydantic)
    
    SaveDatasetCommand --> DatasetManager : Uses
    SaveDatasetCommand --> DatasetProjector : Uses

    %% --- STYLING ---
    style DatasetManager fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style TaskClassifier fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style PromptBuilder fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style SaveDatasetCommand fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style DatasetProjector fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style SingleTaskClassificationRequest fill:#e6fffa,stroke:#28a745,stroke-width:2px
    style ClassificationResult fill:#e6fffa,stroke:#28a745,stroke-width:2px
    
    style ResponseParser fill:#fff5f5,stroke:#dc3545,stroke-width:2px
    style BatchClassificationRequest fill:#fff5f5,stroke:#dc3545,stroke-width:2px
```