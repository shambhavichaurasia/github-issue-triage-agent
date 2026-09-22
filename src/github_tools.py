"""GitHub tools the agent can call. These work without an LLM."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from github import Auth, Github, GithubException


@dataclass
class IssueSummary:
    number: int
    title: str
    state: str
    author: str
    labels: list[str]
    body_preview: str
    comments_count: int
    html_url: str


@dataclass
class IssueDetail:
    number: int
    title: str
    state: str
    author: str
    labels: list[str]
    body: str
    comments: list[dict]
    html_url: str


class GitHubTools:
    def __init__(self, token: str) -> None:
        self._gh = Github(auth=Auth.Token(token))

    def list_open_issues(self, owner: str, repo: str, limit: int = 10) -> list[dict]:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        issues = repository.get_issues(state="open")
        results: list[IssueSummary] = []
        for issue in issues:
            if issue.pull_request:
                continue
            body = (issue.body or "").strip()
            results.append(
                IssueSummary(
                    number=issue.number,
                    title=issue.title,
                    state=issue.state,
                    author=issue.user.login if issue.user else "unknown",
                    labels=[label.name for label in issue.labels],
                    body_preview=(body[:400] + "…") if len(body) > 400 else body,
                    comments_count=issue.comments,
                    html_url=issue.html_url,
                )
            )
            if len(results) >= limit:
                break
        return [asdict(item) for item in results]

    def get_issue(self, owner: str, repo: str, number: int) -> dict:
        repository = self._gh.get_repo(f"{owner}/{repo}")
        issue = repository.get_issue(number)
        comments = []
        for comment in issue.get_comments():
            comments.append(
                {
                    "author": comment.user.login if comment.user else "unknown",
                    "body": (comment.body or "")[:500],
                }
            )
            if len(comments) >= 5:
                break
        detail = IssueDetail(
            number=issue.number,
            title=issue.title,
            state=issue.state,
            author=issue.user.login if issue.user else "unknown",
            labels=[label.name for label in issue.labels],
            body=(issue.body or "")[:4000],
            comments=comments,
            html_url=issue.html_url,
        )
        return asdict(detail)

    def search_code(self, owner: str, repo: str, query: str, limit: int = 5) -> list[dict]:
        """Search code in a public repo. Returns path + tiny snippet metadata."""
        try:
            results = self._gh.search_code(query=f"{query} repo:{owner}/{repo}")
            hits = []
            for item in results:
                hits.append(
                    {
                        "path": item.path,
                        "html_url": item.html_url,
                        "name": item.name,
                    }
                )
                if len(hits) >= limit:
                    break
            return hits
        except GithubException as exc:
            # Code search can fail on rate limits or empty index — return a clear message.
            return [{"error": str(exc.data.get("message", exc))}]


def parse_repo(repo_full_name: str) -> tuple[str, str]:
    parts = repo_full_name.strip().strip("/").split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError("Repo must look like owner/name (example: psf/requests)")
    return parts[0], parts[1]
