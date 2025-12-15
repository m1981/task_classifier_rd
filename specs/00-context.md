# System Context

## Product Vision
A "Triage-First" task manager that uses AI to rapidly sort a chaotic inbox into structured projects, stored in local YAML files for privacy and portability.

## Core Principles
1. **Local-First:** Data lives in `dataset.yaml`. No cloud database.
2. **Human-in-the-Loop:** AI suggests, User decides. AI never destructively edits without confirmation.
3. **Triage Mode:** One task at a time. Focus on clearing the inbox.

## System Actors
*   **User:** The person organizing tasks.
*   **Claude (AI):** The intelligence analyzing text.
*   **File System:** The storage mechanism.