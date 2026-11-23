"""Convert seller-support scenarios into unlabelled human-review tasks."""
from __future__ import annotations

from typing import Any

from backend.ops_metrics import DIMENSIONS
from backend.quality_datasets import load_seller_support_tasks

DIMENSION_LABELS = {"pass", "minor_issue", "major_issue", "not_applicable"}
OVERALL_LABELS = {"accept", "revise", "reject", "escalate"}


def build_review_tasks(tasks: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Create pending review tasks without inventing reviewer labels."""
    source_tasks = tasks if tasks is not None else load_seller_support_tasks()
    output = []
    seen_ids: set[str] = set()

    for row in source_tasks:
        task_id = str(row.get("task_id", "")).strip()
        if not task_id or task_id in seen_ids:
            raise ValueError("Review task source must contain unique, non-empty task_id values")
        seen_ids.add(task_id)

        required = ("category", "difficulty", "query", "context", "response", "expected")
        missing = [field for field in required if not isinstance(row.get(field), str) or not row[field].strip()]
        if missing:
            raise ValueError(f"Task {task_id} is missing required fields: {', '.join(missing)}")

        output.append({
            "review_task_id": task_id,
            "source_dataset": "seller_support_tasks",
            "category": row["category"],
            "difficulty": row["difficulty"],
            "query": row["query"],
            "context": row["context"],
            "candidate_response": row["response"],
            "review_guidance": row["expected"],
            "review_dimensions": list(DIMENSIONS),
            "status": "pending",
            "is_seed_example": True,
        })
    return output


def validate_annotation_submission(task: dict[str, Any], submission: dict[str, Any]) -> dict[str, Any]:
    """Validate one human submission; returns normalized data without persistence."""
    task_id = str(task.get("review_task_id", "")).strip()
    if not task_id:
        raise ValueError("A valid review_task_id is required")

    annotator_id = str(submission.get("annotator_id", "")).strip()
    if not annotator_id:
        raise ValueError("annotator_id must be a non-empty pseudonymous identifier")

    dimensions = submission.get("dimensions")
    if not isinstance(dimensions, dict):
        raise ValueError("dimensions must be an object")
    missing_dimensions = sorted(set(DIMENSIONS) - dimensions.keys())
    if missing_dimensions:
        raise ValueError(f"Missing review dimensions: {', '.join(missing_dimensions)}")
    invalid_labels = {
        key: value for key, value in dimensions.items()
        if key in DIMENSIONS and value not in DIMENSION_LABELS
    }
    if invalid_labels:
        raise ValueError(f"Invalid dimension labels: {invalid_labels}")

    overall_label = submission.get("overall_label")
    if overall_label not in OVERALL_LABELS:
        raise ValueError(f"overall_label must be one of {sorted(OVERALL_LABELS)}")

    evidence = submission.get("evidence")
    if not isinstance(evidence, str) or not 8 <= len(evidence.strip()) <= 4000:
        raise ValueError("evidence must contain between 8 and 4000 characters")

    confidence = submission.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int) or not 1 <= confidence <= 5:
        raise ValueError("confidence must be an integer between 1 and 5")

    handling_seconds = submission.get("handling_seconds", 0)
    if isinstance(handling_seconds, bool) or not isinstance(handling_seconds, int) or handling_seconds < 0:
        raise ValueError("handling_seconds must be a non-negative integer")

    escalated = submission.get("escalated", overall_label == "escalate")
    if not isinstance(escalated, bool):
        raise ValueError("escalated must be a boolean")

    defect_category = submission.get("defect_category", "none")
    if not isinstance(defect_category, str) or not defect_category.strip():
        raise ValueError("defect_category must be a non-empty string")

    return {
        "task_id": task_id,
        "annotator_id": annotator_id,
        **{dimension: dimensions[dimension] for dimension in DIMENSIONS},
        "overall_label": overall_label,
        "evidence": evidence.strip(),
        "confidence": confidence,
        "handling_seconds": handling_seconds,
        "escalated": escalated,
        "defect_category": defect_category.strip(),
        "is_audit": bool(submission.get("is_audit", False)),
    }
