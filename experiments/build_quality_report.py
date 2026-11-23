"""Build a Markdown report from the latest general quality benchmark result."""
from __future__ import annotations

import json
from pathlib import Path


def build_report(payload: dict) -> str:
    metadata = payload.get("metadata", {})
    summary = payload.get("summary", {})
    categories = payload.get("by_category", {})
    lines = [
        "# General LLM Response Benchmark",
        "",
        f"- Provider: {metadata.get('provider', 'unknown')}",
        f"- Model: {metadata.get('model', 'unknown')}",
        f"- Dataset: {metadata.get('dataset', 'unknown')}",
        f"- Cases: {metadata.get('n_cases', 'unknown')}",
        f"- Timestamp (UTC): {metadata.get('timestamp_utc', 'unknown')}",
        f"- Dataset SHA-256: {metadata.get('dataset_sha256', 'not recorded')}",
        "",
        "## Execution summary",
        "",
        "| Measure | Value |",
        "|---|---:|",
        f"| Successful requests | {summary.get('n_successful', 0)} |",
        f"| Failed requests | {summary.get('n_failed', 0)} |",
        f"| Request failure rate | {summary.get('request_failure_rate', 0):.3f} |",
        f"| Mean keyword F1 (lexical) | {summary.get('mean_keyword_f1') if summary.get('mean_keyword_f1') is not None else '—'} |",
        f"| Mean lexical heuristic score | {summary.get('mean_lexical_heuristic_score') if summary.get('mean_lexical_heuristic_score') is not None else '—'} |",
        f"| Mean latency (ms) | {summary.get('latency_mean_ms') if summary.get('latency_mean_ms') is not None else '—'} |",
        f"| P95 latency (ms) | {summary.get('latency_p95_ms') if summary.get('latency_p95_ms') is not None else '—'} |",
        "",
        "## Category diagnostics",
        "",
        "| Category | Cases | Successful | Mean keyword F1 |",
        "|---|---:|---:|---:|",
    ]
    for category, values in sorted(categories.items()):
        f1 = values.get("mean_keyword_f1")
        lines.append(
            f"| {category} | {values.get('n_cases', 0)} | "
            f"{values.get('n_successful', 0)} | {f1:.4f} |" if f1 is not None
            else f"| {category} | {values.get('n_cases', 0)} | {values.get('n_successful', 0)} | — |"
        )
    lines += [
        "",
        "## Interpretation limits",
        "",
        "- Keyword precision, recall, F1, and length sanity are lexical diagnostics against reference text.",
        "- These measures do not establish semantic correctness, factuality, relevance, groundedness, or safety.",
        "- The dataset is a starter benchmark, not an externally validated gold standard.",
        "- Review individual responses and collect independent human annotations before making quality claims.",
        "- Request failures reduce the effective sample size; do not interpret scores without the failure rate.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    files = sorted(
        Path("results").glob("quality_*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise SystemExit("No general quality benchmark result JSON found in results/")
    payload = json.loads(files[0].read_text(encoding="utf-8"))
    report = build_report(payload)
    Path("reports").mkdir(exist_ok=True)
    output = Path("reports") / f"{files[0].stem}_report.md"
    output.write_text(report, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
