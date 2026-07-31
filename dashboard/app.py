import streamlit as st
import pandas as pd
import json
import plotly.express as px
from pathlib import Path
import requests

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

    # ---------- Strategy Comparison ----------
    st.subheader("Strategy Comparison")

    metrics_data = []
    for item in data:
        row = {"strategy": item["strategy"]}
        row.update(item.get("metrics", {}))
        metrics_data.append(row)

    metrics_df = pd.DataFrame(metrics_data)

    # Convert all metric columns to numeric
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

    raw_outputs = selected.get("raw_outputs", [])

    if raw_outputs:
        for i, item in enumerate(raw_outputs[:10]):
            with st.expander(
                f"Sample {i+1} | {item.get('item_id','Unknown')}"
            ):
                st.write("### Prediction")
                st.json(item.get("pred", {}))

                st.write("### Raw LLM Output")
                st.code(
                    item.get("raw", ""),
                    language="json"
                )
    else:
        st.info("No raw outputs available.")

else:
    st.warning("No experiment results found. Run the experiment first.")

# ======================================================================
# Live Extraction
# ======================================================================

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
            "few_shot"
        ]
    )

bullet_points = st.text_area(
    "Bullet Points (separated by | or new lines)"
)

if st.button("Extract Attributes"):

    if item_name and bullet_points:

        try:

            response = requests.post(
                "http://localhost:8000/extract",
                json={
                    "item_name": item_name,
                    "bullet_points": bullet_points,
                    "strategy": strategy,
                },
                timeout=30,
            )

            if response.status_code == 200:

                result = response.json()

                st.success("Extraction successful")

                st.subheader("Extracted Attributes")
                st.json(result.get("prediction", {}))

                with st.expander("Raw LLM Output"):
                    st.code(
                        result.get("raw_output", ""),
                        language="json"
                    )

            else:
                st.error(f"Backend Error:\n{response.text}")

        except Exception as e:
            st.error(
                "Could not connect to FastAPI backend.\n\n"
                "Make sure it is running on http://localhost:8000\n\n"
                f"Error:\n{e}"
            )

    else:
        st.warning("Please enter both the product title and bullet points.")