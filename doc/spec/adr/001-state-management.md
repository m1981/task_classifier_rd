# ADR 001: Explicit Persistence (Dirty State Pattern)

## Context
Streamlit is a stateless framework that reruns the entire script on every interaction. We are building a local-first application backed by a YAML file.
1. Writing to disk on every single click (e.g., moving a task) introduces latency.
2. Relying solely on `st.session_state` risks data loss if the user refreshes the browser before saving.

## Decision
We will implement a **Command Pattern with Explicit Save**.

1.  **In-Memory Mutation:** All actions (Add, Move, Delete) operate strictly on the Python objects stored in `st.session_state`.
2.  **Dirty Flag:** We will maintain a boolean flag `st.session_state.is_dirty`. Any mutation sets this to `True`.
3.  **UI Feedback:** If `is_dirty` is True, a "Save Changes" button becomes prominent (e.g., turns red or appears in the sidebar).
4.  **Explicit Save:** Writing to the YAML file only happens when the user clicks "Save".

## Consequences
*   **Pros:** Fast UI interactions (zero disk I/O latency during triage).
*   **Cons:** Risk of data loss if the browser tab is closed without saving.
*   **Mitigation:** We will add a visual warning "⚠️ Unsaved Changes" in the header whenever the state is dirty.