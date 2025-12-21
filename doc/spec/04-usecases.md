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

## UC-01: Clarify Inbox Item

**Primary Actor:** User
**Scope:** Task Classifier RD (Triage Mode)
**Level:** User Goal (Sea Level)

**Stakeholders and Interests:**
*   **User:** Wants to process raw thoughts into actionable tasks within specific projects.

**Preconditions:**
1.  The System has loaded a valid Dataset.
2.  The Inbox contains at least one raw text item.
3.  The AI Service is available.

**Success Guarantee:**
*   The raw item is removed from the Inbox.
*   The item is appended to the target Project's task list.
*   The System state is updated (and persisted via auto-save or dirty flag).

**Trigger:** User navigates to the "Inbox Triage" view.

**MAIN SUCCESS SCENARIO:**
1.  The System displays the oldest raw item from the Inbox (e.g., "Buy milk").
2.  The System (AI) analyzes the text and presents a **Triage Card** containing:
    *   **Reasoning:** Why the AI chose the project.
    *   **Suggested Project:** The best match (e.g., "Groceries").
    *   **Tags:** Extracted context tags (e.g., "errand").
3.  The User clicks the **"Add"** button (Primary Action).
4.  The System moves the item from the Inbox to the target Project's task list.
5.  The System refreshes the view to show the next item (Loop to Step 1).

**EXTENSIONS:**

*   **1a. Inbox is Empty:**
    1.  The System displays a "Inbox Zero" success message with balloons.
    2.  The Use Case ends.

*   **1b. Quick Capture (Interrupt):**
    1.  The User expands the "Quick Capture" section.
    2.  The User types a new thought and clicks "Capture".
    3.  The System adds the item to the end of the Inbox queue.
    4.  The System resumes the Triage flow (Step 1).

*   **2a. AI cannot find a matching project ("Unmatched"):**
    1.  The System displays "Unsure where to put this" and hides the "Add" button.
    2.  The System expands the "Create New Project" form (See Extension 4a) OR the User uses Manual Assignment (See Extension 3a).

*   **3a. Manual Assignment (Override):**
    1.  The User disagrees with the AI suggestion.
    2.  The User selects a different project from the **"Manual Assignment"** pills (chips).
    3.  The System immediately moves the item to the selected project.
    4.  Resume at Step 5.

*   **3b. User Skips the Item:**
    1.  The User clicks the **"Skip"** button.
    2.  The System moves the current item to the end of the Inbox queue.
    3.  The System clears the current AI prediction cache.
    4.  Resume at Step 5 (showing the next item).

*   **4a. Create New Project:**
    1.  The User (or AI) determines no existing project fits.
    2.  The User enters a name in the **"New Project Name"** field.
    3.  The User clicks "Create & Move".
    4.  The System creates the new Project.
    5.  The System moves the inbox item to this new Project.
    6.  Resume at Step 5.

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

**MAIN SUCCESS SCENARIO (Standard Filter):**
1.  The User selects a Context Filter (e.g., "@home").
2.  The System displays a flat list of **Task Items** matching the filter.
3.  The User marks a Task as complete.
4.  The System updates the Task's status to "Completed."
5.  The System removes the Task from the active view.

**VARIATIONS:**
*   **1a. Smart Context (AI Filter):**
    1.  The User types a natural language query (e.g., "I have 30 mins and low energy").
    2.  The System (AI) analyzes active tasks against the constraints.
    3.  The System returns a filtered list of the best-matching tasks.
    4.  The User proceeds to work on these tasks (Resume at Step 3).

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