# Data Model

## 1. Domain Entities (Persistence Layer)

### Goal
*   `id`: UUID
*   `name`: String (e.g., "Healthy Lifestyle")
*   `status`: Enum [Active, Someday]

### Project
*   `id`: Integer
*   `goal_id`: UUID (Foreign Key, Optional)
*   `name`: String
*   `status`: Enum [Active, OnHold, Completed]

### Task (Actionable)
*   `id`: Integer
*   `project_id`: Integer
*   `name`: String
*   `tags`: List[String] (Contexts)
*   `is_completed`: Boolean

### ShoppingItem (Material)
*   `id`: UUID
*   `project_id`: Integer
*   `name`: String
*   `is_purchased`: Boolean

### ReferenceItem (Information)
*   `id`: UUID
*   `project_id`: Integer
*   `name`: String
*   `content`: Text (URL or Note)

## 2. AI Data Transfer Objects (DTOs)

These models define the contract between the App and the LLM.

### ClassificationType (Enum)
*   `NEW_PROJECT`: The input implies a complex outcome requiring a new project.
*   `TASK`: An actionable step for an existing project.
*   `SHOPPING`: An item to purchase for an existing project.
*   `REFERENCE`: Information to store for an existing project.
*   `TRASH`: Non-actionable nonsense.

### ClassificationResult (Pydantic Model)
*   `classification_type`: ClassificationType
*   `suggested_project_name`: String (Existing project name OR New project name)
*   `confidence`: Float (0.0 - 1.0)
*   `reasoning`: String (Why the AI chose this)
*   `refined_text`: String (Cleaned up version of the user input, e.g., removing "I need to buy...")