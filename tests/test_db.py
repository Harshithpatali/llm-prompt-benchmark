import pytest

from backend.db import DatabaseConfigurationError, _database_url


def test_database_url_is_required(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(DatabaseConfigurationError, match="not configured"):
        _database_url()


def test_database_url_must_be_postgresql(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "https://example.com")
    with pytest.raises(DatabaseConfigurationError, match="PostgreSQL"):
        _database_url()


def test_database_url_is_returned_without_modification(monkeypatch):
    value = "postgresql://user:password@example.neon.tech/db?sslmode=require"
    monkeypatch.setenv("DATABASE_URL", value)
    assert _database_url() == value
