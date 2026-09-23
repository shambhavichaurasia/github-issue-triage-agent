"""Validated data structures returned by the triage agent."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

IssueLabel = Literal[
    "bug",
    "enhancement",
    "documentation",
    "question",
    "good first issue",
]


class TriageSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(gt=0)
    suggested_labels: list[IssueLabel] = Field(min_length=1, max_length=5)
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = Field(min_length=10, max_length=1000)
    draft_reply: str = Field(min_length=10, max_length=2000)
    related_files: list[str] = Field(default_factory=list, max_length=10)
