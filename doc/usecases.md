# Use Cases - Current Implementation

## UC-001: Load Personal Task Dataset
**Primary Actor**: User  
**Goal**: Access my saved task organization data to continue work  
**Preconditions**: I have previously saved at least one dataset  
**Success Guarantee**: My projects and inbox tasks are displayed and ready for work  

### Main Success Scenario:
1. I open the task classification app
2. I see a dropdown showing my available datasets
3. I select "Home Renovation March 2024" from the dropdown
4. The app loads my 3 projects (Kitchen, Bathroom, Garage) in the left panel
5. The app loads my 15 inbox tasks in the left panel
6. I can now see all my data and continue organizing tasks

### Extensions:
3a. I have no saved datasets:
   - App shows "No datasets found" message
   - I need to create datasets elsewhere first

4a. My dataset file is corrupted:
   - App shows clear error message
   - I can try loading a different dataset

---

## UC-002: Organize Inbox Tasks Into Projects
**Primary Actor**: User  
**Goal**: Automatically sort my messy inbox tasks into my existing projects  
**Preconditions**: I have loaded a dataset with projects and inbox tasks  
**Success Guarantee**: Each inbox task gets assigned to the most appropriate project with confidence level  

### Main Success Scenario:
1. I see my 15 inbox tasks like "Fix bathroom sink", "Install cabinet handles", "Buy paint"
2. I select "DIY Renovation" strategy (since I'm doing home improvement)
3. I click "🚀 Classify Tasks" button
4. App shows "🤖 AI is thinking..." while processing
5. App displays results table showing:
   - "Fix bathroom sink" → Bathroom Project (95% confidence) ✅
   - "Install cabinet handles" → Kitchen Project (87% confidence) ✅
   - "Buy paint" → Unmatched (45% confidence) ❓
6. I can see 12 tasks were classified successfully, 3 need review

### Extensions:
3a. I have no inbox tasks to classify:
   - App shows "No inbox tasks to classify" error
   - I need to add tasks to my inbox first

5a. AI service is unavailable:
   - App shows "Classification failed: API error" message
   - I can try again later

---

## UC-003: Review Questionable Task Classifications
**Primary Actor**: User  
**Goal**: Understand why some tasks weren't classified well and decide what to do  
**Preconditions**: I have completed task classification with some low-confidence results  
**Success Guarantee**: I can see detailed reasoning for problematic classifications  

### Main Success Scenario:
1. After classification, I see "🔍 Review Needed (3 tasks)" section
2. I click to expand the review section
3. For "Buy paint" task, I see:
   - Suggested: Unmatched (45% confidence)
   - Alternatives: Kitchen Project, Bathroom Project
   - Reasoning: "Task is too generic - unclear which room needs painting"
4. For "Fix electrical outlet", I see:
   - Suggested: Kitchen Project (65% confidence) ⚠️
   - Alternatives: Bathroom Project, Garage Project
   - Reasoning: "Could apply to multiple rooms, needs more specificity"
5. I now understand what to improve in my task descriptions

### Extensions:
1a. All tasks were classified with high confidence:
   - Review section doesn't appear
   - I can proceed with confidence in all results

---

## UC-004: Edit My Task Data in Real-Time
**Primary Actor**: User  
**Goal**: Quickly modify my projects or inbox tasks without file editing  
**Preconditions**: I have loaded a dataset  
**Success Guarantee**: My changes appear immediately in the interface  

### Main Success Scenario:
1. I see my projects list shows "Kitchen;Kitchen Renovation"
2. I change it to "Kitchen;Kitchen Complete Remodel" in the text area
3. The change appears immediately without clicking save
4. I add a new inbox task "Install new dishwasher" to the inbox text area
5. The new task appears immediately in my inbox list
6. I can now classify tasks with my updated data

### Extensions:
2a. I enter invalid format like missing semicolon:
   - App continues to accept my input
   - Validation will happen when I try to save

---

## UC-005: Save My Work Progress
**Primary Actor**: User  
**Goal**: Permanently save my current task organization progress  
**Preconditions**: I have made changes to my dataset  
**Success Guarantee**: My work is saved and I can reload it later  

### Main Success Scenario:
1. I enter "Home Renovation April 2024" in the "Save As" field
2. I click "💾 Save Dataset" button
3. App validates my dataset name is acceptable
4. App saves my current projects and inbox tasks to file system
5. App shows green "✅ Dataset saved successfully" message
6. The dataset dropdown now includes my new "Home Renovation April 2024" option

### Extensions:
3a. I enter invalid name (empty or too long):
   - App shows red error message
   - I can correct the name and try again

4a. File system has permission issues:
   - App shows "Save failed: Permission denied" error
   - I need to check file permissions

---

## UC-006: Preview AI Strategy Before Using
**Primary Actor**: User  
**Goal**: Understand what instructions the AI will receive before I run classification  
**Preconditions**: I have loaded a dataset  
**Success Guarantee**: I can see the exact prompt that will be sent to AI  

### Main Success Scenario:
1. I select "DIY Renovation" from the strategy dropdown
2. I see the "👁️ Current Prompt Preview" section expand automatically
3. I can read the full prompt showing:
   - "Act as an experienced DIY home renovation expert..."
   - My complete projects list
   - My complete inbox tasks list
   - The expected response format
4. I see "Strategy: diy_renovation | Characters: 1,247"
5. I'm confident this prompt will work well for my home renovation tasks

### Extensions:
None identified - this is purely informational.

---

## UC-007: Understand Classification Quality
**Primary Actor**: User  
**Goal**: Quickly assess how well the AI performed on my tasks  
**Preconditions**: I have completed task classification  
**Success Guarantee**: I can see overall quality metrics and individual task status  

### Main Success Scenario:
1. After classification, I see 4 metric boxes at the top:
   - "✅ High Confidence: 12" (80%+ confidence)
   - "⚠️ Medium Confidence: 2" (60-80% confidence)  
   - "❓ Low Confidence: 1" (<60% confidence)
   - "🔍 Unmatched: 0" (no good project match)
2. In the results table, each task shows a status icon:
   - "Fix bathroom sink" shows ✅ Good
   - "Install cabinet handles" shows ✅ Good
   - "Buy paint supplies" shows ⚠️ Review
3. I can quickly see that 12/15 tasks (80%) were classified with high confidence

### Extensions:
None identified - this provides comprehensive quality overview.

---

## UC-008: Apply Classification Results
**Primary Actor**: User  
**Goal**: Move classified tasks from inbox into their suggested projects  
**Preconditions**: I have completed task classification (UC-002) with acceptable results  
**Success Guarantee**: Tasks are moved to projects and inbox is cleared of processed items  

### Main Success Scenario:
1. I review my classification results showing 12 high-confidence tasks
2. I click "✅ Accept & Apply Results" button
3. App shows confirmation dialog: "Move 12 tasks to their suggested projects?"
4. I click "Confirm"
5. App moves each high-confidence task (≥80%) to its suggested project:
   - "Fix bathroom sink" → Added to Bathroom Project task list
   - "Install cabinet handles" → Added to Kitchen Project task list
6. App removes moved tasks from inbox
7. App shows "✅ Applied 12 classifications. 3 tasks remain in inbox for review"
8. My projects now contain the new tasks, inbox only has unresolved items

### Extensions:
2a. I want to review before applying:
   - I can see preview of what will be moved where
   - I can exclude specific tasks from the move

5a. Some projects don't exist in current dataset:
   - App shows error "Cannot move to non-existent project"
   - I need to create missing projects first

---

## UC-008A: Manually Override Task Assignment
**Primary Actor**: User  
**Goal**: Manually assign a task to a different project than AI suggested  
**Preconditions**: I have classification results and know where a task should really go  
**Success Guarantee**: Task is moved to my chosen project instead of AI suggestion  

### Main Success Scenario:
1. I see "Install cabinet handles" was classified to "Kitchen Project" (87% confidence)
2. I know this task actually belongs to "Garage Workshop" project
3. I click dropdown next to the task showing current suggestion
4. I select "Garage Workshop" from the dropdown of all my projects
5. App updates the assignment immediately
6. When I click "Apply Results", this task goes to Garage Workshop instead
7. App shows "✅ Applied 12 classifications (1 manually corrected)"

### Extensions:
4a. I want to create a new project for this task:
   - Dropdown includes "+ Create New Project" option
   - Leads to UC-011A workflow

---

## UC-009: Edit and Re-classify Tasks
**Primary Actor**: User  
**Goal**: Improve task descriptions that were poorly classified and try again  
**Preconditions**: I have low-confidence results I want to improve  
**Success Guarantee**: Improved tasks get better classification results  

### Main Success Scenario:
1. I see "Buy paint" was classified as "Unmatched" (45% confidence)
2. I click "✏️ Edit Problem Tasks" button
3. App shows editable list of low-confidence tasks:
   - "Buy paint" → [text input field]
   - "Fix electrical" → [text input field]
4. I change "Buy paint" to "Buy paint for kitchen cabinets"
5. I change "Fix electrical" to "Replace broken outlet in bathroom"
6. I click "🔄 Re-classify Edited Tasks"
7. App runs classification only on the 2 edited tasks
8. Results show:
   - "Buy paint for kitchen cabinets" → Kitchen Project (92% confidence) ✅
   - "Replace broken outlet in bathroom" → Bathroom Project (88% confidence) ✅
9. App merges these results with my previous classification

### Extensions:
7a. Edited tasks still get poor results:
   - App suggests trying different strategy
   - App shows examples of well-classified similar tasks

---

## UC-011: Create Project from Unmatched Tasks
**Primary Actor**: User  
**Goal**: Handle orphaned tasks by creating a new project to contain them  
**Preconditions**: I have multiple unmatched tasks that seem related  
**Success Guarantee**: New project is created and unmatched tasks are assigned to it  

### Main Success Scenario:
1. I see 4 tasks were classified as "Unmatched":
   - "Plan vacation itinerary"
   - "Book hotel reservations"
   - "Research flight prices"
   - "Get travel insurance"
2. I realize these all belong to a "Summer Vacation" project I haven't created
3. I click "📁 Create Project from Unmatched" button
4. App shows dialog: "Create new project for unmatched tasks?"
5. I enter project name: "Summer Vacation Planning"
6. App creates new project with ID and default settings
7. App automatically assigns all 4 unmatched tasks to this new project
8. App shows "✅ Created 'Summer Vacation Planning' project with 4 tasks"
9. My dataset now includes the new project with these tasks

### Extensions:
5a. Project name already exists:
   - App shows error and suggests different name
   - I can modify the name or merge with existing project

---

## UC-011A: Selectively Create Project from Chosen Tasks
**Primary Actor**: User  
**Goal**: Create a new project for only some of my unmatched tasks  
**Preconditions**: I have unmatched tasks but only some belong together  
**Success Guarantee**: New project contains only my selected tasks  

### Main Success Scenario:
1. I see 6 unmatched tasks including vacation and car maintenance items
2. I click "🎯 Select Tasks for New Project" button
3. App shows checkbox interface:
   - ☑️ "Plan vacation itinerary"
   - ☑️ "Book hotel reservations"  
   - ☑️ "Research flight prices"
   - ☐ "Change car oil"
   - ☐ "Rotate tires"
   - ☐ "Buy groceries"
4. I check the 3 vacation-related tasks
5. I enter project name: "Summer Vacation Planning"
6. I click "Create Project with Selected Tasks"
7. App creates new project with only the 3 selected tasks
8. App shows "✅ Created 'Summer Vacation Planning' with 3 tasks. 3 tasks remain unmatched"
9. Remaining unmatched tasks stay in inbox for future processing

### Extensions:
4a. I select only 1 task:
   - App warns "Consider if single task needs its own project"
   - I can proceed or cancel

6a. No tasks selected:
   - App shows "Please select at least one task"
   - I must select tasks or cancel
