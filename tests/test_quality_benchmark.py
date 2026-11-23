from experiments.run_quality_benchmark import run_cases
from experiments.build_quality_report import build_report


def _fake_call(client, model, prompt):
    if "fail this request" in prompt:
        return "", None, None, None, "TimeoutError: simulated"
    return "A customer can request a refund within 30 days.", 125.0, 12, 9, None


def test_run_cases_records_metrics_failures_and_same_case_ids():
    cases = [
        {
            "case_id": "A1",
            "category": "support",
            "difficulty": "easy",
            "prompt": "Explain the return policy.",
            "reference_answer": "A customer can request a refund within 30 days.",
        },
        {
            "case_id": "A2",
            "category": "support",
            "difficulty": "medium",
            "prompt": "fail this request",
            "reference_answer": "A customer should receive a clear answer.",
        },
    ]
    result = run_cases(
        cases, provider="mock", model="mock-model", client=None, call_model=_fake_call
    )
    assert result["metadata"]["case_ids"] == ["A1", "A2"]
    assert result["summary"]["n_cases"] == 2
    assert result["summary"]["n_successful"] == 1
    assert result["summary"]["n_failed"] == 1
    assert result["summary"]["request_failure_rate"] == 0.5
    assert result["results"][0]["evaluation"]["keyword_f1"] == 1.0
    assert result["results"][1]["evaluation"] is None


def test_run_cases_rejects_duplicate_case_ids():
    case = {
        "case_id": "DUP",
        "category": "support",
        "difficulty": "easy",
        "prompt": "Question",
        "reference_answer": "Answer",
    }
    try:
        run_cases([case, case], provider="mock", model="mock", client=None, call_model=_fake_call)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("Expected duplicate case ID validation")


def test_report_contains_limits_and_category_summary():
    payload = {
        "metadata": {"provider": "mock", "model": "mock-model", "n_cases": 1},
        "summary": {
            "n_successful": 1, "n_failed": 0, "request_failure_rate": 0.0,
            "mean_keyword_f1": 0.8, "mean_lexical_heuristic_score": 85.0,
            "latency_mean_ms": 100.0, "latency_p95_ms": 100.0,
        },
        "by_category": {
            "support": {"n_cases": 1, "n_successful": 1, "mean_keyword_f1": 0.8}
        },
    }
    report = build_report(payload)
    assert "Category diagnostics" in report
    assert "not establish semantic correctness" in report
    assert "support" in report
