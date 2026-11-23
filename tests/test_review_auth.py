import pytest
from fastapi import HTTPException

from backend.main import require_review_api_key


def test_review_api_fails_closed_when_secret_is_not_configured(monkeypatch):
    monkeypatch.delenv("REVIEW_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        require_review_api_key("any-value")
    assert exc.value.status_code == 503


def test_review_api_rejects_missing_or_invalid_key(monkeypatch):
    monkeypatch.setenv("REVIEW_API_KEY", "test-secret-value")
    with pytest.raises(HTTPException) as missing:
        require_review_api_key(None)
    assert missing.value.status_code == 401
    with pytest.raises(HTTPException) as invalid:
        require_review_api_key("wrong-secret")
    assert invalid.value.status_code == 401


def test_review_api_accepts_matching_key(monkeypatch):
    monkeypatch.setenv("REVIEW_API_KEY", "test-secret-value")
    assert require_review_api_key("test-secret-value") is None
