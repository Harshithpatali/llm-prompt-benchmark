"""Human Quality Review — evidence-led annotation workflow."""
import os
import requests
import streamlit as st

st.set_page_config(page_title="Human Quality Review", page_icon="🧪", layout="wide")
API_URL = os.getenv("API_BASE_URL", "https://llm-prompt-benchmark.onrender.com").rstrip("/")


def secret(name, fallback=""):
    try:
        return str(st.secrets.get(name, os.getenv(name, fallback))).strip()
    except Exception:
        return os.getenv(name, fallback).strip()


def api(method, path, **kwargs):
    headers = kwargs.pop("headers", {})
    headers["X-Review-API-Key"] = st.session_state.get("quality_review_key", "")
    response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=kwargs.pop("timeout", 60), **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")
    return response.json() if response.content else {}


st.title("🧪 Human Quality Review")
st.caption("Inspect an assistant answer, compare it with the supplied context and guidance, then submit an evidence-backed assessment.")

with st.sidebar:
    st.subheader("Reviewer settings")
    default_key = secret("REVIEW_API_KEY") or st.session_state.get("quality_review_key", "")
    key = st.text_input("Review API key", type="password", value=default_key, help="Required to access and submit review tasks.")
    if key:
        st.session_state["quality_review_key"] = key
    st.caption("Use a pseudonymous reviewer ID. Do not enter personal information into review records.")

if not st.session_state.get("quality_review_key"):
    st.info("Enter the review API key in the sidebar to open the queue.")
    st.stop()

try:
    health = api("GET", "/database/health", timeout=10)
    st.success(f"Connected to evaluation API · {health.get('database', 'PostgreSQL')}")
except Exception as exc:
    st.error(f"Could not confirm backend connection: {exc}")

with st.expander("How this workflow works", expanded=False):
    st.markdown("1. Load the authored starter scenarios or open an existing queue.\n2. Select a pending task and read the prompt, context and candidate answer.\n3. Rate relevance, correctness and completeness.\n4. Record specific evidence and submit your decision.")
    st.warning("The 16 starter scenarios are authored examples, not real customer records or validated gold labels.")

st.subheader("1 · Prepare the review queue")
seed_col, refresh_col = st.columns([2, 1])
with seed_col:
    if st.button("Load 16 starter scenarios", type="primary", use_container_width=True):
        try:
            with st.spinner("Importing authored review tasks…"):
                result = api("POST", "/quality/review-tasks/seed")
            st.success(f"Seed complete · {result.get('tasks_in_source', 0)} source scenarios · {result.get('inserted_or_existing', 0)} inserted or already present")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not load starter scenarios: {exc}")
with refresh_col:
    if st.button("Refresh queue", use_container_width=True):
        st.rerun()

st.divider()
st.subheader("2 · Find a task")
filter_col, reviewer_col = st.columns([1, 1])
with filter_col:
    status_filter = st.selectbox("Queue status", ["pending", "claimed", "submitted", "adjudicated", "cancelled", "All"], index=0)
with reviewer_col:
    reviewer_id = st.text_input("Pseudonymous reviewer ID", placeholder="e.g. reviewer-01", help="Use a stable alias such as reviewer-01.")

params = {"limit": 200, "offset": 0}
if status_filter != "All":
    params["status"] = status_filter
try:
    queue = api("GET", "/quality/review-tasks", params=params)
    tasks = queue.get("tasks", [])
except Exception as exc:
    st.error(f"Could not load review tasks: {exc}")
    tasks = []

submitted_count = sum(1 for t in tasks if t.get("status") in {"submitted", "adjudicated"})
pending_count = sum(1 for t in tasks if t.get("status") == "pending")
a, b, c = st.columns(3)
a.metric("Tasks in this view", len(tasks))
b.metric("Pending in this view", pending_count)
c.metric("Submitted / adjudicated", submitted_count)

if not tasks:
    st.info("No tasks match this filter. Use **Load 16 starter scenarios** or change the queue status.")
else:
    options = {
        f"{t.get('category', 'General')} · {t.get('difficulty', 'Unrated')} · {str(t.get('query', ''))[:75]}": t
        for t in tasks
    }
    selected_label = st.selectbox("Choose a review task", list(options))
    task = options[selected_label]
    st.markdown(f"**Task status:** {task.get('status', '—')}　 ·　 **Category:** {task.get('category', '—')}　 ·　 **Difficulty:** {task.get('difficulty', '—')}")
    with st.container(border=True):
        st.markdown("#### User request")
        st.write(task.get("query") or "No request supplied.")
        st.divider()
        st.markdown("#### Context and reference material")
        st.write(task.get("context") or "No context supplied.")
        st.divider()
        st.markdown("#### Candidate assistant response")
        st.write(task.get("candidate_response") or "No candidate response supplied.")
        with st.expander("Review guidance"):
            st.write(task.get("review_guidance") or "No additional guidance supplied.")

    st.subheader("3 · Submit your assessment")
    with st.form("human_quality_annotation", clear_on_submit=False):
        st.caption("Judge only what is supported by the prompt, context and response. Quote or point to concrete evidence.")
        dimensions = {}
        for dimension in ["relevance", "correctness", "completeness"]:
            dimensions[dimension] = st.radio(
                dimension.title(),
                ["pass", "minor_issue", "major_issue", "not_applicable"],
                horizontal=True,
                key=f"review_{task.get('annotation_task_id')}_{dimension}",
                help="Pass = meets requirement; Minor issue = limited defect; Major issue = material defect; N/A = not assessable.",
            )
        overall = st.selectbox("Overall decision", ["accept", "revise", "reject", "escalate"])
        evidence = st.text_area("Evidence and rationale", height=130, max_chars=4000, placeholder="Identify the exact sentence, omission or behavior that supports your decision.")
        left, right = st.columns(2)
        with left:
            confidence = st.slider("Confidence", 1, 5, 4)
            handling_seconds = st.number_input("Review time (seconds)", min_value=0, step=10, value=0)
        with right:
            defect_category = st.selectbox("Primary defect category", ["none", "factual_consistency", "policy_compliance", "relevance", "completeness", "instruction_following", "tone", "other"])
            escalated = st.checkbox("Escalate for specialist review", value=False)
            is_audit = st.checkbox("Mark as audit sample", value=False)
        submitted = st.form_submit_button("Submit human review", type="primary", use_container_width=True)
    if submitted:
        if not reviewer_id.strip():
            st.error("Enter your pseudonymous reviewer ID above.")
        elif len(evidence.strip()) < 8:
            st.error("Add at least eight characters of specific evidence.")
        else:
            body = {
                "annotator_id": reviewer_id.strip(),
                "dimensions": dimensions,
                "overall_label": overall,
                "evidence": evidence.strip(),
                "confidence": confidence,
                "handling_seconds": int(handling_seconds),
                "escalated": escalated or overall == "escalate",
                "defect_category": defect_category,
                "is_audit": is_audit,
            }
            try:
                api("POST", f"/quality/review-tasks/{task['annotation_task_id']}/annotations", json=body)
                st.success("Review submitted and audit event recorded.")
                st.rerun()
            except Exception as exc:
                st.error(f"Could not submit annotation: {exc}")

st.divider()
st.subheader("Recent submitted annotations")
try:
    history = api("GET", "/quality/annotations", params={"limit": 50, "offset": 0})
    annotations = history.get("annotations", [])
    if annotations:
        st.dataframe(annotations, use_container_width=True, hide_index=True)
    else:
        st.caption("No annotations have been submitted yet.")
except Exception as exc:
    st.caption(f"Annotation history is currently unavailable: {exc}")
