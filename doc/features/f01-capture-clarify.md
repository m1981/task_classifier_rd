# Feature F-01: Capture & Clarify (Inbox Mode)

## Value Proposition
To empty the user's brain into a trusted system and rapidly process vague thoughts into concrete items using AI.

## User Stories
*   **US-1.1 Quick Capture:** As a user, I can add a raw text string to the Inbox from any screen.
*   **US-1.2 AI Triage:** As a user, I want the AI to analyze an inbox item and classify it into one of four buckets:
    *   **Task:** Move to an existing Project's task list.
    *   **Shopping:** Move to an existing Project's shopping list.
    *   **Reference:** Move to an existing Project's reference list.
    *   **New Project:** Create a new Project and move the item there as the first task.
*   **US-1.3 One-Touch Processing:** As a user, I want to accept the AI suggestion with a single click.
*   **US-1.4 Manual Override:** As a user, I want to be able to select a different project or category if the AI is wrong.

## UI Components
*   **Inbox Counter:** "5 items remaining"
*   **Triage Card:** The central card showing:
    *   Original Text
    *   AI Suggestion (e.g., "Type: Shopping", "Project: Kitchen Reno")
    *   Action Buttons: [Confirm] [Edit] [Skip] [Delete]