import pytest
from pydantic import ValidationError

from src.models import TriageSuggestion


def valid_suggestion() -> dict:
    return {
        "issue_number": 42,
        "suggested_labels": ["bug"],
        "confidence": 0.9,
        "rationale": "The reproduction describes an unexpected application crash.",
        "draft_reply": "Thanks for the report. This appears to be reproducible.",
        "related_files": ["src/parser.py"],
    }


def test_accepts_valid_suggestion() -> None:
    suggestion = TriageSuggestion.model_validate(valid_suggestion())
    assert suggestion.suggested_labels == ["bug"]


@pytest.mark.parametrize("confidence", [-0.1, 1.1])
def test_rejects_confidence_outside_range(confidence: float) -> None:
    data = valid_suggestion()
    data["confidence"] = confidence
    with pytest.raises(ValidationError):
        TriageSuggestion.model_validate(data)


def test_rejects_unknown_label() -> None:
    data = valid_suggestion()
    data["suggested_labels"] = ["urgent"]
    with pytest.raises(ValidationError):
        TriageSuggestion.model_validate(data)


def test_rejects_missing_required_field() -> None:
    data = valid_suggestion()
    del data["draft_reply"]
    with pytest.raises(ValidationError):
        TriageSuggestion.model_validate(data)


def test_rejects_extra_fields() -> None:
    data = valid_suggestion()
    data["auto_merge"] = True
    with pytest.raises(ValidationError):
        TriageSuggestion.model_validate(data)
