"""Rubric Studio — guided rubric creation, approval and evaluation."""
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.rubric_qa import validate_csv

st.set_page_config(page_title="Rubric Studio", page_icon="🧩", layout="wide")
import sys
from pathlib import Path
DASHBOARD_DIR = Path(__file__).resolve().parents[1]
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from ui import apply_theme, page_header
apply_theme()
API_URL = os.getenv("API_BASE_URL", "https://llm-prompt-benchmark.onrender.com").rstrip("/")
DEFAULT_MODEL = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")


def secret(name, fallback=""):
    try:
        return str(st.secrets.get(name, os.getenv(name, fallback))).strip()
    except Exception:
        return os.getenv(name, fallback).strip()


def api_request(method, path, *, authenticated=False, **kwargs):
    headers = kwargs.pop("headers", {})
    if authenticated:
        key = secret("REVIEW_API_KEY") or st.session_state.get("rubric_review_key", "")
        if key:
            headers["X-Review-API-Key"] = key
    response = requests.request(method, f"{API_URL}{path}", headers=headers, timeout=kwargs.pop("timeout", 90), **kwargs)
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"HTTP {response.status_code}: {detail}")
    return response.json() if response.content else {}


def show_request_error(exc):
    st.error(str(exc))
    if "401" in str(exc) or "403" in str(exc):
        st.info("This action needs the review API key. Add REVIEW_API_KEY to Streamlit Cloud Secrets or enter it in the sidebar.")
    elif "413" in str(exc) or "TPM" in str(exc):
        st.info("The provider token budget was exceeded. Shorten the scenario or try again later.")
    elif "502" in str(exc):
        st.info("The API reached the model provider but generation failed. Check the Render API logs for the upstream provider response.")


page_header("Evaluation design", "Rubric Studio", "Generate traceable criteria from a scenario, validate coverage, manage approved versions and evaluate candidate responses.")

with st.sidebar:
    st.subheader("Reviewer access")
    st.caption("This key protects write actions. It is not needed to generate a rubric.")
    if not secret("REVIEW_API_KEY"):
        entered = st.text_input(
            "Review API key",
            type="password",
            value=st.session_state.get("rubric_review_key", ""),
            help="Ask the platform administrator for access. Never use your model-provider API key here.",
            key="rubric_review_api_key_input",
        )
        if entered:
            st.session_state["rubric_review_key"] = entered

try:
    health = api_request("GET", "/database/health", timeout=8)
    st.success(f"API and database connected · {health.get('database', 'PostgreSQL')}")
except Exception:
    st.warning("Could not confirm the API/database connection. Generation may still work, but saving and evaluation require the backend.")

tab_build, tab_library, tab_evaluate = st.tabs(["① Build a rubric", "② Rubric library", "③ Evaluate a response"])

