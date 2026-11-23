"""Rubric Studio: generation, QA, versioning, approvals and criterion evaluation."""
import os
import sys
from pathlib import Path

import requests
import streamlit as st
import pandas as pd

# Streamlit Cloud may use dashboard/ as the import root. Add the repository
# root explicitly so the shared backend package is importable from this page.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.rubric_qa import validate_csv

st.set_page_config(page_title="Rubric Studio", page_icon="🧩", layout="wide")
st.title("Rubric Studio")
st.caption("Generate, validate, version, approve and evaluate against atomic Pass/Fail criteria.")

api_url = os.getenv("API_BASE_URL", "https://llm-prompt-benchmark.onrender.com").rstrip("/")
with st.sidebar:
    st.subheader("Provider settings")
    provider = st.selectbox("Provider", ["groq", "openrouter"])
    model = st.text_input("Model", value=os.getenv("MODEL_NAME", "openai/gpt-oss-20b"))
    review_key = st.text_input("Review API key", type="password", value=st.session_state.get("review_key", ""))
    st.session_state["review_key"] = review_key
    st.caption("The key is sent only to the configured API service and is not saved in the app.")

def api_headers():
    return {"X-Review-API-Key": st.session_state.get("review_key", "")}

def show_error(exc):
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.error(f"API error {exc.response.status_code}: {exc.response.text[:1200]}")
    else:
        st.error(f"Request failed: {exc}")

tab_generate, tab_library, tab_evaluate = st.tabs(["Generate & QA", "Rubric Library", "Evaluate response"])

with tab_generate:
    scenario = st.text_area("Scenario prompt", height=260, placeholder="Paste the full system/user scenario, constraints, edge cases and safety boundaries.")
    a, b = st.columns(2)
    with a:
        generate = st.button("Generate rubric", type="primary", use_container_width=True, disabled=not scenario.strip())
    with b:
        uploaded = st.file_uploader("Or upload rubric CSV", type=["csv"], key="rubric_upload")
    if generate:
        try:
            with st.spinner("Generating and validating rubric..."):
                res = requests.post(f"{api_url}/rubrics/generate",
                    json={"scenario": scenario, "provider": provider, "model": model}, timeout=180)
                res.raise_for_status()
                payload = res.json()
                st.session_state["rubric_csv"] = payload["csv"]
                st.session_state["rubric_qa"] = payload["qa"]
                st.session_state["rubric_provider"] = provider
                st.session_state["rubric_model"] = model
        except requests.RequestException as exc:
            show_error(exc)
    if uploaded is not None:
        st.session_state["rubric_csv"] = uploaded.getvalue().decode("utf-8-sig")
        st.session_state["rubric_qa"] = validate_csv(st.session_state["rubric_csv"])
        st.session_state["rubric_provider"] = "uploaded"
        st.session_state["rubric_model"] = "manual"
    csv_text = st.session_state.get("rubric_csv")
    qa = st.session_state.get("rubric_qa")
    if csv_text:
        status = qa.get("status", "NOT RUN")
        if status == "PASS": st.success("Rubric passed blocking and coverage QA.")
        elif status == "WARN": st.warning("Rubric passed blocking QA with coverage warnings.")
        else: st.error("Rubric failed QA; it cannot be saved.")
        counts = qa.get("counts", {})
        cols = st.columns(5)
        for col, (label, key) in zip(cols, [("Atomic","atomic_components"),("Overall","overall_components"),("Implicit","implicit_components"),("Explicit","explicit_components"),("Rows","total_rows")]):
            col.metric(label, counts.get(key, 0))
        for issue in qa.get("issues", []):
            msg = f"{issue['layer'].upper()} · {issue['severity'].upper()}: {issue['message']}"
            st.error(msg) if issue["severity"] == "error" else st.warning(msg)
        st.download_button("Download rubric CSV", csv_text, "rubric.csv", "text/csv")
        with st.expander("Preview rubric CSV"):
            st.dataframe(pd.DataFrame(qa.get("rows", [])), use_container_width=True, hide_index=True)
        st.subheader("Save as a version")
        c1, c2 = st.columns(2)
        rubric_name = c1.text_input("Rubric name", value="Scenario Rubric")
        version = c2.text_input("Version label", value="v1.0")
        objective = st.text_area("Evaluation objective", value=scenario[:4000] if scenario else "", max_chars=4000)
        created_by = st.text_input("Created by", value="Rubric author")
        if st.button("Save validated version", disabled=status == "FAIL"):
            try:
                with st.spinner("Saving rubric version to Neon..."):
                    res = requests.post(f"{api_url}/rubrics", headers=api_headers(),
                        json={"rubric_name":rubric_name,"version_label":version,"objective":objective,
                              "csv":csv_text,"generator_provider":st.session_state.get("rubric_provider"),
                              "generator_model":st.session_state.get("rubric_model"),"created_by":created_by}, timeout=45)
                    res.raise_for_status()
                    st.success(f"Saved draft version: {res.json()['rubric_id']}")
                    st.session_state["saved_rubric_id"] = res.json()["rubric_id"]
            except requests.RequestException as exc: show_error(exc)

