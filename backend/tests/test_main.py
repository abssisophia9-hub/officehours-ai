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
    assert response.json() == {"status": "healthy"}


def test_create_request():
    payload = {
        "text": "I need help understanding recursion.",
        "anonymous": False,
        "student_id": "student-123",
    }

    response = client.post("/requests/", json=payload)

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
