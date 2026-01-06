# Architecture & Strategy

## The "Context Injection" Strategy (DRY & OCP)

To ensure the AI behaves correctly in different modes without duplicating logic, we implement a **Service-Led Context Strategy**.

### 1. The Problem
*   **Triage Mode:** Needs to route items anywhere. Needs a **Global Vocabulary** (All tags from all domains).
*   **Enrichment Mode:** Needs to clean up a specific project. Needs a **Local Vocabulary** (Only tags relevant to that domain).

### 2. The Solution (SOLID Principles)
*   **Single Responsibility (SRP):** `PromptBuilder` is "dumb". It does not decide which tags to show. It simply formats the list of tags passed to it.
*   **Open/Closed (OCP):** We can add new Domains or Tagging Strategies in the *Service Layer* without modifying the Prompt Builder or the AI Client.

### 3. Implementation Details

#### A. Triage Context (Global)
*   **Service:** `TriageService.get_triage_tags()`
*   **Logic:** Returns `Union(All Domain Defaults, All Tags in DB)`.
*   **Result:** AI can route a "Buy Milk" task (Lifestyle) and a "Fix Bug" task (Software) in the same session.

#### B. Enrichment Context (Local)
*   **Service:** `PlanningService.enrich_project(id)`
*   **Logic:**
    1.  Look up `Project.domain` (e.g., SOFTWARE).
    2.  Fetch `DOMAIN_CONFIGS[SOFTWARE]`.
    3.  Add tags currently used *only* in this project.
*   **Result:** When enriching a Software project, the AI will never suggest "Grocery" tags.

## Auto-Creation Strategy
To support the AI's tendency to categorize items into standard GTD buckets ("General", "Someday/Maybe"), the `TriageService` implements a **Lazy Initialization** pattern.
*   If the AI suggests a project named "General" and it does not exist, the Service creates it on the fly before assigning the item.