with tab_library:
    st.subheader("Saved rubric versions")
    if st.button("Refresh library"):
        st.session_state["refresh_rubrics"] = True
    try:
        res = requests.get(f"{api_url}/rubrics", timeout=30)
        res.raise_for_status()
        rubrics = res.json().get("rubrics", [])
        if rubrics:
            st.dataframe(pd.DataFrame(rubrics), use_container_width=True, hide_index=True)
            ids = {f"{r['rubric_name']} · {r['version_label']} · {r['status']} · {r['rubric_id'][:8]}":r["rubric_id"] for r in rubrics}
            selected_label = st.selectbox("Select a rubric version", list(ids))
            selected_id = ids[selected_label]
            if rubrics[[r["rubric_id"] for r in rubrics].index(selected_id)]["status"] == "draft":
                approver = st.text_input("Approver identity", key="rubric_approver")
                if st.button("Approve selected version", disabled=not approver.strip()):
                    try:
                        res = requests.post(f"{api_url}/rubrics/{selected_id}/approve",
                            headers=api_headers(), json={"approver":approver}, timeout=30)
                        res.raise_for_status()
                        st.success("Rubric approved. This version is now eligible for evaluation.")
                        st.rerun()
                    except requests.RequestException as exc: show_error(exc)
            st.session_state["selected_rubric_id"] = selected_id
        else:
            st.info("No saved rubrics yet. Generate and save a validated version first.")
    except requests.RequestException as exc:
        show_error(exc)

with tab_evaluate:
    st.subheader("Evaluate a response against an approved rubric")
    try:
        res = requests.get(f"{api_url}/rubrics", timeout=30)
        res.raise_for_status()
        approved = [r for r in res.json().get("rubrics", []) if r["status"] == "approved"]
        if not approved:
            st.info("Approve a rubric version in the library before running an evaluation.")
        else:
            options = {f"{r['rubric_name']} · {r['version_label']}":r["rubric_id"] for r in approved}
            choice = st.selectbox("Approved rubric version", list(options))
            prompt = st.text_area("Original user prompt", height=130)
            response_text = st.text_area("Assistant response to evaluate", height=220)
            if st.button("Run criterion-level evaluation", type="primary", disabled=not prompt.strip() or not response_text.strip()):
                try:
                    with st.spinner("Judge is scoring every rubric criterion..."):
                        result = requests.post(f"{api_url}/rubrics/evaluate", headers=api_headers(),
                            json={"rubric_id":options[choice],"prompt":prompt,"response":response_text,
                                  "provider":provider,"model":model}, timeout=240)
                        result.raise_for_status()
                        payload = result.json()
                    st.success(f"Evaluation saved: {payload['rubric_evaluation_id']}")
                    summary = payload["summary"]
                    k = st.columns(5)
                    for col,(label,key) in zip(k,[("Pass rate","pass_rate"),("Passed","passed"),("Failed","failed"),("N/A","not_applicable"),("Total","total_criteria")]):
                        col.metric(label, summary.get(key, "—"))
                    st.warning(summary["evaluation_type"])
                    st.dataframe(pd.DataFrame(payload["scores"]), use_container_width=True, hide_index=True)
                except requests.RequestException as exc: show_error(exc)
    except requests.RequestException as exc:
        show_error(exc)
