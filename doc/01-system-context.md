# System Context: AI-Powered GTD

## Core Philosophy
We follow the 5-step GTD method, augmented by AI to reduce the cognitive load of "Clarifying" and "Organizing."

## System Architecture
*   **Runtime:** Python 3.10+
*   **Interface:** Streamlit
*   **Persistence:** Local File System (YAML)

## Data Organization (The "Multi-Tenant" Local Approach)
The application does not use a single database. Instead, it operates on **Dataset Fixtures**.
*   **Directory:** `./data/`
*   **Behavior:** The app loads *one* YAML file into memory at a time.
*   **Use Case:** This allows the user to keep "Work" and "Personal" completely separate, or allows developers to load "Test Fixtures" to validate AI behavior.

## The 3 Modes of Operation
1.  **Inbox Mode (Capture & Clarify):** Rapid entry and AI-assisted sorting.
2.  **Planning Mode (Organize & Review):** Aligning Projects with Goals and managing support lists.
3.  **Action Mode (Engage):** A filtered view of what to do *now*.

```mermaid
graph TD
    %% --- STYLES ---
    classDef view fill:#E3F2FD,stroke:#1565C0,stroke-width:2px,color:#0D47A1
    classDef service fill:#E8F5E9,stroke:#2E7D32,stroke-width:2px,color:#1B5E20
    classDef model fill:#FFF3E0,stroke:#EF6C00,stroke-width:2px,color:#E65100
    classDef state fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px,color:#4A148C
    classDef storage fill:#ECEFF1,stroke:#455A64,stroke-width:2px,color:#263238

    %% --- ACTORS ---
    User((User))

    %% --- LAYER 1: THE VIEW (Ephemeral) ---
    subgraph View_Layer ["🖥️ VIEW LAYER (Re-runs on Interaction)"]
        direction TB
        InboxView["📥 Inbox View"]
        PlanView["🎯 Planning View"]
        
        subgraph Forms ["Input Mechanisms"]
            ManualForm["📝 Manual Form\n(Goal / Item)"]
            AIButton["🤖 AI Triage\n(Button)"]
        end
    end

    %% --- LAYER 2: THE STATE (The Bridge) ---
    subgraph State_Layer ["🧠 SESSION STATE (The Container)"]
        SessionState[("st.session_state")]
        DirtyFlag["🚩 is_dirty (bool)"]
        Proposal["💡 current_proposal\n(DraftItem)"]
    end

    %% --- LAYER 3: THE SERVICE (The Brain) ---
    subgraph Service_Layer ["⚙️ SERVICE LAYER (Stable / Cached)"]
        TriageService["TriageService"]
        PlanService["PlanningService"]
        
        subgraph Logic ["The Logic Core"]
            AI_Engine["🤖 AI Engine\n(Claude)"]
            ProposalEngine["Draft Builder\n(Liquid -> Brick)"]
        end
    end

    %% --- LAYER 4: THE MODEL (The Foundation) ---
    subgraph Model_Layer ["📦 DOMAIN MODEL (Polymorphic)"]
        Repo["Repository"]
        
        subgraph Entities ["Unified Stream"]
            Project["Project Container"]
            Items["List[ Union ]"]
            
            Task["⚡ TaskItem"]
            Res["🛒 ResourceItem"]
            Ref["📚 ReferenceItem"]
        end
    end

    %% --- LAYER 5: PERSISTENCE ---
    subgraph Disk ["💾 DISK"]
        YAML["dataset.yaml"]
    end

    %% --- FLOWS ---
    
    %% 1. Manual Path
    User -- "1a. Types Manually" --> ManualForm
    ManualForm -- "Direct Call" --> PlanService
    
    %% 2. AI Path
    User -- "1b. Clicks Triage" --> AIButton
    AIButton -- "Request" --> TriageService
    TriageService --> AI_Engine
    AI_Engine -- "JSON" --> ProposalEngine
    ProposalEngine -- "Draft Object" --> Proposal
    Proposal -.-> InboxView
    InboxView -- "User Confirms" --> TriageService
    
    %% 3. Unification
    TriageService --> Repo
    PlanService --> Repo
    
    %% 4. Data Structure
    Repo --> Project
    Project --> Items
    Items --- Task
    Items --- Res
    Items --- Ref
    
    %% 5. State Updates
    Repo -- "Mark Dirty" --> DirtyFlag
    Repo -- "Update Data" --> SessionState
    SessionState -- "Triggers Rerun" --> View_Layer
    
    %% 6. Persistence
    User -- "Click Save" --> View_Layer
    View_Layer -- "Command" --> Repo
    Repo -- "Write" --> YAML

    %% --- CLASS ASSIGNMENTS ---
    class InboxView,PlanView,ManualForm,AIButton view
    class TriageService,PlanService,AI_Engine,ProposalEngine service
    class Repo,Project,Items,Task,Res,Ref model
    class SessionState,DirtyFlag,Proposal state
    class YAML storage
```