import pytest

from agent.prompts import PromptLoadError, load


def test_load_renders_and_returns_version() -> None:
    text, version = load(
        "answer_from_context",
        context="fourteen days",
        user_question="How long is the refund window?",
    )
    assert version == "v1"
    assert "fourteen days" in text
    assert "How long is the refund window?" in text


def test_load_rejects_missing_placeholder() -> None:
    with pytest.raises(PromptLoadError):
        load("answer_from_context", context="only one")
