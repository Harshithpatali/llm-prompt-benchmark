"""LLM Quality Intelligence Platform — Streamlit landing page."""
import os
import requests
import streamlit as st

st.set_page_config(page_title="LLM Quality Intelligence", page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
API_BASE_URL = os.getenv("API_BASE_URL", "https://llm-prompt-benchmark.onrender.com").rstrip("/")

st.title("LLM Quality Intelligence")
st.caption("A unified workspace for prompt experiments, response evaluation, human review, and model reliability.")

try:
    response = requests.get(f"{API_BASE_URL}/database/health", timeout=8)
    if response.ok:
        health = response.json()
        st.success(f"Evaluation API connected · {health.get('database', 'PostgreSQL')}")
    else:
        st.warning(f"Evaluation API responded with HTTP {response.status_code}.")
except requests.RequestException:
    st.warning("Evaluation API is temporarily unavailable. Local benchmark reports remain accessible.")

st.divider()
st.subheader("Evaluation workspaces")
st.write("Choose a workspace. Existing prompt benchmark datasets and experiment results are preserved.")

left, right = st.columns(2, gap="large")
with left:
    with st.container(border=True):
        st.markdown("### 🧪 Human Quality Review")
        st.write("Inspect candidate answers against their context, record evidence-backed assessments, and review submitted annotations.")
        st.page_link("pages/2_Quality_Review.py", label="Open human review", icon="🧪", use_container_width=True)
with right:
    with st.container(border=True):
        st.markdown("### 📊 Prompt Benchmark")
        st.write("Compare prompt strategies, inspect extraction metrics, explore raw model outputs, and run live attribute extraction.")
        st.page_link("pages/1_Prompt_Benchmark.py", label="Open prompt benchmark", icon="📊", use_container_width=True)

st.divider()
st.subheader("Platform capabilities")
cols = st.columns(4)
items = [
    ("Prompt experiments", "Strategy comparison and extraction metrics"),
    ("Response quality", "Task-level evaluation and diagnostics"),
    ("Human review", "Evidence, confidence, and annotations"),
    ("Reliability", "Latency, usage, audit trail, and calibration"),
]
for col, (heading, detail) in zip(cols, items):
    with col:
        st.markdown(f"**{heading}**")
        st.caption(detail)

with st.expander("Data and evaluation notes"):
    st.write("The repository includes an e-commerce extraction dataset, authored general response cases, and authored seller-support review scenarios. Synthetic starter scenarios are not real customer records or validated gold labels. Lexical overlap diagnostics are not semantic factuality checks.")

st.caption("LLM Quality Intelligence · FastAPI + Streamlit + PostgreSQL")
