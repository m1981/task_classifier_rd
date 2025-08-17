# Research & Development: AI Task Classification Experiment

## Overview

Experimental  test AI capabilities for task categorization and attribute extraction using different prompt contexts. This is a research tool to optimize AI prompts for future production features.


## Core Components

### 1. Reference Tasks Input
- **Component**: `ReferenceTasksInput.svelte`
- **Purpose**: Define training examples for AI context
- **Format**: CSV-like text area
- **Schema**: `id;subject;tags;duration`

### 2. Current Projects Input  
- **Component**: `CurrentProjectsInput.svelte`
- **Purpose**: Available project categories for classification
- **Format**: CSV-like text area
- **Schema**: `pid;subject`

### 3. Inbox Tasks Input
- **Component**: `InboxTasksInput.svelte` 
- **Purpose**: Tasks to be classified by AI
- **Format**: Free text, one task per line

### 4. Results Display
- **Component**: `ClassificationResults.svelte`
- **Purpose**: Show AI classification results with confidence scores

## Data Models

```typescript
interface ReferenceTask {
  id: string;
  subject: string;
  tags: string[];
  duration?: string;
}

interface Project {
  pid: string;
  subject: string;
}

interface InboxTask {
  subject: string;
  originalIndex: number;
}

interface ClassificationResult {
  task: string;
  suggestedProject: string;
  confidence: number;
  extractedTags: string[];
  estimatedDuration?: string;
  reasoning: string;
}

interface ExperimentRequest {
  referenceTasks: ReferenceTask[];
  projects: Project[];
  inboxTasks: InboxTask[];
  promptVariant?: 'basic' | 'detailed' | 'few-shot';
}
```

## API Endpoint

**Route**: `/api/rd/classify-tasks`

### Request Format
```typescript
POST /api/rd/classify-tasks
{
  referenceTasks: ReferenceTask[];
  projects: Project[];
  inboxTasks: InboxTask[];
  promptVariant: string;
}
```

### Response Format
```typescript
{
  success: boolean;
  results: ClassificationResult[];
  promptUsed: string;
  usage: {
    inputTokens: number;
    outputTokens: number;
  };
  error?: string;
}
```

## Prompt Variants to Test

### 1. Basic Context
- Simple task list + projects
- Minimal instructions

### 2. Detailed Context  
- Reference tasks as examples
- Explicit attribute extraction rules
- Confidence scoring instructions

### 3. Few-Shot Learning
- Multiple reference examples per category
- Pattern recognition emphasis
- Tag consistency rules

## UI Layout

```
┌─────────────────────────────────────────┐
│ AI Task Classification Research Tool     │
├─────────────────────────────────────────┤
│ Reference Tasks (Training Data)         │
│ ┌─────────────────────────────────────┐ │
│ │ id;subject;tags;duration            │ │
│ │ 13;Mount socket;physical,1h;        │ │
│ │ ...                                 │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Current Projects                        │
│ ┌─────────────────────────────────────┐ │
│ │ pid;subject                         │ │
│ │ 3;Birthday party                    │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ Inbox Tasks to Classify                 │
│ ┌─────────────────────────────────────┐ │
│ │ Buy decorations                     │ │
│ │ Fix brake cable                     │ │
│ │ Paint accent wall                   │ │
│ └─────────────────────────────────────┘ │
├─────────────────────────────────────────┤
│ [Prompt Variant: Detailed ▼] [Classify]│
├─────────────────────────────────────────┤
│ Results                                 │
│ ┌─────────────────────────────────────┐ │
│ │ Task: Buy decorations               │ │
│ │ Project: Birthday party (95%)       │ │
│ │ Tags: shopping, physical            │ │
│ │ Duration: 30min                     │ │
│ │ Reasoning: Party-related shopping   │ │
│ └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```
