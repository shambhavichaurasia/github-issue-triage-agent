"""LLM client + triage agent loop (suggest only — never posts to GitHub)."""

from __future__ import annotations

import json
import re
import ssl
from typing import Any

import httpx
import truststore

from src.config import Settings
from src.github_tools import GitHubTools, parse_repo

SYSTEM_PROMPT = """You are a careful open-source issue triage assistant.
You MUST use tools when you need repository data.
You never post comments or change GitHub. You only SUGGEST.

Available tools:
1) list_open_issues(owner, repo, limit=5)
2) get_issue(owner, repo, number)
3) search_code(owner, repo, query)

When you have enough context, respond with ONLY this JSON:
{
  "issue_number": <int>,
  "suggested_labels": ["bug"|"enhancement"|"documentation"|"question"|"good first issue"],
  "confidence": <0.0-1.0>,
  "rationale": "<short why>",
  "draft_reply": "<helpful maintainer-style reply>",
  "related_files": ["path/if/known"]
}
"""


def _secure_http_client() -> httpx.Client:
    """Create a client that uses the operating system's trusted certificates."""
    ssl_context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return httpx.Client(timeout=60, verify=ssl_context)


def _chat_groq(api_key: str, model: str, messages: list[dict[str, str]]) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages, "temperature": 0.2}
    with _secure_http_client() as client:
        response = client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def _chat_gemini(api_key: str, model: str, messages: list[dict[str, str]]) -> str:
    # Convert OpenAI-style messages into one Gemini prompt string.
    lines = []
    for message in messages:
        lines.append(f"{message['role'].upper()}:\n{message['content']}")
    prompt = "\n\n".join(lines)
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    with _secure_http_client() as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


def chat(settings: Settings, messages: list[dict[str, str]]) -> str:
    provider, api_key, model = settings.require_llm_key()
    if provider == "groq":
        return _chat_groq(api_key, model, messages)
    return _chat_gemini(api_key, model, messages)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError(f"Model did not return JSON:\n{text}")
        return json.loads(match.group(0))


def _parse_tool_call(text: str) -> dict[str, Any] | None:
    """Allow the model to request a tool as JSON: {"tool": "...", "args": {...}}."""
    try:
        data = _extract_json(text)
    except (ValueError, json.JSONDecodeError):
        return None
    if isinstance(data, dict) and "tool" in data and "args" in data:
        return data
    return None


def run_triage(
    settings: Settings,
    repo_full_name: str,
    issue_number: int | None = None,
    max_steps: int = 4,
) -> dict[str, Any]:
    token = settings.require_github_token()
    tools = GitHubTools(token)
    owner, repo = parse_repo(repo_full_name)

    tool_trace: list[dict[str, Any]] = []
    user_goal = (
        f"Triage repo {owner}/{repo}. "
        + (
            f"Focus on issue #{issue_number}."
            if issue_number
            else "Pick one recent open issue that needs triage and analyze it."
        )
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                user_goal
                + "\n\nIf you need data, reply with ONLY JSON like:\n"
                '{"tool": "list_open_issues", "args": {"owner": "...", "repo": "...", "limit": 5}}\n'
                "When finished, reply with the final triage JSON described in the system prompt."
            ),
        },
    ]

    for _ in range(max_steps):
        raw = chat(settings, messages)
        tool_call = _parse_tool_call(raw)

        # Final answer if it looks like triage JSON (has suggested_labels).
        try:
            maybe_final = _extract_json(raw)
            if "suggested_labels" in maybe_final and "draft_reply" in maybe_final:
                return {"suggestion": maybe_final, "tool_trace": tool_trace, "raw": raw}
        except (ValueError, json.JSONDecodeError):
            pass

        if not tool_call:
            messages.append({"role": "assistant", "content": raw})
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Respond with either a tool JSON "
                        '{"tool": "...", "args": {...}} '
                        "or the final triage JSON."
                    ),
                }
            )
            continue

        name = tool_call["tool"]
        args = tool_call.get("args") or {}
        if name == "list_open_issues":
            result = tools.list_open_issues(
                args.get("owner", owner),
                args.get("repo", repo),
                int(args.get("limit", 5)),
            )
        elif name == "get_issue":
            result = tools.get_issue(
                args.get("owner", owner),
                args.get("repo", repo),
                int(args.get("number", issue_number or 1)),
            )
        elif name == "search_code":
            result = tools.search_code(
                args.get("owner", owner),
                args.get("repo", repo),
                str(args.get("query", "")),
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        tool_trace.append({"tool": name, "args": args, "result_preview": result})
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {
                "role": "user",
                "content": f"Tool result for {name}:\n{json.dumps(result)[:6000]}",
            }
        )

    return {
        "suggestion": None,
        "tool_trace": tool_trace,
        "error": "Reached max steps without a final triage suggestion.",
    }
