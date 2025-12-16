import pytest
from services.services import PromptBuilder
from models.dtos import SingleTaskClassificationRequest


def test_prompt_builder_handles_empty_projects():
    """
    Catch Error: When no projects exist, the prompt should be explicit
    rather than showing an empty JSON array '[]' which confuses the LLM.
    """
    builder = PromptBuilder()
    req = SingleTaskClassificationRequest(
        task_text="Buy Milk",
        available_projects=[]
    )

    prompt = builder.build_single_task_prompt(req)

    # FAILURE CONDITION: The current code outputs "Available Projects: []"
    # EXPECTED: "Available Projects: None" or similar explicit text
    assert "Available Projects: []" not in prompt
    assert "Available Projects: None" in prompt


def test_prompt_builder_sanitizes_quotes():
    """
    Catch Error: If a project name has quotes, it breaks the prompt syntax.
    """
    builder = PromptBuilder()
    req = SingleTaskClassificationRequest(
        task_text="Fix door",
        available_projects=['Guest "Suite"', "Kitchen"]
    )

    prompt = builder.build_single_task_prompt(req)

    # FAILURE CONDITION: Current code produces "Guest "Suite"" which breaks parsing
    assert '"Guest "Suite""' not in prompt
    # EXPECTED: Quotes should be escaped or replaced
    assert "Guest 'Suite'" in prompt or 'Guest \\"Suite\\"' in prompt