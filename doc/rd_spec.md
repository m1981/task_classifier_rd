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

## Architecture Patterns

### DTOs (Data Transfer Objects)
**Purpose**: Clean separation between UI state and domain models
- `SaveDatasetRequest`: Encapsulates dataset save operations with validation
- `SaveDatasetResponse`: Structured response with success/error details
- **Benefits**: Type safety, validation encapsulation, API contract clarity

```python
@dataclass
class SaveDatasetRequest:
    name: str
    source_dataset: str
    projects: List[str]
    inbox_tasks: List[str]
    
    def validate(self) -> Optional[str]:
        # Built-in validation logic
```

### CQRS Commands
**Purpose**: Separate read/write operations with clear command boundaries
- `SaveDatasetCommand`: Handles dataset persistence with validation and error handling
- **Benefits**: Single responsibility, testable business logic, consistent error handling

```python
class SaveDatasetCommand:
    def execute(self, request: SaveDatasetRequest, source_dataset: DatasetContent) -> SaveDatasetResponse:
        # 1. Validate → 2. Project → 3. Persist → 4. Return structured response
```

### Data Projection
**Purpose**: Transform between different data representations without coupling
- `DatasetProjector`: Converts between UI state, DTOs, and domain models
- **Benefits**: Loose coupling, reusable transformations, clean boundaries

```python
class DatasetProjector:
    @staticmethod
    def from_ui_state(dataset: DatasetContent, name: str) -> SaveDatasetRequest
    
    @staticmethod  
    def project_for_save(dataset: DatasetContent, request: SaveDatasetRequest) -> DatasetContent
```

### Single Responsibility Principle
**Implementation**:
- `DatasetManager`: Only handles file I/O operations
- `TaskClassifier`: Only handles AI API communication
- `ResponseParser`: Only handles response parsing logic
- `PromptBuilder`: Only handles prompt construction
- **Benefits**: Easier testing, clearer debugging, maintainable code

### DRY (Don't Repeat Yourself)
**Implementation**:
- Shared validation logic in DTOs (`SaveDatasetRequest.validate()`)
- Reusable error handling patterns in `DatasetManager.save_dataset()`
- Common parsing utilities in `ResponseParser._parse_confidence()`
- Centralized service initialization in `get_services()`
- **Benefits**: Consistent behavior, single source of truth, easier maintenance

## API Contracts

### Dataset Management API
```python
# Load Dataset
DatasetManager.load_dataset(name: str) -> DatasetContent
# Raises: FileNotFoundError

# Save Dataset  
DatasetManager.save_dataset(name: str, content: DatasetContent) -> dict
# Returns: {"success": bool, "message": str, "type": str}

# List Datasets
DatasetManager.list_datasets() -> List[str]
```

### Classification API
```python
# Classify Tasks
TaskClassifier.classify(request: ClassificationRequest) -> ClassificationResponse
# Raises: RuntimeError for API failures

# Build Prompt
PromptBuilder.build_prompt(request: ClassificationRequest) -> str
# Auto-detects static vs dynamic prompts

# Parse Response
ResponseParser.parse(raw_response: str) -> List[ClassificationResult]
# Handles malformed responses gracefully
```

### Command API
```python
# Save Dataset Command
SaveDatasetCommand.execute(
    request: SaveDatasetRequest, 
    source_dataset: DatasetContent
) -> SaveDatasetResponse
# Encapsulates: Validate → Project → Persist → Response
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
├── dataset.yaml          # YAML format with projects and inbox_tasks
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
- ✅ CQRS command pattern
- ✅ DTO validation
- ✅ Data projection layer
- ✅ Single responsibility services
- ✅ DRY principle implementation
