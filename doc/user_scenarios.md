File: `./doc/user_scenarios.md`
```markdown
# User Scenario: Mixed Inbox Triage

## Scenario: Clearing a Weekend Brain Dump

### User Context:
David has spent the weekend thinking about his "Kitchen Renovation" project and his "Personal Website" project. He has dumped 5 random thoughts into his Inbox via his phone.

### The Inbox Content:
1. "Call plumber about sink"
2. "Need 2x4 lumber"
3. "https://inspiration.com/modern-kitchens"
4. "Update CSS for homepage"
5. "Buy milk"

### The Triage Process (F-01):

1.  **Item 1: "Call plumber about sink"**
    *   **AI Analysis:** Detects action verb "Call". Matches context to existing project "Kitchen Renovation".
    *   **Suggestion:** Type: **Task** | Project: **Kitchen Renovation**.
    *   **User Action:** Clicks [Confirm]. Item moves to Task list.

2.  **Item 2: "Need 2x4 lumber"**
    *   **AI Analysis:** Detects material/purchase intent. Matches context to "Kitchen Renovation".
    *   **Suggestion:** Type: **Shopping Item** | Project: **Kitchen Renovation**.
    *   **User Action:** Clicks [Confirm]. Item moves to Shopping list.

3.  **Item 3: "https://inspiration.com/..."**
    *   **AI Analysis:** Detects URL. Matches context to "Kitchen Renovation".
    *   **Suggestion:** Type: **Reference** | Project: **Kitchen Renovation**.
    *   **User Action:** Clicks [Confirm]. Item moves to Reference list.

4.  **Item 4: "Update CSS for homepage"**
    *   **AI Analysis:** Matches context to "Personal Website".
    *   **Suggestion:** Type: **Task** | Project: **Personal Website**.
    *   **User Action:** Clicks [Confirm].

5.  **Item 5: "Buy milk"**
    *   **AI Analysis:** Detects shopping. No relevant project found.
    *   **Suggestion:** Type: **Task** | Project: **Groceries** (New Project?).
    *   **User Action:** David realizes this is just a quick errand. He clicks [Edit] and assigns it to a generic "Errands" project manually.

### Result:
Inbox is empty. The "Kitchen Renovation" project now has 1 new task, 1 new shopping item, and 1 new reference link, all sorted correctly without David navigating into the project folders.