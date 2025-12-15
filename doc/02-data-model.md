# Data Model

## Entities

### 1. Goal (New)
*   `id`: UUID
*   `name`: String (e.g., "Healthy Lifestyle")
*   `status`: Enum [Active, Someday]

### 2. Project (Updated)
*   `id`: Integer
*   `goal_id`: UUID (Foreign Key)
*   `name`: String
*   `status`: Enum [Active, OnHold, Completed]

### 3. Task (Actionable)
*   `id`: Integer
*   `project_id`: Integer
*   `name`: String
*   `tags`: List[String] (Contexts)
*   `is_completed`: Boolean

### 4. ShoppingItem (New - from Diagram)
*   `id`: UUID
*   `project_id`: Integer
*   `name`: String
*   `link`: URL (Optional)
*   `is_purchased`: Boolean

### 5. ReferenceItem (New - from Diagram)
*   `id`: UUID
*   `project_id`: Integer
*   `name`: String
*   `description`: Text