# Features & Use Cases

## Feature A: Dataset Management
*Managing the physical files.*
*   **UC-01 Load Dataset:** User selects a folder; App validates and loads YAML into memory.
*   **UC-02 Save Dataset:** User clicks save; App writes memory state to disk safely.

## Feature B: AI Triage (The Core Loop)
*The single-task processing workflow.*
*   **UC-03 Classify Single Task:** App sends task + project list to AI; AI returns structured JSON.
*   **UC-04 Apply Suggestion:** User accepts AI match; Task moves to project; Tags applied.
*   **UC-05 Manual Override:** User selects a different project via "Pills".
*   **UC-06 Skip Task:** User defers decision; Task moves to end of queue.

## Feature C: Project Management
*   **UC-07 Create Project:** User types new name; App creates project and moves current task there immediately.