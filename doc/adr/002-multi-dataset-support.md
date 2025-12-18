# ADR 002: Multi-Dataset Fixture Support

## Context
For development, testing, and distinct user contexts (e.g., "Work" vs "Home"), relying on a single hardcoded `dataset.yaml` is insufficient. We need a way to swap the entire application state instantly.

## Decision
We will implement a **File-Based Dataset Manager**.

1.  **Discovery:** On startup, the `DatasetManager` will scan the `./data/` directory for `*.yaml` files.
2.  **Selection:** The Streamlit Sidebar will populate a `selectbox` with these filenames.
3.  **Loading:** Selecting a file triggers `DatasetManager.load(filename)`, replacing `st.session_state.data` entirely.
4.  **Safety:** If `st.session_state.is_dirty` is True, the app must block the switch (or show a confirmation dialog) to prevent data loss.

## Consequences
*   **Testing:** We can commit files like `tests/fixtures/complex_renovation.yaml` or `tests/fixtures/spanish_tasks.yaml` to the repo.
*   **QA:** We can verify AI performance on specific edge cases by loading a static dataset.
*   **Complexity:** We must handle file I/O errors (e.g., corrupted YAML) gracefully.