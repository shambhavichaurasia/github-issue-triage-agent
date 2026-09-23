"""Build a small benchmark from labeled issues in public GitHub repositories."""

from __future__ import annotations

import json
from pathlib import Path

from github import Auth, Github

from src.config import get_settings

OUTPUT_PATH = Path(__file__).with_name("public_cases.json")

# Two public examples per normalized label. The repository's own label is treated
# as the expected answer, so every case remains traceable to its source.
SOURCES = [
    ("psf/requests", "Bug", "bug"),
    ("fastapi/fastapi", "bug", "bug"),
    ("psf/requests", "Documentation", "documentation"),
    ("fastapi/fastapi", "docs", "documentation"),
    ("psf/requests", "Feature Request", "enhancement"),
    ("fastapi/fastapi", "feature", "enhancement"),
    ("psf/requests", "Question/Not a bug", "question"),
    ("fastapi/fastapi", "question", "question"),
]


def build_public_cases() -> list[dict[str, str | int]]:
    settings = get_settings()
    github = Github(auth=Auth.Token(settings.require_github_token()))
    cases: list[dict[str, str | int]] = []

    for repo_name, source_label, expected_label in SOURCES:
        repository = github.get_repo(repo_name)
        selected = None
        for issue in repository.get_issues(
            state="all", labels=[source_label], sort="created", direction="desc"
        ):
            if issue.pull_request is None and (issue.body or "").strip():
                selected = issue
                break

        if selected is None:
            raise RuntimeError(
                f"No usable public issue found for {repo_name} / {source_label}"
            )

        cases.append(
            {
                "id": f"{repo_name.replace('/', '-')}-{selected.number}",
                "source_repo": repo_name,
                "issue_number": selected.number,
                "source_url": selected.html_url,
                "source_label": source_label,
                "title": selected.title,
                "body": (selected.body or "").strip()[:800],
                "expected_label": expected_label,
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps(cases, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return cases


if __name__ == "__main__":
    built_cases = build_public_cases()
    print(f"Saved {len(built_cases)} public cases to {OUTPUT_PATH}")
