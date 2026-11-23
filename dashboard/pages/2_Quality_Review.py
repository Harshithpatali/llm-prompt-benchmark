"""Authenticated human-review queue for the LLM Quality Intelligence API."""
import os
from datetime import datetime, timezone

import requests
import streamlit as st

st.set_page_config(page_title="Human Quality Review", page_icon="🧪", layout="wide")
st.title("Human Quality Review")
st.caption("Review candidate responses against their supplied context and guidance. Human labels are review evidence, not infallible ground truth.")

def setting(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default))).strip()
    except Exception:
        return os.getenv(name, default).strip()

API_BASE_URL = setting("API_BASE_URL", "https://llm-prompt-benchmark.onrender.com").rstrip("/")
API_KEY = setting("REVIEW_API_KEY")
TIMEOUT = 30

if not API_KEY:
    st.error("Reviewer access is not configured. Add REVIEW_API_KEY to Streamlit Cloud Secrets.")
    st.code('API_BASE_URL = "https://llm-prompt-benchmark.onrender.com"\nREVIEW_API_KEY = "the-same-secret-configured-on-Render"')
    st.stop()

def api(method: str, path: str, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-Review-API-Key"] = API_KEY
    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            st.error(f"API returned {response.status_code}: {detail}")
            return None
        return response.json() if response.content else {}
    except requests.RequestException as exc:
        st.error(f"Could not reach the API: {exc}")
        return None

health_col, refresh_col = st.columns([3, 1])
with health_col:
    st.caption(f"API: {API_BASE_URL}")
with refresh_col:
    if st.button("Refresh queue", use_container_width=True):
        st.rerun()

health = api("GET", "/database/health")
if health:
    st.success(f"API and database connected · {health.get('database', 'PostgreSQL')}")

with st.expander("Load authored starter scenarios"):
    st.warning("This imports 16 authored seller-support examples as unlabelled review tasks. They are not real customer records or validated gold labels.")
    if st.button("Seed review tasks"):
        seeded = api("POST", "/quality/review-tasks/seed")
        if seeded:
            st.success(f"Seed operation completed. Source tasks: {seeded.get('tasks_in_source', 0)}; inserted or already present: {seeded.get('inserted_or_existing', 0)}")
            st.rerun()

annotator_id = st.text_input("Pseudonymous reviewer ID", placeholder="e.g. reviewer-01", help="Do not enter your name, email, or other personal information.")
status_filter = st.selectbox("Queue status", ["pending", "claimed", "submitted", "adjudicated", "cancelled", "All"], index=0)
status = None if status_filter == "All" else status_filter
params = {"limit": 200, "offset": 0}
if status:
    params["status"] = status
payload = api("GET", "/quality/review-tasks", params=params)
tasks = payload.get("tasks", []) if payload else []

st.subheader("Review queue")
st.metric("Tasks returned", len(tasks))
if not tasks:
    st.info("No tasks match this filter. Seed the authored examples or select another status.")
else:
    options = {f"{t.get('task_key', t.get('annotation_task_id'))} · {t.get('category', 'uncategorized')} · {str(t.get('query', ''))[:85]}": t for t in tasks}
    selected_label = st.selectbox("Choose a task", list(options))
    task = options[selected_label]
    st.markdown(f"**Category:** {task.get('category', '—')}　 **Difficulty:** {task.get('difficulty', '—')}　 **Status:** {task.get('status', '—')}")
    left, right = st.columns(2)
    with left:
        st.markdown("#### User request")
        st.write(task.get("query", ""))
        st.markdown("#### Context")
        st.write(task.get("context") or "No context supplied.")
    with right:
        st.markdown("#### Candidate response")
        st.write(task.get("candidate_response", ""))
        with st.expander("Review guidance / reference"):
            st.write(task.get("review_guidance", ""))

    st.divider()
    st.markdown("#### Submit human assessment")
    with st.form("annotation_form", clear_on_submit=False):
        dimensions = {}
        cols = st.columns(3)
        choices = ["pass", "minor_issue", "major_issue", "not_applicable"]
        for col, dimension in zip(cols, ["relevance", "correctness", "completeness"]):
            with col:
                dimensions[dimension] = st.selectbox(dimension.title(), choices, key=f"dim_{dimension}")
        overall = st.selectbox("Overall decision", ["accept", "revise", "reject", "escalate"])
        evidence = st.text_area("Evidence and rationale (required)", placeholder="Quote or describe the specific content that supports your assessment.", max_chars=4000)
        confidence = st.slider("Confidence", 1, 5, 3)
        handling_seconds = st.number_input("Handling time (seconds)", min_value=0, step=5, value=0)
        escalated = st.checkbox("Escalate for specialist review", value=(overall == "escalate"))
        defect_category = st.selectbox("Primary defect category", ["none", "factual_consistency", "policy_compliance", "relevance", "completeness", "instruction_following", "tone", "other"])
        is_audit = st.checkbox("This is an audit sample")
        submitted = st.form_submit_button("Submit annotation", type="primary", use_container_width=True)
    if submitted:
        if not annotator_id.strip():
            st.error("Enter a pseudonymous reviewer ID before submitting.")
        elif len(evidence.strip()) < 8:
            st.error("Evidence must contain at least 8 characters.")
        else:
            body = {
                "annotator_id": annotator_id.strip(),
                "dimensions": dimensions,
                "overall_label": overall,
                "evidence": evidence.strip(),
                "confidence": confidence,
                "handling_seconds": int(handling_seconds),
                "escalated": escalated,
                "defect_category": defect_category,
                "is_audit": is_audit,
            }
            result = api("POST", f"/quality/review-tasks/{task['annotation_task_id']}/annotations", json=body)
            if result:
                st.success("Annotation saved and audit event recorded.")
                st.rerun()

st.divider()
st.subheader("Recent submitted annotations")
history = api("GET", "/quality/annotations", params={"limit": 100, "offset": 0})
annotations = history.get("annotations", []) if history else []
if annotations:
    st.dataframe(annotations, use_container_width=True, hide_index=True)
else:
    st.caption("No annotations have been submitted yet.")
