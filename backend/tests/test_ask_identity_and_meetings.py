"""Identity + help-mode (meeting preference) request behavior."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_anonymous_strips_identity():
    created = client.post(
        "/requests/",
        json={
            "text": "How do hash tables handle collisions?",
            "anonymous": True,
            "student_id": "should-not-persist",
            "student_name": "Hidden",
            "help_mode": "message",
        },
    ).json()
    assert created["anonymous"] is True
    assert created["student_id"] is None
    assert created["student_name"] is None
    assert created["help_mode"] == "message"


def test_identified_ask_keeps_name():
    created = client.post(
        "/requests/",
        json={
            "text": "Can we review red-black deletion together?",
            "anonymous": False,
            "student_id": "117400",
            "student_name": "Sara El Idrissi",
            "help_mode": "message",
        },
    ).json()
    assert created["anonymous"] is False
    assert created["student_id"] == "117400"
    assert created["student_name"] == "Sara El Idrissi"


def test_identified_ask_requires_identity():
    response = client.post(
        "/requests/",
        json={
            "text": "I want to be identified but sent nothing.",
            "anonymous": False,
            "help_mode": "message",
        },
    )
    assert response.status_code == 422


def test_face_to_face_help_mode_sets_action():
    created = client.post(
        "/requests/",
        json={
            "text": "I need an in-person walkthrough of chaining vs open addressing.",
            "anonymous": True,
            "help_mode": "face_to_face",
        },
    ).json()
    assert created["help_mode"] == "face_to_face"
    assert "face-to-face" in (created["recommended_action"] or "").lower()

    status = client.get(f"/requests/{created['id']}/status").json()
    assert status["help_mode"] == "face_to_face"
    assert "face-to-face" in (status["recommended_next_step"] or "").lower()


def test_online_meeting_help_mode():
    created = client.post(
        "/requests/",
        json={
            "text": "Can we do a short Zoom on mergesort recurrence?",
            "anonymous": False,
            "student_name": "Youssef Amrani",
            "help_mode": "online_meeting",
        },
    ).json()
    assert created["help_mode"] == "online_meeting"
    assert "online" in (created["recommended_action"] or "").lower()


def test_invalid_help_mode_rejected():
    response = client.post(
        "/requests/",
        json={
            "text": "Bad modality",
            "anonymous": True,
            "help_mode": "carrier_pigeon",
        },
    )
    assert response.status_code == 422
