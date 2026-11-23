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
API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://llm-prompt-benchmark.onrender.com"
).rstrip("/")


def render_home() -> None:
    st.title("LLM Quality Intelligence")
    st.caption(
        "A unified workspace for prompt experiments, response evaluation, "
        "human review, and model reliability."
    )

    try:
        response = requests.get(f"{API_BASE_URL}/database/health", timeout=8)
        if response.ok:
            health = response.json()
            st.success(
                f"Evaluation API connected · {health.get('database', 'PostgreSQL')}"
            )
        else:
            st.warning(
                f"Evaluation API responded with HTTP {response.status_code}."
            )
    except requests.RequestException:
        st.warning(
            "Evaluation API is temporarily unavailable. "
            "Local benchmark reports remain accessible."
        )

    st.divider()
    st.subheader("Evaluation workspaces")
    st.write(
        "Choose a workspace. Existing prompt benchmark datasets "
        "and experiment results are preserved."
    )

    left, right, third = st.columns(3, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### 🧪 Human Quality Review")
            st.write(
                "Inspect candidate answers against their context, record "
                "evidence-backed assessments, and review submitted annotations."
            )
            st.page_link(
                review_page,
                label="Open human review",
                icon="🧪",
                use_container_width=True,
            )
    with right:
        with st.container(border=True):
            st.markdown("### 📊 Prompt Benchmark")
            st.write(
                "Compare prompt strategies, inspect extraction metrics, "
                "explore raw model outputs, and run live attribute extraction."
            )
            st.page_link(
                benchmark_page,
                label="Open prompt benchmark",
                icon="📊",
                use_container_width=True,
            )
    with third:
        with st.container(border=True):
            st.markdown("### 🧩 Rubric Studio")
            st.write(
                "Generate atomic Pass/Fail rubrics from scenario prompts "
                "and run framework QA before export."
            )
            st.page_link(
                rubric_page,
                label="Open Rubric Studio",
                icon="🧩",
                use_container_width=True,
            )

    with st.container(border=True):
        st.markdown("### ⚖️ Judge Calibration")
        st.write(
            "Collect expert criterion labels, adjudicate disagreements, "
            "and measure LLM judge reliability."
        )
        st.page_link(
            calibration_page,
            label="Open judge calibration",
            icon="⚖️",
            use_container_width=True,
        )

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
        st.write(
            "The repository includes an e-commerce extraction dataset, "
            "authored general response cases, and authored seller-support "
            "review scenarios. Synthetic starter scenarios are not real "
            "customer records or validated gold labels. Lexical overlap "
            "diagnostics are not semantic factuality checks."
        )

    st.caption("LLM Quality Intelligence · FastAPI + Streamlit + PostgreSQL")


# Register every page with st.navigation. In navigation mode, st.page_link
# must receive one of these Page objects rather than a path string.
home_page = st.Page(render_home, title="Home", icon="🧭", default=True)
review_page = st.Page(
    "pages/2_Quality_Review.py", title="Human Quality Review", icon="🧪"
)
benchmark_page = st.Page(
    "pages/1_Prompt_Benchmark.py", title="Prompt Benchmark", icon="📊"
)
rubric_page = st.Page("pages/3_Rubric_Studio.py", title="Rubric Studio", icon="🧩")
calibration_page = st.Page(
    "pages/4_Judge_Calibration.py", title="Judge Calibration", icon="⚖️"
)

navigation = st.navigation(
    [
        home_page,
        review_page,
        benchmark_page,
        rubric_page,
        calibration_page,
    ],
    position="hidden",
)
navigation.run()
