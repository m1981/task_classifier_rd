# Data Model

## Entities

### Task
*   `id`: Integer (Unique per project)
*   `name`: String
*   `tags`: List[String] (e.g., "physical", "urgent")
*   `duration`: String (optional)

### Project
*   `id`: Integer
*   `name`: String
*   `tasks`: List[Task]

## Schema (YAML)
```yaml
projects:
  kitchen_reno:
    id: 1
    name: "Kitchen"
    tasks: [...]
inbox_tasks:
  - "Buy milk"
  - "Fix door"