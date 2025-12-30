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
*   **User:** Wants to rapidly process "Stuff" into the correct GTD buckets (Projects, Next Actions, Reference, Incubate, Trash) with AI assistance but final control.

**Preconditions:**
1.  The System has loaded a valid Dataset.
2.  The Inbox contains at least one raw text item.

**Success Guarantee:**
*   The raw item is removed from the Inbox.
*   **Outcome A (Actionable):** Item is converted to a Task/Resource and assigned to a Project (Existing or New).
*   **Outcome B (Non-Actionable):** Item is converted to a Reference Item or moved to the "Someday/Maybe" list (Incubate).
*   **Outcome C (Trash):** Item is permanently deleted (Manual only).

**MAIN SUCCESS SCENARIO (The AI-Assisted Path):**
1.  The System displays the oldest raw item from the Inbox.
2.  The System (AI) analyzes the item against the Goal/Project Hierarchy to determine **Actionability**.
3.  The System presents a **Draft Proposal** based on the analysis:
    *   *Variation A (Actionable - Existing Project):* Suggests Type (Task/Resource) and targets an Existing Project.
    *   *Variation B (Actionable - New Project):* Suggests Type "New Project" and proposes a Project Name.
    *   *Variation C (Non-Actionable - Reference):* Suggests Type "Reference" and targets a relevant Project or General storage.
    *   *Variation D (Non-Actionable - Incubate):* Suggests moving to "Someday/Maybe" list.
4.  The User reviews the reasoning and **Confirms** the proposal.
5.  **System Action:**
    *   Converts the Draft into the specific concrete Entity (TaskItem, ResourceItem, ReferenceItem).
    *   Appends the Entity to the target container (Project Stream or Someday List).
6.  The System removes the raw item from the Inbox.
7.  The System displays the next item.

**EXTENSIONS:**

*   **3a. Manual Override (User Disagrees with AI):**
    1.  The User disagrees with the AI's classification (e.g., AI suggests "Task", User knows it's "Reference").
    2.  The User manually selects the correct **Type** or **Target Project** via UI controls.
    3.  The System updates the Draft to reflect the manual selection.
    4.  The User clicks Confirm.
    5.  Resume at Step 5.

*   **3b. Trash (Manual Only):**
    *   *Context:* The AI never suggests "Trash" to prevent data loss.
    1.  The User determines the item is junk or no longer needed.
    2.  The User clicks the **"Delete/Trash"** button.
    3.  The System permanently deletes the raw item from the Inbox.
    4.  Resume at Step 7.

*   **3c. Skip Item:**
    1.  The User is undecided.
    2.  The User clicks **"Skip"**.
    3.  The System moves the item to the end of the Inbox queue.
    4.  Resume at Step 7.

*   **3d. AI cannot determine context ("Unmatched"):**
    1.  The System displays "Unmatched" and suggests a generic "New Project" or asks for input.
    2.  The User either:
        *   Selects an existing project manually.
        *   Types a custom name for a New Project.
    3.  Resume at Step 5.

*   **1a. Inbox is Empty:**
    1.  The System displays a "Inbox Zero" success message.
    2.  The Use Case ends.

*   **1b. Quick Capture (Interrupt):**
    1.  The User expands "Quick Capture".
    2.  The User types a new thought and clicks "Capture".
    3.  The System appends the item to the Inbox.
    4.  The System resumes the current Triage flow.
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
1.  The User views the Goal Dashboard.
2.  The System displays Goals with their associated Projects rendered as **Collapsible Strips**.
3.  The User expands a Project Strip.
4.  The System displays the **Unified Stream** of items (Tasks, Resources, References) chronologically.
5.  The User clicks "Add Item" (Quick Add).
6.  The User specifies the Type and Name.
7.  The System adds the new item to the stream.

**VARIATIONS:**
*   **2a. Reordering Projects:**
    1.  The User clicks the "Up" or "Down" arrow on a Project Strip.
    2.  The System swaps the `sort_order` of the project with its neighbor.
    3.  The System refreshes the view with the new order.

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