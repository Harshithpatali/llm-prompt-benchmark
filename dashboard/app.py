"""LLM Quality Intelligence Platform — Streamlit multipage entrypoint."""
import os
import sys
from pathlib import Path

import requests
import streamlit as st


st.set_page_config(
    page_title="LLM Quality Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)


DASHBOARD_DIR = Path(__file__).resolve().parent
if str(DASHBOARD_DIR) not in sys.path:
    sys.path.insert(0, str(DASHBOARD_DIR))
from ui import apply_theme, page_header

apply_theme()

API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://llm-prompt-benchmark.onrender.com"
).rstrip("/")


def render_home() -> None:
    page_header("Evaluation operations", "LLM Quality Intelligence", "A unified workspace to build evaluation rubrics, review model responses, benchmark prompt strategies and measure judge reliability.")
    st.markdown("**Start with a workflow** · Your evaluation data and experiment history stay in the connected workspace.")

    try:
        response = requests.get(f"{API_BASE_URL}/database/health", timeout=8)
        if response.ok:
            health = response.json()
            st.success(f"API connected · {health.get('database', 'PostgreSQL')}")
        else:
            st.warning(f"API responded with HTTP {response.status_code}.")
    except requests.RequestException:
        st.warning("API is temporarily unavailable. Existing local benchmark reports may still be explored.")

    st.subheader("Workspaces")
    st.caption("Choose a task to get started. Each workspace is focused on one stage of evaluation.")
    cards = [
        ("🧩", "Rubric Studio", "Create a rubric from a scenario, run quality checks, save versions and evaluate responses.", rubric_page, "Start building"),
        ("🧪", "Human Quality Review", "Review candidate answers, record evidence and submit structured human assessments.", review_page, "Review answers"),
        ("⚖️", "Judge Calibration", "Compare expert labels with LLM judge decisions and identify unreliable criteria.", calibration_page, "Calibrate judge"),
        ("📊", "Prompt Benchmark", "Compare prompt strategies, inspect extraction metrics and explore model outputs.", benchmark_page, "Explore benchmarks"),
    ]
    for row in range(2):
        cols = st.columns(2, gap="large")
        for col, item in zip(cols, cards[row*2:(row+1)*2]):
            icon, title, desc, page, action = item
            with col:
                with st.container(border=True):
                    st.markdown(f"### {icon} {title}")
                    st.write(desc)
                    st.page_link(page, label=action, use_container_width=True)

    st.subheader("Recommended workflow")
    st.markdown("**1. Build a rubric** → **2. Approve a version** → **3. Evaluate a response** → **4. Collect expert labels** → **5. Measure judge agreement**")
    with st.expander("About the data and metrics"):
        st.write("Starter seller-support scenarios are authored examples, not real customer records or validated gold labels. Human agreement and judge reliability should only be interpreted after collecting sufficient independent expert annotations. Lexical overlap diagnostics are not semantic factuality checks.")
    st.caption("FastAPI · Streamlit · Neon PostgreSQL")

