"""Tests for request follow-up messages."""

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


def _create_request():
    response = client.post(
        "/requests/",
        json={
            "text": "Still stuck on binary search edge cases.",
            "anonymous": False,
            "student_id": "s1",
            "student_name": "Sara",
            "course": "CS 400",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_list_followups():
    created = _create_request()
    request_id = created["id"]
    assert created.get("followups") == []

    post = client.post(
        f"/requests/{request_id}/followups",
        json={
            "message": "I tried the mid+1 tip but still get an off-by-one.",
            "author_role": "student",
            "author_name": "Sara",
        },
    )
    assert post.status_code == 201
    followup = post.json()
    assert followup["request_id"] == request_id
    assert followup["author_role"] == "student"
    assert "off-by-one" in followup["message"]

    listed = client.get(f"/requests/{request_id}/followups")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    detail = client.get(f"/requests/{request_id}")
    assert detail.status_code == 200
    assert len(detail.json()["followups"]) == 1
    assert detail.json()["followups"][0]["message"] == followup["message"]


def test_followup_appears_on_ta_queue():
    created = _create_request()
    request_id = created["id"]
    client.post(
        f"/requests/{request_id}/followups",
        json={
            "message": "Can a TA look at my loop bounds?",
            "author_role": "student",
            "author_name": "Sara",
        },
    )
    queue = client.get("/ta/queue/")
    assert queue.status_code == 200
    item = next(row for row in queue.json() if row["request"]["id"] == request_id)
    assert len(item["request"]["followups"]) == 1


def test_followup_not_found_request():
    response = client.post(
        "/requests/999/followups",
        json={
            "message": "Hello",
            "author_role": "student",
            "author_name": "Sara",
        },
    )
    assert response.status_code == 404
