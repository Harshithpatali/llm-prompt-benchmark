"""Reproducible runner for the general-response quality benchmark.

Run with: python -m experiments.run_quality_benchmark
Live execution requires provider credentials and may incur API charges.
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Callable, Any

from backend.evaluator import evaluate_reference_overlap
from backend.quality_datasets import GENERAL_BENCHMARK_PATH, load_general_benchmark


CallModel = Callable[[Any, str, str], tuple[str, float, int | None, int | None, str | None]]


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 2)


def run_cases(
    cases: list[dict],
    *,
    provider: str,
    model: str,
    client: Any,
    call_model: CallModel,
) -> dict:
    """Run the exact supplied cases and return per-case plus aggregate diagnostics."""
    if not cases:
        raise ValueError("At least one benchmark case is required")
    ids = [str(case.get("case_id", "")).strip() for case in cases]
    if any(not case_id for case_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("Benchmark cases must have unique, non-empty case_id values")

    rows = []
    by_category: dict[str, list[dict]] = defaultdict(list)
    for case in cases:
        for field in ("prompt", "reference_answer", "category", "difficulty"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"Case {case['case_id']} requires non-empty '{field}'")

        raw, latency_ms, prompt_tokens, completion_tokens, error = call_model(
            client, model, case["prompt"]
        )
        evaluation = (
            evaluate_reference_overlap(raw, case["reference_answer"])
            if not error else None
        )
        row = {
            "case_id": case["case_id"],
            "category": case["category"],
            "difficulty": case["difficulty"],
            "prompt": case["prompt"],
            "reference_answer": case["reference_answer"],
            "response": raw,
            "status": "error" if error else "success",
            "error": error,
            "latency_ms": round(float(latency_ms), 2) if latency_ms is not None else None,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "evaluation": evaluation,
        }
        rows.append(row)
        by_category[case["category"]].append(row)

    successful = [row for row in rows if row["status"] == "success"]
    latencies = [row["latency_ms"] for row in successful if row["latency_ms"] is not None and row["latency_ms"] > 0]
    scores = [row["evaluation"] for row in successful if row["evaluation"] is not None]

    category_summary = {}
    for category, category_rows in sorted(by_category.items()):
        category_scores = [
            row["evaluation"] for row in category_rows
            if row["evaluation"] is not None
        ]
        category_summary[category] = {
            "n_cases": len(category_rows),
            "n_successful": len(category_scores),
            "mean_keyword_f1": round(mean(x["keyword_f1"] for x in category_scores), 4) if category_scores else None,
            "mean_lexical_heuristic_score": round(mean(x["heuristic_score"] for x in category_scores), 2) if category_scores else None,
        }

    return {
        "metadata": {
            "provider": provider,
            "model": model,
            "dataset": "general_response_benchmark",
            "case_ids": ids,
            "n_cases": len(cases),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "metric_note": (
                "Keyword overlap and length diagnostics only. They are not semantic "
                "correctness, factuality, groundedness, relevance, or safety scores."
            ),
        },
        "summary": {
            "n_cases": len(rows),
            "n_successful": len(successful),
            "n_failed": len(rows) - len(successful),
            "request_failure_rate": round((len(rows) - len(successful)) / len(rows), 4),
            "mean_keyword_f1": round(mean(x["keyword_f1"] for x in scores), 4) if scores else None,
            "mean_lexical_heuristic_score": round(mean(x["heuristic_score"] for x in scores), 2) if scores else None,
            "latency_mean_ms": round(mean(latencies), 2) if latencies else None,
            "latency_p50_ms": _percentile(latencies, 0.50),
            "latency_p95_ms": _percentile(latencies, 0.95),
            "total_prompt_tokens": sum(row["prompt_tokens"] or 0 for row in rows),
            "total_completion_tokens": sum(row["completion_tokens"] or 0 for row in rows),
        },
        "by_category": category_summary,
        "results": rows,
    }


def _dataset_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from experiments.run_experiment import DEFAULT_MODELS, make_client, call_model as call_prompt_benchmark_model

    provider = os.getenv("PROVIDER", "groq").strip().lower()
    model = os.getenv("MODEL_NAME", DEFAULT_MODELS.get(provider, "")).strip()
    if not model:
        raise SystemExit(f"MODEL_NAME is required for provider '{provider}'")

    all_cases = load_general_benchmark()
    limit = int(os.getenv("QUALITY_SAMPLE_SIZE", "60"))
    if limit < 1:
        raise SystemExit("QUALITY_SAMPLE_SIZE must be at least 1")
    cases = all_cases[:limit]
    client = make_client(provider)
    payload = run_cases(
        cases, provider=provider, model=model, client=client,
        call_model=call_prompt_benchmark_model,
    )
    payload["metadata"]["dataset_path"] = str(GENERAL_BENCHMARK_PATH.relative_to(GENERAL_BENCHMARK_PATH.parents[1]))
    payload["metadata"]["dataset_sha256"] = _dataset_sha256(GENERAL_BENCHMARK_PATH)
    payload["metadata"]["dataset_total_cases"] = len(all_cases)
    payload["metadata"]["sample_selection"] = "first N cases in versioned dataset order"

    Path("results").mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_model = model.replace("/", "_").replace(":", "_")
    output = Path("results") / f"quality_{provider}_{safe_model}_{timestamp}.json"
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"result_file": str(output), "metadata": payload["metadata"], "summary": payload["summary"]}, indent=2))


if __name__ == "__main__":
    main()