with tab_build:
    st.subheader("Choose your generation model")
    st.caption("Select the provider and exact model here before generating. The API key stays securely on Render.")
    model_col1, model_col2 = st.columns(2)
    with model_col1:
        provider = st.selectbox(
            "Model provider",
            ["gemini", "groq", "openrouter"],
            format_func=lambda value: {"gemini": "Google Gemini", "groq": "Groq", "openrouter": "OpenRouter"}[value],
            key="rubric_provider_choice",
        )
    model_options = {
        "gemini": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "Custom model…"],
        "groq": ["openai/gpt-oss-20b", "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "Custom model…"],
        "openrouter": ["openai/gpt-oss-20b", "google/gemini-2.5-flash", "anthropic/claude-sonnet-4", "Custom model…"],
    }
    with model_col2:
        selected_model = st.selectbox(
            "Model",
            model_options[provider],
            index=0,
            key=f"rubric_model_choice_{provider}",
            help="Choose a model supported by the selected provider.",
        )
    if selected_model == "Custom model…":
        model = st.text_input(
            "Custom model ID",
            value=(
                os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
                if provider == "gemini" else DEFAULT_MODEL
            ),
            key=f"rubric_custom_model_{provider}",
            help="Enter the exact model ID accepted by your provider.",
        )
    else:
        model = selected_model
    if provider == "gemini":
        st.info("Google Gemini uses GEMINI_API_KEY configured on Render. Do not enter the key here.")
    elif provider == "groq":
        st.info("Groq uses GROQ_API_KEY configured on Render.")
    else:
        st.info("OpenRouter uses OPENROUTER_API_KEY configured on Render.")

    st.divider()
    st.subheader("Describe what the assistant must do")
    st.write("Paste the system prompt, task instructions, constraints, edge cases and expected output requirements. The generator turns them into atomic criteria.")
    with st.form("rubric_generation_form"):
        scenario = st.text_area(
            "Scenario prompt",
            value=st.session_state.get("rubric_scenario", ""),
            height=230,
            max_chars=30000,
            placeholder="Example: You are a customer-support assistant. Answer only from the supplied policy...\n\nRequirements:\n- ...\n- ...",
            help="Use the complete scenario. Very long prompts may exceed the model provider's token budget.",
            key="rubric_scenario_input",
        )
        left, right = st.columns(2)
        with left:
            st.caption("Include")
            st.markdown("- Explicit instructions and constraints\n- Safety and refusal boundaries\n- Context and source-use rules")
        with right:
            st.caption("Also include")
            st.markdown("- Edge cases and conflict handling\n- Required output structure\n- Actions and verification, if relevant")
        generate = st.form_submit_button("Generate rubric", type="primary", use_container_width=True)
    if generate:
        if len(scenario.strip()) < 10:
            st.error("Enter a scenario of at least 10 characters before generating a rubric.")
            st.stop()
        st.session_state["rubric_scenario"] = scenario
        st.session_state.pop("rubric_csv", None)
        try:
            with st.spinner("Generating atomic criteria and running rubric QA…"):
                result = api_request("POST", "/rubrics/generate", json={"scenario": scenario, "provider": provider, "model": model or None}, timeout=240)
            st.session_state["rubric_csv"] = result["csv"]
            st.session_state["rubric_qa"] = result["qa"]
            st.session_state["rubric_provider"] = result.get("provider", provider)
            st.session_state["rubric_model"] = result.get("model", model)
            st.success("Rubric generated. Review the QA report before saving.")
        except Exception as exc:
            show_request_error(exc)

    csv_text = st.session_state.get("rubric_csv")
    qa = st.session_state.get("rubric_qa")
    if csv_text and qa:
        st.divider()
        st.subheader("Quality check")
        status = qa.get("status", "UNKNOWN")
        counts = qa.get("counts", {})
        if status == "PASS":
            st.success("QA passed. The rubric is ready for a final review.")
        elif status == "WARN":
            st.warning("Blocking checks passed, but review the coverage warnings before approval.")
        else:
            st.error("QA failed. Fix the reported issues before saving this rubric.")
        metric_cols = st.columns(4)
        metrics = [
            ("Atomic criteria", counts.get("atomic_components", 0)),
            ("Overall criteria", counts.get("overall_components", 0)),
            ("Explicit / implicit", f"{counts.get('explicit_components', 0)} / {counts.get('implicit_components', 0)}"),
            ("Total rows", counts.get("total_rows", 0)),
        ]
        for col, (label, value) in zip(metric_cols, metrics):
            col.metric(label, value)
        errors = [x for x in qa.get("issues", []) if x.get("severity") == "error"]
        warnings = [x for x in qa.get("issues", []) if x.get("severity") != "error"]
        if errors or warnings:
            with st.expander(f"Review QA findings · {len(errors)} errors · {len(warnings)} warnings", expanded=bool(errors)):
                for issue in errors:
                    st.error(f"Row {issue.get('row') or '—'} · {issue.get('layer', 'QA')}: {issue.get('message')}")
                for issue in warnings:
                    st.warning(f"Row {issue.get('row') or '—'} · {issue.get('layer', 'QA')}: {issue.get('message')}")
        preview = pd.DataFrame(qa.get("rows", []))
        expected_columns = [
            "Rubric Component Number", "Rubric Parent Category",
            "Rubric Sub-Category", "Rubric Component Name",
            "Rubric Evaluation Question", "Implicit vs. Explicit in the Prompt",
            "Direct Quotation from the Prompt (N/A if Implicit)",
            "Implicit Logic (N/A if Explicit)", "Pass/Fail Criteria",
        ]
        looks_like_rubric = (
            not preview.empty
            and list(preview.columns) == expected_columns
            and "Rubric Component Number" in preview.columns
        )
        if looks_like_rubric and status in {"PASS", "WARN"}:
            st.subheader("Rubric preview")
            st.caption("Check criterion wording, traceability and pass/fail conditions before saving.")
            st.dataframe(preview, use_container_width=True, hide_index=True)
            st.download_button("Download rubric CSV", data=csv_text, file_name="evaluation_rubric.csv", mime="text/csv", use_container_width=True)
            with st.expander("Advanced · View validated CSV source"):
                st.code(csv_text, language="csv")
        else:
            st.error("The model response did not produce a valid rubric table. It has been withheld from the preview and download. Try again or change the configured model.")
            with st.expander("Technical QA details"):
                st.json(qa)
        st.divider()
        st.subheader("Save this rubric version")
        with st.form("save_rubric_form"):
            a, b = st.columns(2)
            with a:
                rubric_name = st.text_input("Rubric name", value="Scenario Evaluation Rubric")
                version = st.text_input("Version", value="v1.0")
            with b:
                created_by = st.text_input("Author ID", value="rubric-author", help="Use a role or pseudonymous ID.")
                objective = st.text_input("Evaluation objective", value=(st.session_state.get("rubric_scenario", "")[:500] or "Evaluate assistant response quality"))
            save = st.form_submit_button("Save validated draft", type="primary", use_container_width=True, disabled=status == "FAIL")
        if save:
            try:
                with st.spinner("Saving version to the rubric library…"):
                    saved = api_request("POST", "/rubrics", authenticated=True, json={
                        "rubric_name": rubric_name, "version_label": version, "objective": objective,
                        "csv": csv_text, "generator_provider": st.session_state.get("rubric_provider"),
                        "generator_model": st.session_state.get("rubric_model"), "created_by": created_by,
                    }, timeout=60)
                st.session_state["saved_rubric_id"] = saved["rubric_id"]
                st.success(f"Draft saved · ID: {saved['rubric_id']}")
                st.info("Next: open the Rubric library, inspect the version and approve it before evaluation.")
            except Exception as exc:
                show_request_error(exc)

