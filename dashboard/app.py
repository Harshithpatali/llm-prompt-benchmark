import streamlit as st
import pandas as pd
import json
import plotly.express as px
from pathlib import Path
import requests

# ==============================
# Configuration
# ==============================

BACKEND_URL = "https://llm-prompt-benchmark.onrender.com"

st.set_page_config(page_title="LLM Prompt Benchmark", layout="wide")
st.title("LLM Prompt Evaluation Dashboard")

# ---------- Sidebar ----------
st.sidebar.header("Settings")

results_dir = Path("results")
result_files = sorted(results_dir.glob("*.json"), reverse=True) if results_dir.exists() else []

selected_file = st.sidebar.selectbox(
    "Select Experiment Result",
    options=[f.name for f in result_files] if result_files else ["No results found"]
)

# ---------- Load Data ----------
if result_files and selected_file != "No results found":

    with open(results_dir / selected_file, encoding="utf-8") as f:
        data = json.load(f)

    # New benchmark artifacts are metadata/results objects; retain legacy list support.
    if isinstance(data, dict):
        metadata = data.get('metadata', {})
        if metadata:
            st.caption(f"Model: {metadata.get('model', 'unknown')} | Provider: {metadata.get('provider', 'unknown')} | Test rows: {len(metadata.get('test_ids', []))}")
        comparisons = data.get('paired_comparisons_vs_zero_shot', {})
        if comparisons:
            with st.expander('Paired comparisons vs zero-shot'):
                st.json(comparisons)
        data = data.get('results', [])

    st.subheader("Strategy Comparison")

    metrics_data = []

    for item in data:
        row = {"strategy": item["strategy"]}
        metric_values = item.get("metrics", {})
        row.update({k: v for k, v in metric_values.items() if k != "per_attribute" and isinstance(v, (int, float))})
        for attribute, values in metric_values.get("per_attribute", {}).items():
            row[attribute] = values.get("exact_match", 0.0)
        metrics_data.append(row)

    metrics_df = pd.DataFrame(metrics_data)

    # Convert numeric columns
    for col in metrics_df.columns:
        if col != "strategy":
            metrics_df[col] = pd.to_numeric(metrics_df[col], errors="coerce")

    numeric_cols = [c for c in metrics_df.columns if c != "strategy"]

    st.dataframe(
        metrics_df.style.format(
            "{:.3f}",
            subset=numeric_cols
        ),
        use_container_width=True
    )

    # ---------- Overall Performance ----------
    if "overall" in metrics_df.columns:

        fig = px.bar(
            metrics_df,
            x="strategy",
            y="overall",
            color="strategy",
            title="Overall Exact Match by Strategy",
            text="overall",
        )

        fig.update_traces(
            texttemplate="%{text:.3f}",
            textposition="outside"
        )

        fig.update_layout(yaxis_range=[0, 1])

        st.plotly_chart(fig, use_container_width=True)

    # ---------- Attribute Performance ----------
    st.subheader("Attribute-level Performance")

    attr_cols = [
        c for c in metrics_df.columns
        if c not in ["strategy", "overall"]
    ]

    if attr_cols:

        melted = metrics_df.melt(
            id_vars="strategy",
            value_vars=attr_cols,
            var_name="attribute",
            value_name="score"
        )

        fig2 = px.bar(
            melted,
            x="attribute",
            y="score",
            color="strategy",
            barmode="group",
            title="Attribute-wise Exact Match"
        )

        fig2.update_layout(yaxis_range=[0, 1])

        st.plotly_chart(fig2, use_container_width=True)

    # ---------- Raw Outputs ----------
    st.subheader("Raw Outputs Explorer")

    strategy_filter = st.selectbox(
        "Filter by strategy",
        options=[d["strategy"] for d in data]
    )

    selected = next(
        d for d in data
        if d["strategy"] == strategy_filter
    )

    raw_outputs = selected.get("raw_outputs") or selected.get("rows", [])

    if raw_outputs:
        for i, item in enumerate(raw_outputs[:20]):
            with st.expander(f"Sample {i+1} | {item.get('item_id', 'Unknown')}"):
                st.write("### Prediction")
                st.json(item.get("prediction", item.get("pred", {})))
                st.write("### Ground truth")
                st.json(item.get("gold", {}))
                st.caption(f"Latency: {item.get('latency_ms', 'n/a')} ms")
                if item.get("error"): st.warning(item["error"])
                st.write("### Raw LLM Output")
                st.code(item.get("raw", ""), language="json")
    else:
        st.info("No raw outputs available.")

else:
    st.warning("No experiment results found. Run the experiment first.")

# ==========================================================
# Live Attribute Extraction
# ==========================================================

st.divider()
st.subheader("Live Attribute Extraction")

col1, col2 = st.columns(2)

with col1:
    item_name = st.text_input("Product Title")

with col2:
    strategy = st.selectbox(
        "Strategy",
        [
            "structured",
            "zero_shot",
            "cot",
            "role_based",
        ],
    )

bullet_points = st.text_area(
    "Bullet Points (separated by | or new lines)"
)

if st.button("Extract Attributes"):

    if item_name and bullet_points:

        try:

            response = requests.post(
                f"{BACKEND_URL}/extract",
                json={
                    "item_name": item_name,
                    "bullet_points": bullet_points,
                    "strategy": strategy,
                    "provider": "groq",
                },
                timeout=60,
            )

            response.raise_for_status()

            result = response.json()

            st.success("Extraction successful!")

            st.subheader("Extracted Attributes")
            st.json(result.get("prediction", {}))

            # Show judge evaluation if available
            judge = result.get("judge")
            if judge:
                st.write("### 🤖 LLM Judge")

                st.metric("Judge Score", f"{judge['score']}/5")

                st.write("**Reason**")
                st.write(judge["reason"])

                st.write("**Correct Attributes**")
                st.write(judge["correct_attributes"])

                st.write("**Incorrect Attributes**")
                st.write(judge["incorrect_attributes"])

            with st.expander("Raw LLM Output"):
                st.code(
                    result.get("raw_output", ""),
                    language="json"
                )

        except requests.exceptions.RequestException as e:

            st.error(
                f"""
Could not connect to the FastAPI backend.

Backend URL:
{BACKEND_URL}

Please ensure:
• The Render service is running.
• The /extract endpoint exists.
• The backend deployment completed successfully.

Error:
{e}
"""
            )

    else:
        st.warning("Please enter both the product title and bullet points.")