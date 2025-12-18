# Feature F-00: System & Dataset Management

## Value Proposition
To allow developers and users to switch between different contexts (Personal, Work, Testing) and to provide a robust environment for validating AI behavior across different languages and domains without manual data entry.

## User Stories
*   **US-0.1 Dataset Selection:** As a user/developer, I want to see a list of available datasets (YAML files) in the sidebar so I can switch contexts immediately.
*   **US-0.2 Safe Switching:** As a user, if I try to switch datasets while I have unsaved changes, I want the system to warn me so I don't lose work.
*   **US-0.3 New Dataset:** As a user, I want to create a blank dataset from the UI so I can start a fresh domain.
*   **US-0.4 Multilingual Support:** As a developer, I want to load datasets in different languages (e.g., `german_recipes.yaml`) to verify the AI's classification logic works globally.

## Technical Scope
*   **Storage Location:** All datasets reside in a local `./data/` directory.
*   **File Format:** YAML (human-readable, git-friendly).
*   **Default:** On first launch, load `default.yaml` or create it if missing.