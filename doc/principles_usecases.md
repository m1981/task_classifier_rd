Here is a comprehensive guide to writing textual use cases, based on the methodology of Alistair Cockburn (author of the definitive book *Writing Effective Use Cases*).

As an experienced Requirements Engineer, I have structured this from the high-level structure down to the sentence-level grammar.

---

### 1. The Structure Rules (The Skeleton)

Before writing a single step, you must establish the context. A use case is not just a list of steps; it is a contract of behavior.

**Rule:** Every Use Case must have a defined Goal Level.
*   **Do:** Use Cockburn’s icons/levels:
    *   ☁️ **Cloud (Summary):** High-level business goals (e.g., "Manage Inventory").
    *   🪁 **Kite (High-level):** A business process (e.g., "Process an Order").
    *   🌊 **Sea-level (User Goal):** The most common level. What one person wants to get done in one sitting (e.g., "Register a Customer").
    *   🐟 **Fish (Sub-function):** Detailed steps used by other use cases (e.g., "Validate Credit Card").
*   **Don't:** Mix levels. Don't put "Click the OK button" (Fish/Clam level) inside a "Manage Inventory" (Cloud level) use case.

**Rule:** Define the Scope and the Primary Actor clearly.
*   **Do:** Identify the "System Under Discussion" (SuD). Is it the whole company? The website? The database API?
*   **Do:** Identify the Primary Actor (the one with the goal).
*   **Don't:** Write a use case where the system does everything and the user does nothing.

---

### 2. The Main Success Scenario (The Happy Path)

This is the heart of the use case. It describes what happens when everything goes perfectly.

**Rule:** Number the steps sequentially.
*   **Do:** Use a simple 1, 2, 3 list.
*   **Don't:** Use complex flowcharts or pseudo-code logic (if/else) inside the main scenario.

**Rule:** Use the "Subject + Verb + Direct Object" sentence structure.
*   **Do:** "Customer enters address." / "System validates the zip code."
*   **Don't:** "Address entry." (Passive) or "The user will then proceed to type in their address details." (Wordy).

**Rule:** Show the "Tennis Match" dialogue.
*   **Do:** Alternate between Actor and System.
    1. User does X.
    2. System does Y.
    3. User does Z.
*   **Don't:** Group five system actions into one step unless they happen instantaneously and atomically.

**Rule:** Write from a "Bird’s Eye View."
*   **Do:** Describe *intent*, not GUI specifics. "User selects a payment method."
*   **Don't:** Describe specific UI mechanics. "User clicks the blue radio button in the top right corner." (The UI will change; the intent won't).

---

### 3. The Extensions (The "What Ifs")

This is where Cockburn’s method shines. Instead of cluttering the main path with "If/Else," we move all deviations to the Extensions section.

**Rule:** Use the Main Scenario step numbers as reference points.
*   **Do:** Label extensions like "3a. Invalid Password entered." (This means something went wrong at step 3).
*   **Don't:** Write generic error handling like "Global: If database fails." (Unless it truly applies everywhere).

**Rule:** Describe the Condition, then the Handling.
*   **Do:**
    *   *3a. Customer is under 18:*
        *   *3a1. System displays age restriction warning.*
        *   *3a2. Use case ends.*
*   **Don't:** Just list the error without saying how the system fixes it or ends the interaction.

**Rule:** Handle the "Rejoin" or "End."
*   **Do:** Explicitly state if the flow returns to the main path ("Resume at step 4") or if the use case fails ("Use case ends failure").
*   **Don't:** Leave the reader hanging, wondering if the process continues after the error.

---

### 4. Grammar and Style (The Fine Print)

Cockburn emphasizes readability. Use cases are for humans, not compilers.

**Rule:** No "GUI-speak."
*   **Do:** "User submits the request."
*   **Don't:** "User clicks the 'Submit' button." (Why? Because tomorrow the button might be a voice command or a swipe gesture).

**Rule:** No "Data-speak."
*   **Do:** "System records the transaction."
*   **Don't:** "System writes the transaction ID to table TBL_TRANS with a foreign key to TBL_USER." (Save that for the technical design document).

**Rule:** Avoid the "check" verb.
*   **Do:** "System validates the password." (Implies the check and the outcome).
*   **Don't:** "System checks the password." (This is weak. What happens if it fails? The extension handles the failure; the main step assumes success).

---

### Summary Checklist: Do's and Don'ts

| Feature | DO ✅ | DON'T ❌ |
| :--- | :--- | :--- |
| **Perspective** | Write from outside the system (Black Box). | Write about internal code logic or database fields (White Box). |
| **Tone** | Active voice ("System sends email"). | Passive voice ("Email is sent by system"). |
| **Detail** | "User identifies herself." | "User enters ID and Password in the login box." |
| **Flow** | Put failures in the "Extensions" section. | Put "If/Else" logic in the Main Success Scenario. |
| **Completeness** | Specify Preconditions (what must be true before starting). | Assume the system is always ready to go. |
| **Ending** | Define Success Guarantees (what is true when done). | Just stop writing after the last step. |

### Example of a Cockburn-Style Use Case (Snippet)

**Use Case:** Withdraw Cash (Sea Level 🌊)
**Primary Actor:** Account Holder
**Precondition:** User is logged in.

**Main Success Scenario:**
1. User selects "Withdraw Cash."
2. System asks for amount.
3. User enters amount.
4. System validates amount is within limits and balance.
5. System dispenses cash.
6. System deducts amount from balance.

**Extensions:**
*4a. Insufficient funds:*
    *   4a1. System displays "Insufficient Funds" message.
    *   4a2. System asks for new amount.
    *   4a3. Resume at step 3.
*4b. ATM out of cash:*
    *   4b1. System displays apology.
    *   4b2. Use case ends.