"""GET /health — DB probe + env key presence (no external calls, no values)."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import _HEALTH_ENV_KEYS, app

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health_database_ok_and_key_presence_shape(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-not-real")
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", "test-pedagogy-not-real")
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-not-real")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_API_TOKEN", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()

    assert body["status"] == "healthy"
    assert body["database_ok"] is True
    assert body["database"] == "sqlite"
    assert isinstance(body["demo"], bool)
    assert isinstance(body["rate_limit"], bool)

    keys = body["keys"]
    assert list(keys) == list(_HEALTH_ENV_KEYS)
    assert keys["GEMINI_API_KEY"] is True
    assert keys["PEDAGOGY_GEMINI_API_KEY"] is True
    assert keys["YOUTUBE_API_KEY"] is True
    assert keys["DATABASE_URL"] is True
    assert keys["CANVAS_BASE_URL"] is False
    assert keys["CANVAS_API_TOKEN"] is False
    assert keys["ANTHROPIC_API_KEY"] is False
    assert all(isinstance(v, bool) for v in keys.values())

    # Presence only — never echo secret values.
    text = response.text
    assert "test-gemini-not-real" not in text
    assert "test-pedagogy-not-real" not in text
    assert "test-youtube-not-real" not in text


def test_health_whitespace_key_counts_as_missing(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "   ")
    monkeypatch.setenv("YOUTUBE_API_KEY", "")
    response = client.get("/health")
    assert response.status_code == 200
    keys = response.json()["keys"]
    assert keys["GEMINI_API_KEY"] is False
    assert keys["YOUTUBE_API_KEY"] is False
