import pytest

from backend.review_tasks import build_review_tasks, validate_annotation_submission


def test_seed_scenarios_become_pending_unlabelled_review_tasks():
    tasks = build_review_tasks()
    assert len(tasks) == 16
    assert len({task["review_task_id"] for task in tasks}) == 16
    assert all(task["status"] == "pending" for task in tasks)
    assert all(task["is_seed_example"] for task in tasks)
    assert all("overall_label" not in task for task in tasks)
    assert all("annotator_id" not in task for task in tasks)


def test_submission_validation_returns_pseudonymous_human_decision():
    task = build_review_tasks()[0]
    submission = {
        "annotator_id": "reviewer-001",
        "dimensions": {
            "relevance": "pass",
            "correctness": "major_issue",
            "completeness": "pass",
        },
        "overall_label": "reject",
        "evidence": "The answer contradicts the supplied order status.",
        "confidence": 4,
        "handling_seconds": 55,
        "escalated": True,
        "defect_category": "factual_consistency",
    }
    result = validate_annotation_submission(task, submission)
    assert result["task_id"] == task["review_task_id"]
    assert result["annotator_id"] == "reviewer-001"
    assert result["overall_label"] == "reject"
    assert result["correctness"] == "major_issue"


def test_submission_validation_rejects_missing_evidence_and_bad_labels():
    task = build_review_tasks()[0]
    submission = {
        "annotator_id": "reviewer-002",
        "dimensions": {
            "relevance": "pass",
            "correctness": "pass",
            "completeness": "pass",
        },
        "overall_label": "accept",
        "evidence": "short",
        "confidence": 3,
    }
    with pytest.raises(ValueError, match="evidence"):
        validate_annotation_submission(task, submission)
    submission["evidence"] = "Evidence with enough detail."
    submission["dimensions"]["correctness"] = "unknown"
    with pytest.raises(ValueError, match="Invalid dimension labels"):
        validate_annotation_submission(task, submission)


def test_review_task_builder_rejects_duplicate_ids():
    rows = [
        {
            "task_id": "X", "category": "returns", "difficulty": "easy",
            "query": "Question", "context": "Policy context",
            "response": "Candidate answer", "expected": "Review guidance",
        },
        {
            "task_id": "X", "category": "returns", "difficulty": "easy",
            "query": "Question", "context": "Policy context",
            "response": "Candidate answer", "expected": "Review guidance",
        },
    ]
    with pytest.raises(ValueError, match="unique"):
        build_review_tasks(rows)
