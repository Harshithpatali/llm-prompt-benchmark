"""Validated loaders for the general-response and seller-support datasets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GENERAL_BENCHMARK_PATH = PROJECT_ROOT / "data" / "benchmark.jsonl"
SELLER_SUPPORT_PATH = PROJECT_ROOT / "data" / "seller_support_tasks.json"

GENERAL_REQUIRED = {
    "case_id", "category", "difficulty", "prompt",
    "reference_answer", "evaluation_criteria",
}
SELLER_REQUIRED = {
    "task_id", "category", "query", "context",
    "response", "expected", "difficulty",
}


def _require_nonempty_string(record: dict[str, Any], field: str, location: str) -> None:
    if not isinstance(record.get(field), str) or not record[field].strip():
        raise ValueError(f"{location}: '{field}' must be a non-empty string")


def load_general_benchmark(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load JSONL general benchmark cases and validate IDs and required fields."""
    source = Path(path) if path is not None else GENERAL_BENCHMARK_PATH
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    with source.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            location = f"{source}:{line_number}"
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{location}: invalid JSON: {exc.msg}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{location}: each JSONL row must be an object")
            missing = sorted(GENERAL_REQUIRED - row.keys())
            if missing:
                raise ValueError(f"{location}: missing required fields: {', '.join(missing)}")
            for field in ("case_id", "category", "difficulty", "prompt", "reference_answer"):
                _require_nonempty_string(row, field, location)
            criteria = row["evaluation_criteria"]
            if not isinstance(criteria, list) or not criteria or not all(
                isinstance(item, str) and item.strip() for item in criteria
            ):
                raise ValueError(f"{location}: evaluation_criteria must be a non-empty list of strings")
            case_id = row["case_id"]
            if case_id in seen_ids:
                raise ValueError(f"{location}: duplicate case_id '{case_id}'")
            seen_ids.add(case_id)
            rows.append(row)

    if not rows:
        raise ValueError(f"No benchmark cases found in {source}")
    return rows


def load_seller_support_tasks(path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load and validate seller-support challenge scenarios from a JSON array."""
    source = Path(path) if path is not None else SELLER_SUPPORT_PATH
    try:
        rows = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON: {exc.msg}") from exc

    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{source}: expected a non-empty JSON array")

    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        location = f"{source}:record {index}"
        if not isinstance(row, dict):
            raise ValueError(f"{location}: each task must be an object")
        missing = sorted(SELLER_REQUIRED - row.keys())
        if missing:
            raise ValueError(f"{location}: missing required fields: {', '.join(missing)}")
        for field in SELLER_REQUIRED:
            _require_nonempty_string(row, field, location)
        task_id = row["task_id"]
        if task_id in seen_ids:
            raise ValueError(f"{location}: duplicate task_id '{task_id}'")
        seen_ids.add(task_id)
    return rows
