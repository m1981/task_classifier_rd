#### ADRs - Architecture Decision Records
*This is crucial for YAGNI. Record why you said "No" to things.*

```markdown
# Architecture Decisions

## ADR-001: Use Local YAML instead of SQLite
*   **Status:** Accepted
*   **Context:** We need simple portability and git-friendliness for user data.
*   **Decision:** Use YAML.
*   **Consequence:** Performance might suffer if datasets get huge (>10k tasks), but YAGNI for now.

## ADR-002: Single-Task Triage vs Batch Processing
*   **Status:** Accepted
*   **Context:** Batch processing (sending 50 tasks at once) confused the AI and the User.
*   **Decision:** Switch to "Tinder-style" one-card-at-a-time interface.
*   **Consequence:** Slower total time, but higher accuracy and lower cognitive load.