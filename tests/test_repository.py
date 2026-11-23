from contextlib import contextmanager
from uuid import uuid4

from backend import repository


class FakeCursor:
    def __init__(self, rows=None):
        self.rows = rows or []
        self.executed = None
        self.batch = None

    def execute(self, query, params):
        self.executed = (query, params)
        return self

    def executemany(self, query, rows):
        self.batch = (query, rows)
        return self


class FakeConnection:
    def __init__(self):
        self.cursor = FakeCursor([{"run_id": "abc", "status": "pending"}])

    def execute(self, query, params):
        return self.cursor.execute(query, params)

    def executemany(self, query, rows):
        return self.cursor.executemany(query, rows)


def test_create_run_uses_bound_parameters(monkeypatch):
    fake = FakeConnection()

    @contextmanager
    def fake_connection():
        yield fake

    monkeypatch.setattr(repository, "connection", fake_connection)
    result = repository.create_run(
        run_type="general_quality",
        provider="mock",
        model_name="mock-model",
        configuration={"seed": 42},
    )
    assert result["status"] == "pending"
    assert "%s" in fake.cursor.executed[0]
    assert "mock-model" in fake.cursor.executed[1]


def test_add_results_uses_parameterized_batch_and_handles_empty(monkeypatch):
    fake = FakeConnection()

    @contextmanager
    def fake_connection():
        yield fake

    monkeypatch.setattr(repository, "connection", fake_connection)
    assert repository.add_results(uuid4(), []) == 0
    count = repository.add_results(uuid4(), [{
        "case_id": "CASE-1", "category": "reasoning", "prompt": "Question",
        "status": "success", "metrics": {"keyword_f1": 0.5},
    }])
    assert count == 1
    assert "ON CONFLICT" in fake.cursor.batch[0]
    assert len(fake.cursor.batch[1]) == 1
