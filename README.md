# GitHub Issue Triage Agent

Agentic AI project that **reads public GitHub issues**, optionally **searches code**, and **suggests labels + a draft maintainer reply**.

**Human approval required.** v1 never posts comments or changes GitHub.

Built for a student portfolio / SDE-1 agentic AI interviews (free stack).

## What recruiters should hear (30 sec)

> I built a tool-calling agent over the GitHub API. It lists issues, reads an issue, can search code, then drafts labels and a reply. Nothing is written back unless a human approves — and in this MVP we only record approve/reject locally.

## Features (MVP)

- Tool calling: `list_open_issues`, `get_issue`, `search_code`
- Structured suggestion: labels, confidence, rationale, draft reply
- Tool trace visible in the UI
- Local Approve / Reject (no GitHub write)
- Free LLM: Groq **or** Gemini

## Stack

| Piece | Choice |
|--------|--------|
| Language | Python |
| UI | Streamlit |
| GitHub | PyGithub + personal access token |
| LLM | Groq or Gemini (free tier) |
| Config | `.env` |

## Setup (local)

```bash
cd github-issue-triage-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

1. `GITHUB_TOKEN` — [create a classic PAT](https://github.com/settings/tokens) (read access to public repos is enough)
2. Pick **one**:
   - `LLM_PROVIDER=groq` + `GROQ_API_KEY` from [Groq Console](https://console.groq.com/keys)
   - `LLM_PROVIDER=gemini` + `GEMINI_API_KEY` from [Google AI Studio](https://aistudio.google.com/apikey)

Run:

```bash
streamlit run app.py
```

Try repo: `psf/requests` (public, always available).

## Project layout

```text
app.py                 # Streamlit UI
src/config.py          # env settings
src/github_tools.py    # tools (work even without LLM)
src/agent.py           # LLM + tool loop
examples/              # sample outputs for README/resume
```

## Resume bullets (draft)

- Built a tool-calling GitHub issue triage agent (list/read issues, search code, draft labels + replies)
- Added a human approval gate so the agent cannot write to GitHub without review
- Shipped a Streamlit demo on a free stack (Groq/Gemini + public GitHub API)

## Next (after MVP works)

- Deploy to Hugging Face Spaces
- Optional: post comment only after explicit approve + write-scope token
- Tiny eval set: 10 saved issues → did labels look reasonable?

## Sibling portfolio projects (separate repos)

2. Study Notes RAG Agent  
3. Multi-Agent Research Brief Generator  