with tab_library:
    st.subheader("Saved rubric versions")
    st.write("Drafts must be approved before they can be used by the evaluator.")
    if st.button("Refresh rubric library", use_container_width=False):
        st.rerun()
    try:
        library = api_request("GET", "/rubrics", params={"limit": 100, "offset": 0}, timeout=45).get("rubrics", [])
        if not library:
            st.info("Your library is empty. Generate and save a validated rubric first.")
        else:
            table = pd.DataFrame(library)
            preferred = [c for c in ["rubric_name", "version_label", "status", "created_at", "rubric_id"] if c in table.columns]
            st.dataframe(table[preferred] if preferred else table, use_container_width=True, hide_index=True)
            choices = {f"{r.get('rubric_name','Rubric')} · {r.get('version_label','')} · {r.get('status','')} · {r.get('rubric_id','')[:8]}": r for r in library}
            selected_label = st.selectbox("Select a version", list(choices))
            selected = choices[selected_label]
            st.markdown(f"**Status:** {selected.get('status', 'unknown')}  ")
            st.caption(f"Rubric ID: {selected.get('rubric_id')}")
            if selected.get("status") == "draft":
                approver = st.text_input("Approver ID", placeholder="e.g. reviewer-lead")
                if st.button("Approve this version", type="primary", disabled=not approver.strip(), use_container_width=True):
                    try:
                        api_request("POST", f"/rubrics/{selected['rubric_id']}/approve", authenticated=True, json={"approver": approver.strip()}, timeout=45)
                        st.success("Rubric approved. It is now available for evaluation.")
                        st.rerun()
                    except Exception as exc:
                        show_request_error(exc)
            else:
                st.success("This version is approved and eligible for evaluation.")
    except Exception as exc:
        show_request_error(exc)

with tab_evaluate:
    st.subheader("Evaluate an assistant response")
    st.write("Choose an approved rubric, provide the original prompt and candidate answer, then run criterion-level scoring.")
    try:
        library = api_request("GET", "/rubrics", params={"limit": 100, "offset": 0}, timeout=45).get("rubrics", [])
        approved = [r for r in library if r.get("status") == "approved"]
        if not approved:
            st.info("No approved rubrics are available yet. Save and approve a version in the Rubric library.")
        else:
            options = {f"{r['rubric_name']} · {r['version_label']}": r["rubric_id"] for r in approved}
            with st.form("evaluate_response_form"):
                choice = st.selectbox("Approved rubric", list(options))
                prompt_text = st.text_area("Original user prompt", height=130, placeholder="Paste the exact prompt the assistant received.")
                response_text = st.text_area("Assistant response", height=220, placeholder="Paste the response you want the judge to evaluate.")
                run_eval = st.form_submit_button("Evaluate response", type="primary", use_container_width=True, disabled=not prompt_text.strip() or not response_text.strip())
            if run_eval:
                with st.spinner("Scoring each rubric criterion…"):
                    result = api_request("POST", "/rubrics/evaluate", authenticated=True, json={
                        "rubric_id": options[choice], "prompt": prompt_text, "response": response_text,
                        "provider": provider, "model": model or None,
                    }, timeout=300)
                st.session_state["latest_rubric_evaluation"] = result
                st.success("Evaluation completed and saved.")
            result = st.session_state.get("latest_rubric_evaluation")
            if result:
                st.divider()
                st.subheader("Evaluation results")
                st.code(result.get("rubric_evaluation_id", ""), language=None)
                summary = result.get("summary", {})
                cols = st.columns(4)
                for col, (label, key) in zip(cols, [("Pass rate", "pass_rate"), ("Passed", "passed"), ("Failed", "failed"), ("Not applicable", "not_applicable")]):
                    value = summary.get(key, "—")
                    col.metric(label, f"{value:.1%}" if key == "pass_rate" and isinstance(value, (float, int)) else value)
                st.caption(summary.get("evaluation_type", "LLM judge evaluation"))
                scores = pd.DataFrame(result.get("scores", []))
                if not scores.empty:
                    st.dataframe(scores, use_container_width=True, hide_index=True)
                st.info("Copy the evaluation ID above into Judge Calibration to collect independent expert labels and compare them with the judge.")
                st.button("Copy evaluation ID", on_click=lambda: st.session_state.update({"copied_eval_id": result.get("rubric_evaluation_id", "")}))
                if st.session_state.get("copied_eval_id"):
                    st.code(st.session_state["copied_eval_id"])
    except Exception as exc:
        show_request_error(exc)
