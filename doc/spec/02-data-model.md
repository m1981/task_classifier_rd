# Data Model: The Unified Stream

## Core Philosophy
We utilize a **Polymorphic Data Structure**. A Project does not contain separate lists for Tasks, Shopping, and References. Instead, it contains a single chronological stream of `ProjectItem` objects, distinguished by a `kind` discriminator.

## 1. The Abstract Base
### ProjectItem (Abstract)
*   `id`: UUID
*   `kind`: Enum ["task", "resource", "reference"] (The Discriminator)
*   `name`: String
*   `created_at`: DateTime

## 2. Concrete Entities (The "Bricks")

### TaskItem (extends ProjectItem)
*   `kind`: "task"
*   `is_completed`: Boolean
*   `tags`: List[String]
*   `duration`: String (Optional)

### ResourceItem (extends ProjectItem)
*   `kind`: "resource"
*   `is_acquired`: Boolean
*   `store`: String (Default: "General")
*   `cost_estimate`: Float (Optional)

### ReferenceItem (extends ProjectItem)
*   `kind`: "reference"
*   `url`: String (Optional)
*   `content`: Text

## 3. The Containers

### Project
*   `id`: Integer
*   `name`: String
*   `status`: Enum [Active, OnHold, Completed]
*   `goal_id`: UUID (Optional)
*   **`items`: List[Union[TaskItem, ResourceItem, ReferenceItem]]**  <-- The Unified Stream

### Goal
*   `id`: UUID
*   `name`: String
*   `description`: String
*   `status`: Enum [Active, Someday]

### DatasetContent (Root Aggregate)
*   `goals`: List[Goal]
*   `projects`: List[Project]
*   `inbox_tasks`: List[String] (Raw text, pre-classification)

## 4. AI & Ephemeral Models

### ClassificationType (Enum)
*   `TASK`, `SHOPPING`, `REFERENCE`, `NEW_PROJECT`, `TRASH`

### DraftItem (The "Proposal")
*   `source_text`: String
*   `suggested_kind`: ClassificationType
*   `suggested_project_id`: Integer (or None)
*   `reasoning`: String
*   `entity_payload`: Dict (The data ready to be cast into a Concrete Entity)