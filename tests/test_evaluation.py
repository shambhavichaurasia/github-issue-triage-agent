import pytest

from src.evaluation import _extract_json_array, score_predictions


def test_scores_predictions() -> None:
    cases = [
        {"id": "1", "title": "Crash", "expected_label": "bug"},
        {"id": "2", "title": "Typo", "expected_label": "documentation"},
    ]
    predictions = [
        {"id": "1", "predicted_label": "bug"},
        {"id": "2", "predicted_label": "question"},
    ]

    report = score_predictions(cases, predictions)

    assert report["correct"] == 1
    assert report["total"] == 2
    assert report["accuracy"] == 0.5


def test_missing_prediction_is_incorrect() -> None:
    cases = [{"id": "1", "title": "Crash", "expected_label": "bug"}]

    report = score_predictions(cases, [])

    assert report["accuracy"] == 0.0
    assert report["results"][0]["predicted"] == "missing"


def test_extracts_array_from_markdown() -> None:
    result = _extract_json_array(
        '```json\n[{"id": "1", "predicted_label": "bug"}]\n```'
    )
    assert result == [{"id": "1", "predicted_label": "bug"}]


def test_rejects_non_array_response() -> None:
    with pytest.raises(ValueError, match="JSON array"):
        _extract_json_array('{"id": "1", "predicted_label": "bug"}')
