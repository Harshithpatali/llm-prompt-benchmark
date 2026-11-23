"""Rubric Studio: generate, inspect, validate and export rubric CSV files."""
import os
import io
import requests
import streamlit as st

from backend.rubric_qa import validate_csv

st.set_page_config(page_title="Rubric Studio",page_icon="🧩",layout="wide")
st.title("Rubric Studio")
st.caption("Generate scenario-specific atomic Pass/Fail rubrics and validate them against the supplied Universal Framework and QA specification.")

api_url=os.getenv("API_BASE_URL","https://llm-prompt-benchmark.onrender.com").rstrip("/")
with st.sidebar:
    st.subheader("Generation settings")
    provider=st.selectbox("Provider",["groq","openrouter"])
    model=st.text_input("Model",value=os.getenv("MODEL_NAME","openai/gpt-oss-20b"))
    st.caption("Live generation uses the configured provider API key. Offline CSV validation does not require an API key.")

scenario=st.text_area("Scenario prompt",height=300,placeholder="Paste the complete system/user scenario prompt, including constraints, formatting, edge cases and safety boundaries.")
col1,col2=st.columns([1,1])
with col1:
    generate=st.button("Generate rubric",type="primary",use_container_width=True,disabled=not scenario.strip())
with col2:
    uploaded=st.file_uploader("Or upload an existing rubric CSV",type=["csv"])

if generate:
    with st.spinner("Generating rubric and running QA checks..."):
        try:
            response=requests.post(f"{api_url}/rubrics/generate",json={"scenario":scenario,"provider":provider,"model":model},timeout=180)
            response.raise_for_status()
            payload=response.json()
            st.session_state["rubric_csv"]=payload["csv"]
            st.session_state["rubric_qa"]=payload["qa"]
        except requests.RequestException as exc:
            st.error(f"Generation service unavailable: {exc}")

if uploaded is not None:
    try:
        st.session_state["rubric_csv"]=uploaded.getvalue().decode("utf-8-sig")
        st.session_state["rubric_qa"]=validate_csv(st.session_state["rubric_csv"])
    except UnicodeDecodeError:
        st.error("CSV must be UTF-8 encoded.")

csv_text=st.session_state.get("rubric_csv")
qa=st.session_state.get("rubric_qa")
if csv_text:
    st.divider()
    st.subheader("Quality assurance")
    status=(qa or {}).get("status","NOT RUN")
    if status=="PASS": st.success("Rubric passed structural and framework QA.")
    elif status=="WARN": st.warning("Rubric passed blocking checks but has coverage warnings.")
    else: st.error("Rubric has blocking QA issues.")
    counts=(qa or {}).get("counts",{})
    cols=st.columns(5)
    for col,(label,key) in zip(cols,[("Atomic","atomic_components"),("Overall","overall_components"),("Implicit","implicit_components"),("Explicit","explicit_components"),("Rows","total_rows")]):
        col.metric(label,counts.get(key,0))
    for issue in (qa or {}).get("issues",[]):
        msg=f"{issue['layer'].upper()} · {issue['severity'].upper()}: {issue['message']}"
        if issue["severity"]=="error": st.error(msg)
        else: st.warning(msg)
    st.subheader("Rubric CSV")
    st.download_button("Download rubric CSV",data=csv_text,file_name="generated_rubric.csv",mime="text/csv")
    st.code(csv_text[:12000],language="csv")
    with st.expander("Full validation report"):
        st.json(qa)
else:
    st.info("Paste a scenario prompt to generate a rubric, or upload an existing CSV to validate it.")
