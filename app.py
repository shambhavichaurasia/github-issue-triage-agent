"""Streamlit demo for the GitHub Issue Triage Agent."""

from __future__ import annotations

import json

import streamlit as st

from src.agent import run_triage
from src.config import get_settings
from src.github_tools import GitHubTools, parse_repo

st.set_page_config(page_title="GitHub Issue Triage Agent", page_icon="🧾", layout="wide")
st.title("GitHub Issue Triage Agent")
st.caption(
    "Suggests labels + a draft reply for public GitHub issues. "
    "MVP never posts to GitHub — you approve or reject locally."
)

with st.sidebar:
    st.header("How to use")
    st.markdown(
        """
1. Copy `.env.example` → `.env`
2. Add `GITHUB_TOKEN` + Groq or Gemini key
3. Enter a public repo like `psf/requests`
4. Run triage → Approve / Reject the suggestion
        """
    )
    st.markdown("**Safety:** this app does not write to GitHub.")

repo = st.text_input("Public repository", value="psf/requests")
issue_number_raw = st.text_input("Issue number (optional)", value="")
col_a, col_b = st.columns(2)

if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "decision" not in st.session_state:
    st.session_state.decision = None

with col_a:
    list_clicked = st.button("List open issues only", use_container_width=True)
with col_b:
    run_clicked = st.button("Run triage agent", type="primary", use_container_width=True)

if list_clicked:
    try:
        settings = get_settings()
        owner, name = parse_repo(repo)
        tools = GitHubTools(settings.require_github_token())
        issues = tools.list_open_issues(owner, name, limit=8)
        st.subheader("Open issues")
        st.json(issues)
    except Exception as exc:  # noqa: BLE001 - show any setup error in the UI
        st.error(str(exc))

if run_clicked:
    try:
        settings = get_settings()
        issue_number = int(issue_number_raw) if issue_number_raw.strip() else None
        with st.spinner("Agent is calling tools and drafting a suggestion…"):
            result = run_triage(settings, repo, issue_number=issue_number)
        st.session_state.last_result = result
        st.session_state.decision = None
    except Exception as exc:  # noqa: BLE001
        st.error(str(exc))

result = st.session_state.last_result
if result:
    st.subheader("Tool trace")
    for step in result.get("tool_trace", []):
        with st.expander(f"Tool: {step['tool']}"):
            st.code(json.dumps(step, indent=2)[:4000])

    suggestion = result.get("suggestion")
    if suggestion:
        st.subheader("Suggestion (pending your approval)")
        st.json(suggestion)

        a, b, c = st.columns(3)
        with a:
            if st.button("Approve suggestion", type="primary"):
                st.session_state.decision = "approved"
        with b:
            if st.button("Reject suggestion"):
                st.session_state.decision = "rejected"
        with c:
            st.download_button(
                "Download suggestion JSON",
                data=json.dumps(suggestion, indent=2),
                file_name="triage_suggestion.json",
                mime="application/json",
            )

        if st.session_state.decision:
            st.success(f"Decision recorded locally: **{st.session_state.decision}**")
            st.info("v1 does not post to GitHub. That keep the demo safe and free.")
    elif result.get("error"):
        st.warning(result["error"])
        if result.get("raw"):
            st.code(result["raw"])
