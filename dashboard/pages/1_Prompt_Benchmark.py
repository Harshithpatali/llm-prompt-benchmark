"""Prompt Benchmark — experiment comparison and live extraction."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Prompt Benchmark", page_icon="📊", layout="wide")
API_URL = "https://llm-prompt-benchmark.onrender.com"

st.title("📊 Prompt Benchmark")
st.caption("Compare structured extraction strategies, inspect experiment artifacts and run a live product-attribute extraction.")

results_dir = Path("results")
result_files = sorted(results_dir.glob("*.json"), reverse=True) if results_dir.exists() else []

tab_results, tab_live = st.tabs(["① Experiment results", "② Live extraction"])

with tab_results:
    st.subheader("Select an experiment")
    if not result_files:
        st.info("No experiment result files were found in the repository's results/ directory. Run a benchmark and add its JSON artifact to explore results here.")
    else:
        selected_file = st.selectbox("Experiment result", result_files, format_func=lambda p: p.name)
        try:
            with selected_file.open(encoding="utf-8") as handle:
                artifact = json.load(handle)
            metadata = artifact.get("metadata", {}) if isinstance(artifact, dict) else {}
            rows = artifact.get("results", []) if isinstance(artifact, dict) else artifact
            if metadata:
                st.caption(
                    f"Provider: {metadata.get('provider', '—')} · Model: {metadata.get('model', '—')} · "
                    f"Test examples: {len(metadata.get('test_ids', []))}"
                )
            if not rows:
                st.warning("The selected artifact does not contain strategy results.")
            else:
                metrics_data = []
                for item in rows:
                    metrics = item.get("metrics", {})
                    row = {"Strategy": item.get("strategy", "unknown")}
                    row.update({k: v for k, v in metrics.items() if k != "per_attribute" and isinstance(v, (int, float))})
                    for attribute, values in metrics.get("per_attribute", {}).items():
                        row[attribute] = values.get("exact_match", 0.0)
                    metrics_data.append(row)
                metrics_df = pd.DataFrame(metrics_data)
                for column in metrics_df.columns:
                    if column != "Strategy":
                        metrics_df[column] = pd.to_numeric(metrics_df[column], errors="coerce")
                st.subheader("Strategy comparison")
                metric_cols = [c for c in metrics_df.columns if c != "Strategy"]
                if metric_cols:
                    first_metric = "overall" if "overall" in metric_cols else metric_cols[0]
                    best = metrics_df.sort_values(first_metric, ascending=False).iloc[0]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Strategies compared", len(metrics_df))
                    c2.metric(f"Best {first_metric}", best["Strategy"])
                    c3.metric("Score", f"{best[first_metric]:.3f}" if pd.notna(best[first_metric]) else "—")
                st.dataframe(metrics_df, use_container_width=True, hide_index=True)
                if "overall" in metrics_df.columns:
                    fig = px.bar(metrics_df, x="Strategy", y="overall", color="Strategy", text="overall", title="Overall exact match by strategy")
                    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
                    fig.update_layout(yaxis_range=[0, 1], showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
                attribute_cols = [c for c in metric_cols if c != "overall"]
                if attribute_cols:
                    melted = metrics_df.melt(id_vars="Strategy", value_vars=attribute_cols, var_name="Attribute", value_name="Exact match")
                    fig2 = px.bar(melted, x="Attribute", y="Exact match", color="Strategy", barmode="group", title="Attribute-level exact match")
                    fig2.update_layout(yaxis_range=[0, 1])
                    st.plotly_chart(fig2, use_container_width=True)
                comparisons = artifact.get("paired_comparisons_vs_zero_shot", {}) if isinstance(artifact, dict) else {}
                if comparisons:
                    with st.expander("Paired comparisons against zero-shot"):
                        st.json(comparisons)
                st.subheader("Inspect individual outputs")
                strategy_names = [item.get("strategy", "unknown") for item in rows]
                selected_strategy = st.selectbox("Strategy", strategy_names)
                selected = next(item for item in rows if item.get("strategy", "unknown") == selected_strategy)
                raw_outputs = selected.get("raw_outputs") or selected.get("rows", [])
                if raw_outputs:
                    for index, item in enumerate(raw_outputs[:50]):
                        with st.expander(f"Example {index + 1} · {item.get('item_id', 'unknown item')}"):
                            left, right = st.columns(2)
                            with left:
                                st.markdown("**Prediction**")
                                st.json(item.get("prediction", item.get("pred", {})))
                            with right:
                                st.markdown("**Reference**")
                                st.json(item.get("gold", {}))
                            st.caption(f"Latency: {item.get('latency_ms', '—')} ms")
                            if item.get("error"):
                                st.warning(item["error"])
                            with st.expander("Raw model output"):
                                st.code(item.get("raw", ""), language="json")
                else:
                    st.info("This strategy artifact does not include raw outputs.")
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            st.error(f"Could not read this experiment artifact: {exc}")

with tab_live:
    st.subheader("Run a live product extraction")
    st.write("Send a product title and its bullet points to the evaluation API. The result is a single live model response, not a benchmark score.")
    with st.form("live_extraction"):
        title = st.text_input("Product title", placeholder="e.g. Wireless noise-cancelling headphones")
        bullets = st.text_area("Product bullet points", height=150, placeholder="Paste product features. Separate points with new lines or |.")
        strategy = st.selectbox("Prompt strategy", ["structured", "zero_shot", "cot", "role_based"])
        run = st.form_submit_button("Extract attributes", type="primary", use_container_width=True, disabled=not title.strip() or not bullets.strip())
    if run:
        try:
            with st.spinner("Calling the extraction API…"):
                response = requests.post(f"{API_URL}/extract", json={
                    "item_name": title,
                    "bullet_points": bullets,
                    "strategy": strategy,
                    "provider": "groq",
                }, timeout=90)
                response.raise_for_status()
                result = response.json()
            st.success("Extraction completed.")
            st.subheader("Extracted attributes")
            st.json(result.get("prediction", {}))
            judge = result.get("judge")
            if judge:
                cols = st.columns(3)
                cols[0].metric("Judge score", f"{judge.get('score', '—')}/5")
                cols[1].metric("Correct attributes", len(judge.get("correct_attributes", [])))
                cols[2].metric("Incorrect attributes", len(judge.get("incorrect_attributes", [])))
                st.markdown("**Judge rationale**")
                st.write(judge.get("reason", ""))
                with st.expander("Correct and incorrect attribute details"):
                    st.write("Correct")
                    st.write(judge.get("correct_attributes", []))
                    st.write("Incorrect")
                    st.write(judge.get("incorrect_attributes", []))
            with st.expander("Raw model output"):
                st.code(result.get("raw_output", ""), language="json")
        except requests.RequestException as exc:
            st.error(f"Extraction request failed: {exc}")
