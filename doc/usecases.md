This is a crucial step. By applying Alistair Cockburn's rigorous standards, we move from "developer notes" to a "contract of behavior." This ensures that the **Polymorphism**, **Proposal Engine**, and **Explicit Persistence** are not just implementation details, but observable behaviors that serve the user's goals.

Here are the refined Use Case Specifications.

---

# Use Case Catalog

| ID | Name | Level | Primary Actor |
| :--- | :--- | :--- | :--- |
| **UC-01** | **Clarify Inbox Item** | 🌊 User Goal | User |
| **UC-02** | **Plan Project Work** | 🌊 User Goal | User |
| **UC-03** | **Execute Next Actions** | 🌊 User Goal | User |
| **UC-04** | **Switch Context (Dataset)** | 🌊 User Goal | User |
| **UC-05** | **Persist Data** | 🐟 Subfunction | User |

---


---

## UC-02: Plan Project Work

**Primary Actor:** User
**Scope:** Task Classifier RD (Planning Mode)
**Level:** User Goal (Sea Level)

**Stakeholders and Interests:**
*   **User:** Wants to structure a project with mixed item types (Tasks, Shopping, Notes) manually.

**Preconditions:**
1.  The System has loaded a valid Dataset.

**Success Guarantee:**
*   New items are added to the Project's unified stream.
*   The System marks the session state as "Dirty."

**Trigger:** User navigates to the "Planning" view.

**MAIN SUCCESS SCENARIO:**
1.  The User selects a specific Project.
2.  The System displays the Project's unified stream of items.
3.  The User initiates "Add Item."
4.  The User specifies the **Item Type** (Task, Resource, or Reference) and enters the content.
5.  The System validates the input.
6.  The System adds the new polymorphic item to the Project.
7.  The System updates the view to show the new item in the stream.

**EXTENSIONS:**
*   **1a. Project does not exist:**
    1.  The User creates a new Goal (optional) and a new Project.
    2.  The System initializes an empty unified stream for the Project.
    3.  Resume at Step 3.

*   **4a. User adds a Resource (Shopping Item):**
    1.  The User enters the Item Name and optionally the Store/Location.
    2.  Resume at Step 5.

*   **4b. User adds a Reference:**
    1.  The User enters the Title and the URL/Content.
    2.  Resume at Step 5.

---

## UC-03: Execute Next Actions

**Primary Actor:** User
**Scope:** Task Classifier RD (Execution Mode)
**Level:** User Goal (Sea Level)

**Stakeholders and Interests:**
*   **User:** Wants to see only actionable tasks relevant to the current context.

**Preconditions:**
1.  Projects contain active Task items.

**Success Guarantee:**
*   Completed items are marked as done in the domain model.
*   The System marks the session state as "Dirty."

**Trigger:** User navigates to the "Execution" view.

**MAIN SUCCESS SCENARIO:**
1.  The User selects a Context Filter (e.g., "@home").
2.  The System displays a flat list of **Task Items** matching the filter (hiding Resources and References).
3.  The User marks a Task as complete.
4.  The System updates the Task's status to "Completed."
5.  The System removes the Task from the active view (or visually strikes it out).

**EXTENSIONS:**
*   **1a. No Context selected:**
    1.  The System displays all active Task Items from all active Projects.

*   **3a. User marks a task by mistake:**
    1.  The User unchecks the completed item.
    2.  The System reverts the status to "Active."

---

## UC-04: Switch Context (Dataset)

**Primary Actor:** User
**Scope:** Task Classifier RD (System)
**Level:** User Goal (Sea Level)

**Stakeholders and Interests:**
*   **User:** Wants to switch between "Work" and "Personal" modes completely.
*   **Developer:** Wants to load a "Test Fixture" to verify system behavior.

**Preconditions:**
1.  Multiple YAML dataset files exist in the `./data` directory.

**Success Guarantee:**
*   The application state is replaced entirely with the data from the selected file.

**Trigger:** User selects a file from the "Dataset" dropdown in the sidebar.

**MAIN SUCCESS SCENARIO:**
1.  The User selects a target dataset (e.g., `work.yaml`).
2.  The System verifies that the current session is **Clean** (not Dirty).
3.  The System loads the target YAML file from disk.
4.  The System replaces the in-memory Domain Model with the new content.
5.  The System refreshes the UI to reflect the new context.

**EXTENSIONS:**
*   **2a. Current session is Dirty (Unsaved Changes):**
    1.  The System blocks the load operation.
    2.  The System displays a warning: "Unsaved changes. Please save or revert."
    3.  The User saves the current data (See **UC-05**).
    4.  The User re-selects the target dataset.
    5.  Resume at Step 3.

---

## UC-05: Persist Data

**Primary Actor:** User
**Scope:** Task Classifier RD (System)
**Level:** Subfunction (Fish Level)

**Stakeholders and Interests:**
*   **User:** Wants to ensure work is not lost if the browser is closed.

**Preconditions:**
1.  The Session State is marked as "Dirty" (Unsaved Changes).

**Success Guarantee:**
*   The in-memory Domain Model is serialized to YAML.
*   The file on disk is updated.
*   The "Dirty" flag is cleared.

**Trigger:** User clicks the "Save" button.

**MAIN SUCCESS SCENARIO:**
1.  The User clicks "Save Changes."
2.  The System serializes the polymorphic Domain Model into JSON-compatible format.
3.  The System writes the data to the active YAML file.
4.  The System clears the "Dirty" flag.
5.  The System provides visual feedback (e.g., "Saved").

**EXTENSIONS:**
*   **3a. File Write Error (Permission/Disk Full):**
    1.  The System displays an error message.
    2.  The System retains the "Dirty" flag.
    3.  The System retains the in-memory data (no data loss).