"""LLM Quality Intelligence Platform — Streamlit multipage entrypoint."""
import os

import requests
import streamlit as st


st.set_page_config(
    page_title="LLM Quality Intelligence",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
:root { color-scheme: dark; }
.block-container { max-width: 1180px; padding-top: 1.5rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { border-right: 1px solid rgba(128,128,128,.18); }
h1 { letter-spacing: -.035em; }
h2, h3 { letter-spacing: -.02em; }
div[data-testid="stMetric"] { background: rgba(128,128,128,.08); border: 1px solid rgba(128,128,128,.16); padding: 14px 16px; border-radius: 14px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 16px; }
.stButton > button, .stDownloadButton > button { border-radius: 11px; min-height: 2.8rem; font-weight: 600; }
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"] { border-radius: 10px; }
div[data-testid="stAlert"] { border-radius: 12px; }
div[data-testid="stTabs"] button { font-weight: 600; }
.small-muted { color: rgba(180,180,180,.85); font-size: .9rem; }
@media (max-width: 700px) {
 .block-container { padding-left: 1rem; padding-right: 1rem; padding-top: .8rem; }
 h1 { font-size: 1.8rem !important; }
 h2 { font-size: 1.4rem !important; }
 div[data-testid="stMetric"] { padding: 10px; }
}
</style>
""", unsafe_allow_html=True)

API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://llm-prompt-benchmark.onrender.com"
).rstrip("/")


def render_home() -> None:
    st.title("LLM Quality Intelligence")
    st.caption("One workspace to benchmark prompts, inspect response quality, build evaluation rubrics and calibrate LLM judges.")

    try:
        response = requests.get(f"{API_BASE_URL}/database/health", timeout=8)
        if response.ok:
            health = response.json()
            st.success(f"API connected · {health.get('database', 'PostgreSQL')}")
        else:
            st.warning(f"API responded with HTTP {response.status_code}.")
    except requests.RequestException:
        st.warning("API is temporarily unavailable. Existing local benchmark reports may still be explored.")

    st.subheader("Your workspaces")
    st.write("Choose a task to get started.")
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

    st.subheader("Suggested workflow")
    st.markdown("**1. Build a rubric** → **2. Approve a version** → **3. Evaluate a response** → **4. Collect expert labels** → **5. Measure judge agreement**")
    with st.expander("About the data and metrics"):
        st.write("Starter seller-support scenarios are authored examples, not real customer records or validated gold labels. Human agreement and judge reliability should only be interpreted after collecting sufficient independent expert annotations. Lexical overlap diagnostics are not semantic factuality checks.")
    st.caption("FastAPI · Streamlit · Neon PostgreSQL")

