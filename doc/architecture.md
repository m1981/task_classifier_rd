Here is the fully updated `doc/usage.md` file, incorporating the new architecture, the refined diagrams, and the correct user flows.


# Usage & Architecture

## High-Level Data Flow

The application follows a **Model-View-Service (MVS)** architecture designed for Streamlit's rerun cycle. Data flows from the "Liquid" state (User/AI input) into a "Brick" state (Polymorphic Entities) via a stable Service Layer.

```mermaid
graph RL
    %% Nodes
    User((User))
    YAML[("📂 dataset.yaml\n(Hard Drive)")]
    App["🖥️ Streamlit App\n(Session State)"]
    AI["🤖 Anthropic API\n(Claude Haiku)"]
    
    %% Flow
    YAML -- "1. Load Data" --> App
    App -- "2. Show Current View" --> User
    
    subgraph "The Triage Loop"
        App -- "3. Send Text + Context" --> AI
        AI -- "4. Return Classification" --> App
        App -- "5. Create Draft Proposal" --> User
        User -- "6. Confirm / Edit" --> App
    end
    
    App -- "7. Mutate Domain Model\n(Mark Dirty)" --> App
    User -- "8. Click Save" --> App
    App -- "9. Write to Disk" --> YAML

    %% Styling
    style YAML fill:#f9f,stroke:#333,stroke-width:2px
    style App fill:#bbf,stroke:#333,stroke-width:2px
    style AI fill:#bfb,stroke:#333,stroke-width:2px
```

---

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

---

## Architecture Diagrams

### 1. Class Diagram: The Polymorphic Stream
The core data structure uses a **Unified Stream** (`Project.items`) containing different types of items (`Task`, `Resource`, `Reference`).

```mermaid
classDiagram
    %% --- DOMAIN MODEL (Polymorphic) ---
    class Project {
        +str name
        +List~ProjectItem~ items
    }

    class ProjectItem {
        <<Abstract>>
        +str id
        +str kind
        +str name
    }

    class TaskItem {
        +bool is_completed
        +List~str~ tags
        +str duration
    }

    class ResourceItem {
        +bool is_acquired
        +str store
    }

    class ReferenceItem {
        +str url
        +str content
    }

    %% Inheritance
    ProjectItem <|-- TaskItem
    ProjectItem <|-- ResourceItem
    ProjectItem <|-- ReferenceItem
    Project *-- ProjectItem : Contains

    %% --- SERVICE LAYER ---
    class TriageService {
        +create_draft(text, result) DraftItem
        +apply_draft(draft)
    }

    class DraftItem {
        <<Proposal>>
        +ClassificationResult classification
        +to_entity() ProjectItem
    }

    class ClassificationResult {
        +Enum classification_type
        +str suggested_project
        +str reasoning
    }

    %% Relationships
    TriageService ..> DraftItem : Creates
    DraftItem ..> ProjectItem : Factory for
    TriageService --> Project : Mutates
```

### 2. Sequence Diagram: The Proposal Loop (Triage)
This flow shows how the AI suggests a "Draft," and the user confirms it to create a concrete entity.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as View (Triage)
    participant Service as TriageService
    participant AI as Claude (API)
    participant Repo as Repository

    %% 1. Analysis
    User->>UI: Opens Inbox Item: "Buy white paint"
    UI->>Service: classify("Buy white paint")
    Service->>AI: Prompt (JSON Schema)
    AI-->>Service: {type: "RESOURCE", project: "Home Reno"}
    
    %% 2. The Proposal (New Step)
    Service->>Service: create_draft(result)
    Service-->>UI: Returns DraftItem
    UI->>User: Display Proposal Card:\n"Type: Shopping | Project: Home Reno"

    %% 3. Confirmation (Polymorphic Creation)
    User->>UI: Click "Confirm"
    UI->>Service: apply_draft(draft)
    Service->>Service: item = draft.to_entity() -> ResourceItem
    Service->>Repo: Projects["Home Reno"].items.append(item)
    Service->>Repo: mark_dirty()
    
    %% 4. UI Update
    Service-->>UI: Success
    UI->>UI: st.rerun()
```

### 3. Sequence Diagram: Explicit Persistence
This flow demonstrates the "Dirty Flag" pattern. Data is only written to disk when explicitly requested.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant UI as Sidebar
    participant Repo as Repository
    participant Disk as dataset.yaml

    %% 1. State Check
    Note over UI, Repo: User has made changes
    Repo-->>UI: is_dirty = True
    UI->>User: Show "🔴 Unsaved Changes"

    %% 2. Explicit Save
    User->>UI: Click "Save Changes"
    UI->>Repo: save()
    
    %% 3. Serialization
    Repo->>Repo: model_dump(mode='json')
    Repo->>Disk: Write YAML
    Repo->>Repo: is_dirty = False
    
    %% 4. Feedback
    Repo-->>UI: Success
    UI->>User: Show "🟢 Saved"
```
