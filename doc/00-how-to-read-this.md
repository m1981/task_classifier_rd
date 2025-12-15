The approach I described is not taken from a single "Holy Bible" of software engineering. Instead, it is a **hybrid best-practice** derived from three specific, well-established methodologies.

If you want to cite sources or study the theory behind this structure, here are the three methodologies it comes from:
## 1. Intro
### 1. BDD (Behavior-Driven Development)
**Where it appears in my advice:** *The "Feature" files containing "User Stories/Scenarios".*

*   **The Principle:** BDD dictates that software should be specified in terms of its **behavior** (what it does) rather than its implementation (how it works).
*   **The Artifact:** In BDD (specifically using the **Gherkin** syntax), you organize files exactly as I suggested:
    *   `Feature: Goal Planning`
    *   `Scenario: User adds a shopping item`
*   **Key Reference:** *Specification by Example* by Gojko Adzic.

### 2. The "C4 Model" for Software Architecture
**Where it appears in my advice:** *The separation of Context, Containers (Features), and Components (Flows/Data).*

*   **The Principle:** You cannot document a system at just one level of zoom. You need different levels for different audiences.
    *   **Level 1 (Context):** My `00-context.md` (System Context).
    *   **Level 2 (Containers):** My `01-feature-catalog.md` (High-level functional blocks).
    *   **Level 3 (Components):** My detailed Feature Briefs and Data Models.
*   **Key Reference:** *The C4 Model* by Simon Brown.

### 3. "Docs as Code" (Documentation as Code)
**Where it appears in my advice:** *Using Markdown files in the git repo (`/specs`) rather than Word/Confluence.*

*   **The Principle:** Documentation should live as close to the code as possible, use the same tools (Git, VS Code), and evolve at the same pace. If specs are in a separate Wiki, they rot. If they are in the repo, they stay alive.
*   **Key Reference:** *Docs Like Code* by Anne Gentle.

---

### The "Un-Methodology": Agile/Lean
The overarching philosophy here is **Lean Requirements**.

In traditional **Waterfall** (e.g., IEEE 830 standard), you would write a massive "SRS" (Software Requirements Specification) document. It would be 200 pages long, contain every feature, and be obsolete the day it was signed.

The structure I gave you is the **Agile** antidote to the SRS:
1.  **Just Enough:** Only document what you are about to build (YAGNI).
2.  **Living Documents:** Files that change as the code changes.
3.  **Feature-Centric:** Organizing by "Value delivered" (Features) rather than "System modules" (Database, UI, API).

### Summary Table

| Concept I Suggested | Methodology Origin |
| :--- | :--- |
| **Feature Files** | **BDD** (Behavior-Driven Development) |
| **Context -> Feature -> Flow** | **C4 Model** (Architecture) |
| **Markdown in Git** | **Docs as Code** |
| **YAGNI / KISS** | **XP** (Extreme Programming) / **Lean** |


## 2. Examples
### 1. What is a "Feature" vs. a "Use Case"?

To structure this correctly, we need to distinguish between three levels of abstraction:

1.  **The Goal (Why):** "I need to clear my mind." (User Need)
2.  **The Feature (What):** A distinct slice of functionality that delivers value. It is a container for capabilities. (e.g., "Inbox Triage", "Goal Dashboard").
3.  **The Use Case / User Story (How):** The specific interaction steps. (e.g., "User clicks 'Skip' button").

**The Methodology:**
Features are the **Table of Contents** of your product. They bridge the gap between high-level vision and low-level code.

---

### 2. Where do Features Live?

Features should live in a **Feature Catalog** (or Feature Map). This is usually the "Parent" document that links to specific flows and data models.

In your file structure, I recommend renaming/restructuring slightly to make "Features" the primary organization method.

#### Recommended Structure:

```text
/specs
  ├── 00-product-vision.md    # The "Why"
  ├── 01-feature-catalog.md   # <--- THE HOME OF FEATURES
  ├── features/               # Detailed specs per feature
  │   ├── f01-inbox-triage.md
  │   ├── f02-goal-planning.md
  │   └── f03-execution-mode.md
  └── data-model.md           # Shared entities
```

---

### 3. How to Describe a Feature (The Methodology)

Don't just write a paragraph of text. Use a structured **Feature Brief** format. This is the industry standard for capturing features effectively.

**The Feature Brief Template:**
1.  **ID & Name:** Unique identifier (e.g., F-01).
2.  **Value Proposition:** Why are we building this?
3.  **Scope (In/Out):** What does this feature include, and crucially, what does it *not* include?
4.  **User Stories/Use Cases:** The list of interactions.
5.  **Dependencies:** What other features does this rely on?

#### Example: Describing your "Planning" Feature

**File:** `specs/features/f02-goal-planning.md`

```markdown
# Feature F-02: Goal-Oriented Planning

## 1. Value Proposition
Users need to see the "Big Picture" to ensure their daily tasks align with their long-term ambitions. This feature allows users to structure projects under Goals and manage support materials (shopping lists, references).

## 2. Scope
*   **In Scope:** 
    *   Creating/Editing Goals.
    *   Linking Projects to Goals.
    *   Managing "Shopping Lists" and "Reference Items" within a project.
*   **Out of Scope:** 
    *   Executing tasks (checking them off happens in Execution Mode).
    *   AI auto-generation of goals (Future V2).

## 3. Key Components (The "Views")
*   **Goal Dashboard:** A high-level card view of all active goals.
*   **Project Detail View:** A tabbed view showing Tasks, Shopping List, and References side-by-side.

## 4. User Stories (The Requirements)
*   **US-01:** As a user, I want to create a Goal so that I can group related projects.
*   **US-02:** As a user, I want to add a "Shopping List" item to a project so I don't mix it with actionable tasks.
*   **US-03:** As a user, I want to see a progress bar for a Goal based on completed projects.

## 5. Dependencies
*   Requires **F-01 (Data Model)** to support the `Goal` entity.
```

---

### 4. Why separate "Features" from "Flows"?

You might ask: *"Why not just put everything in one file?"*

**The Reason:** Features are **Marketing/Product** concepts. Flows are **UX/Engineering** concepts.

*   **When you talk to a stakeholder:** You show them the **Feature Catalog**. ("We are building the Goal Planning feature next.")
*   **When you talk to a developer (or yourself coding):** You look at the **Use Cases** and **Flows**.

### 5. Summary: The "Feature-First" Hierarchy

If you adopt this methodology, your mental model looks like this:

1.  **Product:** "GTD App"
2.  **Feature (F-02):** "Goal Planning" (Lives in `specs/features/f02...`)
    *   *Contains:* **View:** "Project Detail Screen"
    *   *Contains:* **Logic:** "Link Project to Goal"
    *   *Contains:* **Data:** "Shopping List Entity"

**Action Plan for you:**
1.  Create a `features/` folder in your specs.
2.  Create one markdown file for each major "box" in your diagram (e.g., `inbox-triage.md`, `goal-planning.md`, `next-actions.md`).
3.  Move your Use Cases into these specific Feature files.