"""Ask Triage must degrade to rules when the ML embedder cannot load (not HTTP 500)."""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ANALYZER_BACKEND"] = "ml"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ.setdefault("OFFICEHOURS_SERVE_FRONTEND", "false")
os.environ.setdefault("OFFICEHOURS_DEMO", "true")

from fastapi.testclient import TestClient

from app.ai.classifier import classify
from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def _patch_classify_ml(monkeypatch, boom):
    """Patch both the module and Analyzer's bound import."""
    monkeypatch.setattr("app.ai.ml_classifier.classify_ml", boom)
    monkeypatch.setattr("app.ai.analyzer_agent.classify_ml", boom)


def test_classify_ml_embedder_failure_falls_back_to_rules(monkeypatch):
    def boom(_text: str, *, model_path=None):
        raise RuntimeError("SentenceTransformer offline / HF hub unavailable")

    monkeypatch.setenv("OFFICEHOURS_CLASSIFIER_BACKEND", "ml")
    _patch_classify_ml(monkeypatch, boom)

    result = classify("Explain red-black tree rotations after deletion.")
    assert result["classifier_backend"] == "rules_embedder_fallback"
    assert result["category"]


def test_ask_submit_not_500_when_embedder_raises(monkeypatch):
    def boom(_text: str, *, model_path=None):
        raise OSError("cannot load all-MiniLM-L6-v2")

    _patch_classify_ml(monkeypatch, boom)

    login = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    courses = client.get("/courses/mine", headers={"Authorization": f"Bearer {token}"})
    assert courses.status_code == 200
    course_id = courses.json()[0]["id"]
    course_code = courses.json()[0]["code"]

    response = client.post(
        "/requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "Explain red-black tree delete fixup rotations.",
            "course_id": course_id,
            "course": course_code,
            "anonymous": True,
            "help_mode": "message",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body.get("category")
    assert body.get("urgency")
    assert body.get("triage") is not None
