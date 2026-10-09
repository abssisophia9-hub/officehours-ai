"""Identity + help-mode (meeting preference) request behavior."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import post_student_request, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_anonymous_strips_identity():
    created, _, _ = post_student_request(
        client,
        "How do hash tables handle collisions?",
        student_id="should-not-persist",
        student_name="Hidden",
        help_mode="message",
    )
    created = created.json()
    assert created["anonymous"] is True
    assert created["student_id"] is None
    assert created["student_name"] is None


def test_identified_ask_keeps_name():
    created, _, _ = post_student_request(
        client,
        "Can we review red-black deletion together?",
        anonymous=False,
        student_id="117400",
        student_name="Sara El Idrissi",
        help_mode="message",
    )
    created = created.json()
    assert created["student_id"] == "117400"
    assert created["student_name"] == "Sara El Idrissi"


def test_identified_ask_requires_identity():
    headers, course_id = student_auth(client)
    response = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "I want to be identified but sent nothing.",
            "anonymous": False,
            "help_mode": "message",
            "course_id": course_id,
        },
    )
    assert response.status_code == 422


def test_face_to_face_help_mode_sets_action():
    created, headers, _ = post_student_request(
        client,
        "I need an in-person walkthrough of chaining vs open addressing.",
        help_mode="face_to_face",
    )
    created = created.json()
    assert created["help_mode"] == "face_to_face"
    status = client.get(f"/requests/{created['id']}/status", headers=headers).json()
    assert status["help_mode"] == "face_to_face"


def test_online_meeting_help_mode():
    created, _, _ = post_student_request(
        client,
        "Can we do a short Zoom on mergesort recurrence?",
        anonymous=False,
        student_name="Youssef Amrani",
        help_mode="online_meeting",
    )
    assert created.json()["help_mode"] == "online_meeting"


def test_invalid_help_mode_rejected():
    headers, course_id = student_auth(client)
    response = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "Bad modality",
            "anonymous": True,
            "help_mode": "carrier_pigeon",
            "course_id": course_id,
        },
    )
    assert response.status_code == 422
