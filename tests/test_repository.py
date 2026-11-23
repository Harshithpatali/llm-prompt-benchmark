from contextlib import contextmanager
from uuid import uuid4

from backend import repository


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = []
        self.batch = None

    def execute(self, query, params):
        self.executed.append((query, params))
        return self

    def executemany(self, query, rows):
        self.batch = (query, rows)
        return self

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self):
        self.cursor = FakeCursor([{"run_id": "abc", "status": "pending", "annotation_id": "ann-1"}])

    def execute(self, query, params):
        return self.cursor.execute(query, params)

    def executemany(self, query, rows):
        return self.cursor.executemany(query, rows)


def _patch(monkeypatch):
    fake = FakeConnection()

    @contextmanager
    def fake_connection():
        yield fake

    monkeypatch.setattr(repository, "connection", fake_connection)
    return fake


def test_create_run_uses_bound_parameters(monkeypatch):
    fake = _patch(monkeypatch)
    result = repository.create_run(run_type="general_quality", provider="mock",
                                   model_name="mock-model", configuration={"seed": 42})
    assert result["status"] == "pending"
    assert "%s" in fake.cursor.executed[0]
    assert "mock-model" in fake.cursor.executed[1]


def test_add_results_uses_parameterized_batch_and_handles_empty(monkeypatch):
    fake = _patch(monkeypatch)
    assert repository.add_results(uuid4(), []) == 0
    count = repository.add_results(uuid4(), [{
        "case_id": "CASE-1", "category": "reasoning", "prompt": "Question",
        "status": "success", "metrics": {"keyword_f1": 0.5},
    }])
    assert count == 1
    assert "ON CONFLICT" in fake.cursor.batch[0]
    assert len(fake.cursor.batch[1]) == 1


def test_create_review_tasks_is_idempotent_insert(monkeypatch):
    fake = _patch(monkeypatch)
    count = repository.create_review_tasks([{
        "review_task_id": "SELL-001", "source_dataset": "seller_support_tasks",
        "category": "returns", "difficulty": "easy", "query": "Q",
        "context": "C", "candidate_response": "R", "review_guidance": "G",
    }])
    assert count == 1
    assert "ON CONFLICT (task_key) DO NOTHING" in fake.cursor.batch[0]


def test_submit_annotation_updates_task_and_audit_log(monkeypatch):
    fake = _patch(monkeypatch)
    result = repository.submit_annotation(uuid4(), {
        "annotator_id": "reviewer-1", "relevance": "pass", "correctness": "pass",
        "completeness": "minor_issue", "overall_label": "revise",
        "evidence": "Evidence long enough.", "confidence": 4,
        "handling_seconds": 35, "escalated": False,
        "defect_category": "completeness", "is_audit": False,
    })
    assert result["annotation_id"] == "ann-1"
    statements = [query for query, _ in fake.cursor.executed]
    assert any("FOR UPDATE" in query for query in statements)
    assert any("UPDATE public.annotation_tasks" in query for query in statements)
    assert any("INSERT INTO public.audit_events" in query for query in statements)
