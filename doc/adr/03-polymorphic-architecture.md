# ADR 003: Polymorphic Unified Stream

## Context
In a GTD system, a Project contains various types of items: actionable tasks, things to buy, and reference notes.
*   **Option A (Bag of Lists):** `Project.tasks`, `Project.shopping`, `Project.refs`.
*   **Option B (Unified Stream):** `Project.items` containing a mix of types.

## Decision
We choose **Option B: The Unified Stream**.

We will use Pydantic's `Union` type with a `kind` discriminator field.
```python
items: List[Union[TaskItem, ResourceItem, ReferenceItem]]