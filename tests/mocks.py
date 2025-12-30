from unittest.mock import MagicMock
from models.ai_schemas import ClassificationResult, ClassificationType, SmartFilterResult


class MockAIClient:
    def __init__(self):
        self.beta = MagicMock()
        self.beta.messages.parse.side_effect = self._handle_parse

    def _handle_parse(self, **kwargs):
        """
        Intercepts the AI call and returns a specific Pydantic model
        based on the prompt content.
        """
        messages = kwargs.get('messages', [])
        user_content = messages[0]['content'] if messages else ""
        content_lower = user_content.lower()

        # --- SCENARIO 1: TRIAGE (Task/Shopping) ---
        if 'incoming item: "buy milk"' in content_lower:
            return self._wrap_result(ClassificationResult(
                classification_type=ClassificationType.SHOPPING,
                suggested_project="Groceries",
                confidence=0.99,
                reasoning="It is a purchase.",
                refined_text="Milk",
                extracted_tags=["errand"]
            ))

        # --- SCENARIO: INCUBATE (Someday/Maybe) ---
        if 'incoming item: "learn guitar someday"' in content_lower:
            return self._wrap_result(ClassificationResult(
                classification_type=ClassificationType.INCUBATE,
                suggested_project="Unmatched",
                confidence=0.8,
                reasoning="Not actionable now.",
                refined_text="Learn Guitar",
                extracted_tags=[]
            ))

        # --- SCENARIO: REFERENCE (URL/Info) ---
        if 'incoming item: "http://wiki.com"' in content_lower:
            return self._wrap_result(ClassificationResult(
                classification_type=ClassificationType.REFERENCE,
                suggested_project="Groceries",
                confidence=0.95,
                reasoning="It is a link.",
                refined_text="Cool Article",
                extracted_tags=[]
            ))

        # --- SCENARIO: NEW PROJECT ---
        if 'incoming item: "start a new project"' in content_lower:
            return self._wrap_result(ClassificationResult(
                classification_type=ClassificationType.NEW_PROJECT,
                suggested_project="Unmatched",
                suggested_new_project_name="New Big Goal",
                confidence=0.9,
                reasoning="Multi-step outcome.",
                refined_text="Launch Rocket",
                extracted_tags=[]
            ))

        # --- SCENARIO: TRASH CANDIDATE ---
        if 'incoming item: "total junk text"' in content_lower:
            return self._wrap_result(ClassificationResult(
                classification_type=ClassificationType.TASK,
                suggested_project="Groceries",
                confidence=0.2,  # Low confidence
                reasoning="Unsure.",
                refined_text="Junk text",
                extracted_tags=[]
            ))

        # --- SCENARIO: SMART FILTER ---
        if "user query" in content_lower:
            return self._wrap_result(SmartFilterResult(
                matching_task_ids=["task-123"],
                reasoning="Matches context.",
                estimated_total_time="1h"
            ))

        # Default Fallback
        return self._wrap_result(ClassificationResult(
            classification_type=ClassificationType.TASK,
            suggested_project="Groceries",
            confidence=0.5,
            reasoning="Default Fallback",
            refined_text="Generic Task",
            extracted_tags=[]
        ))

    def _wrap_result(self, pydantic_obj):
        """Wraps the result to mimic the Anthropic SDK structure"""
        mock_response = MagicMock()
        mock_response.parsed_output = pydantic_obj
        return mock_response