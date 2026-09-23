"""Streamlit demo for the GitHub Issue Triage Agent."""

from __future__ import annotations

import json

import streamlit as st

from src.agent import LLMRateLimitError, run_triage
from src.config import get_settings
from src.evaluation import run_label_evaluation, run_public_label_evaluation
from src.github_tools import GitHubTools, parse_repo

st.set_page_config(page_title="GitHub Issue Triage Agent", page_icon="🧾", layout="wide")
st.title("GitHub Issue Triage Agent")
st.caption(
    "Suggests labels + a draft reply for public GitHub issues. "
    "MVP never posts to GitHub — you approve or reject locally."
)

with st.sidebar:
    st.header("Demo")
    st.markdown(
        """
- Enter a public repository such as `psf/requests`
- Optionally enter an issue number such as `7627`
- Run triage and review the suggestion
- Use the benchmarks to inspect label accuracy
        """
    )
    st.markdown("**Read-only:** this app never writes to GitHub.")
    st.caption("The public demo uses free-tier APIs and may be temporarily rate-limited.")

repo = st.text_input("Public repository", value="psf/requests")
issue_number_raw = st.text_input("Issue number (optional)", value="")
col_a, col_b = st.columns(2)

if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "decision" not in st.session_state:
    st.session_state.decision = None
if "eval_report" not in st.session_state:
    st.session_state.eval_report = None
if "edited_reply" not in st.session_state:
    st.session_state.edited_reply = ""

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
        if issue_number_raw.strip():
            try:
                issue_number = int(issue_number_raw)
            except ValueError as exc:
                raise ValueError("Issue number must be a positive whole number.") from exc
            if issue_number <= 0:
                raise ValueError("Issue number must be a positive whole number.")
        else:
            issue_number = None
        with st.spinner("Agent is calling tools and drafting a suggestion…"):
            result = run_triage(settings, repo, issue_number=issue_number)
        st.session_state.last_result = result
        st.session_state.decision = None
        suggestion = result.get("suggestion")
        if suggestion:
            st.session_state.edited_reply = suggestion["draft_reply"]
    except LLMRateLimitError as exc:
        st.warning(str(exc))
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
        if result.get("safety_revisions", 0):
            st.info(
                "The safety checker detected an authority claim and made the AI "
                "rewrite this draft before showing it."
            )

        labels_col, confidence_col = st.columns([3, 1])
        with labels_col:
            st.markdown("**Suggested labels**")
            st.write(" · ".join(suggestion["suggested_labels"]))
        with confidence_col:
            st.metric("Confidence", f"{suggestion['confidence']:.0%}")

        st.markdown("**Rationale**")
        st.write(suggestion["rationale"])

        if suggestion["related_files"]:
            st.markdown("**Related files**")
            st.code("\n".join(suggestion["related_files"]))

        edited_reply = st.text_area(
            "Draft reply (editable before approval)",
            key="edited_reply",
            height=180,
        )
        reviewed_suggestion = {**suggestion, "draft_reply": edited_reply}

        with st.expander("View structured JSON"):
            st.json(reviewed_suggestion)

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
                data=json.dumps(reviewed_suggestion, indent=2),
                file_name="triage_suggestion.json",
                mime="application/json",
            )

        if st.session_state.decision:
            st.success(f"Decision recorded locally: **{st.session_state.decision}**")
            st.info("v1 does not post to GitHub. That keeps the demo safe and free.")
    elif result.get("error"):
        st.warning(result["error"])
        if result.get("raw"):
            st.code(result["raw"])

st.divider()
with st.expander("Evaluate label accuracy"):
    st.write(
        "Each benchmark runs 8 issues through Groq in one batch request, "
        "then compares its labels with expected answers. Public cases include source URLs."
    )
    synthetic_col, public_col = st.columns(2)
    with synthetic_col:
        run_synthetic = st.button(
            "Run synthetic benchmark", use_container_width=True
        )
    with public_col:
        run_public = st.button("Run public benchmark", use_container_width=True)

    if run_synthetic or run_public:
        try:
            with st.spinner("Evaluating 8 issues…"):
                evaluation = (
                    run_public_label_evaluation
                    if run_public
                    else run_label_evaluation
                )
                st.session_state.eval_report = evaluation(get_settings())
        except LLMRateLimitError as exc:
            st.warning(str(exc))
        except Exception as exc:  # noqa: BLE001
            st.error(str(exc))

    report = st.session_state.eval_report
    if report:
        dataset_name = report.get("dataset", "cases").replace("_", " ").title()
        st.caption(f"Dataset: {dataset_name}")
        st.metric(
            "Label accuracy",
            f"{report['accuracy']:.0%}",
            f"{report['correct']} of {report['total']} correct",
        )
        if report["invalid_labels"]:
            st.warning(
                "Unexpected labels returned: " + ", ".join(report["invalid_labels"])
            )
        st.dataframe(report["results"], use_container_width=True, hide_index=True)

        incorrect_results = [
            item for item in report["results"] if not item["correct"]
        ]
        if incorrect_results:
            st.subheader("Mismatch analysis")
            st.caption(
                "Expected means the repository's existing label. Predicted means "
                "the AI's label from the issue text. A mismatch can reveal either "
                "an AI error or an ambiguous repository convention."
            )
            for item in incorrect_results:
                with st.expander(item["title"]):
                    expected_col, predicted_col = st.columns(2)
                    expected_col.metric("Repository label", item["expected"])
                    predicted_col.metric("AI prediction", item["predicted"])
                    if item["source"] != "synthetic":
                        st.link_button("Open original GitHub issue", item["source"])
