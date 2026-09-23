import pytest

from src.agent import _execute_scoped_tool, _extract_json, _unsafe_draft_reasons


class FakeGitHubTools:
    def __init__(self) -> None:
        self.last_call: tuple[str, dict] | None = None

    def list_open_issues(self, **kwargs):
        self.last_call = ("list_open_issues", kwargs)
        return []

    def get_issue(self, **kwargs):
        self.last_call = ("get_issue", kwargs)
        return {"number": kwargs["number"]}

    def search_code(self, **kwargs):
        self.last_call = ("search_code", kwargs)
        return []


@pytest.mark.parametrize(
    "draft",
    [
        "Thanks. We'll apply the patch directly.",
        "I will fix this in the next release.",
        "We can merge this change today.",
        "I've closed the issue.",
    ],
)
def test_unsafe_promises_are_detected(draft: str) -> None:
    assert _unsafe_draft_reasons(draft)


@pytest.mark.parametrize(
    "draft",
    [
        "Thanks for the report. This appears to be a documentation issue.",
        "The proposed change is ready for maintainer review.",
        "Could you provide a minimal reproduction and the Python version?",
    ],
)
def test_neutral_drafts_are_allowed(draft: str) -> None:
    assert _unsafe_draft_reasons(draft) == []


def test_extracts_json_from_markdown_fence() -> None:
    result = _extract_json('```json\n{"suggested_labels": ["bug"]}\n```')
    assert result["suggested_labels"] == ["bug"]


def test_rejects_text_without_json() -> None:
    with pytest.raises(ValueError, match="Model did not return JSON"):
        _extract_json("This response contains no structured result.")


def test_tool_cannot_switch_repository() -> None:
    tools = FakeGitHubTools()
    executed_args, _ = _execute_scoped_tool(
        tools,
        "list_open_issues",
        {"owner": "attacker", "repo": "other", "limit": 999},
        "psf",
        "requests",
        None,
    )

    assert executed_args == {"owner": "psf", "repo": "requests", "limit": 10}
    assert tools.last_call == ("list_open_issues", executed_args)


def test_selected_issue_number_cannot_be_changed() -> None:
    tools = FakeGitHubTools()
    executed_args, _ = _execute_scoped_tool(
        tools,
        "get_issue",
        {"owner": "attacker", "repo": "other", "number": 1},
        "psf",
        "requests",
        7627,
    )

    assert executed_args["number"] == 7627
    assert executed_args["owner"] == "psf"
    assert executed_args["repo"] == "requests"


def test_empty_code_search_is_not_executed() -> None:
    tools = FakeGitHubTools()
    _, result = _execute_scoped_tool(
        tools, "search_code", {"query": "   "}, "psf", "requests", None
    )

    assert result == {"error": "search_code requires a non-empty query"}
    assert tools.last_call is None
