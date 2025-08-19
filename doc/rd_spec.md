# Research & Development: AI Task Classification Experiment

## Overview

Production-ready MVP for experimenting with AI task classification using Anthropic Claude. Built with Streamlit for rapid iteration and dataset management. Designed to optimize AI prompts and evaluate classification accuracy across different domains (personal productivity, home renovation, etc.).

## Architecture

### Core Services
- **DatasetManager**: File-based dataset persistence (`data/datasets/{name}/`)
- **TaskClassifier**: Claude API integration with error handling
- **PromptBuilder**: Configurable prompt strategies for experimentation
- **ResponseParser**: Robust parsing with fallback handling

### UI Features
- **Real-time Dataset Editing**: Modify projects/tasks without file system access
- **Confidence Analysis**: Visual breakdown of classification quality
- **Results Review**: Flagging system for low-confidence/unmatched tasks
- **Prompt Preview**: Live preview of AI prompts before execution
- **Debug Mode**: Full request/response inspection

## Enhanced Data Models

```typescript
interface ClassificationResult {
  task: string;
  suggestedProject: string;
  confidence: number;
  extractedTags: string[];
  estimatedDuration?: string;
  reasoning: string;
  alternativeProjects: string[]; // NEW: Alternative project suggestions
}

interface ClassificationResponse {
  results: ClassificationResult[];
  promptUsed: string;
  rawResponse: string; // NEW: Full AI response for debugging
}
```

## Current Prompt Strategies

### 1. Basic Context
- Simple task organization guidance
- Minimal AI persona

### 2. DIY Renovation Expert
- Domain-specific expertise (home improvement)
- Safety and skill level considerations
- Material/tool requirements focus

## Tag System

**Core Tags:**
- `physical` / `digital` - Task nature
- `out` - Requires leaving home
- `need-material` - Purchase requirements
- `need-tools` - Tool requirements  
- `buy` - Shopping list items

**Domain-Specific Extensions:**
- Renovation: `electrical`, `plumbing`, `carpentry`, `painting`, `tiling`
- Duration estimates: `15min`, `1h`, `4h`, etc.

## Results Analysis Features

### Confidence Scoring
- **High (≥80%)**: ✅ Ready to use
- **Medium (60-79%)**: ⚠️ Review recommended  
- **Low (<60%)**: ❓ Manual review required
- **Unmatched**: 🔍 No suitable project found

### Review System
- Automatic flagging of problematic classifications
- Alternative project suggestions
- Reasoning explanations for manual review

## Dataset Structure

```
data/datasets/{name}/
├── reference_tasks.txt    # id;subject;tags;duration
├── projects.txt          # pid;subject  
└── inbox_tasks.txt       # one task per line
```

## API Integration

**Model**: Claude 3.5 Haiku (fast, cost-effective)
**Max Tokens**: 2000
**Error Handling**: Comprehensive with user-friendly messages

## Production Considerations

### Implemented
- ✅ Structured error handling
- ✅ Session state management
- ✅ File-based persistence
- ✅ Debug logging
- ✅ Response validation
