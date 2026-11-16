"""
Basic smoke test for the FastAPI app.

Run with: pytest
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "demo" in body
    assert body["database_ok"] is True
    assert body["database"] == "sqlite"
    assert isinstance(body["keys"], dict)
    assert set(body["keys"]) == {
        "GEMINI_API_KEY",
        "PEDAGOGY_GEMINI_API_KEY",
        "YOUTUBE_API_KEY",
        "DATABASE_URL",
        "CANVAS_BASE_URL",
        "CANVAS_API_TOKEN",
        "ANTHROPIC_API_KEY",
    }
    assert all(isinstance(v, bool) for v in body["keys"].values())
    # DATABASE_URL is set by this module for in-memory tests.
    assert body["keys"]["DATABASE_URL"] is True
    # Never leak secret values into the health payload.
    blob = response.text
    for secretish in ("aui-demo", "sk-", "AIza"):
        assert secretish not in blob


def test_create_request():
    from tests.helpers import student_auth

    headers, course_id = student_auth(client)
    payload = {
        "text": "I need help understanding recursion.",
        "anonymous": False,
        "student_id": "student-123",
        "student_name": "Sara El Idrissi",
        "course_id": course_id,
        "course": "CSC 3374",
    }

    response = client.post("/requests/", headers=headers, json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["text"] == payload["text"]
    assert data["anonymous"] is False
    assert data["student_id"] == "student-123"
    assert data["category"] == "conceptual_question"
    assert data["cluster_id"] == 1
    assert (
        data["recommended_action"]
        == "Review in office hours; schedule a group session if repeated"
    )
    assert "created_at" in data
