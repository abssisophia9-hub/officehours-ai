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


def test_get_request_status_for_queued_request():
    created = client.post(
        "/requests/",
        json={
            "text": "Can you explain BFS vs DFS?",
            "anonymous": True,
        },
    ).json()

    response = client.get(f"/requests/{created['id']}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["request_code"] == created["id"]
    assert data["status"] == "queued"
    assert data["anonymous_submission"] is True
    assert "student_id" not in data
    assert "text" not in data


def test_get_request_status_hides_identity_for_identified_request():
    created = client.post(
        "/requests/",
        json={
            "text": "Need help with my grade.",
            "anonymous": False,
            "student_id": "117027",
        },
    ).json()

    response = client.get(f"/requests/{created['id']}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["anonymous_submission"] is False
    assert "student_id" not in data
    assert "117027" not in response.text


def test_get_request_status_reflects_approved_action_plan():
    request = client.post(
        "/requests/",
        json={
            "text": "Can we review recursion before the final?",
            "anonymous": True,
        },
    ).json()
    client.post(
        "/actions/recommendations/",
        json={
            "card_id": "group_session:recursion:cluster-1",
            "action_kind": "group_session",
            "action_title": "Schedule group review session",
            "status": "approved",
            "cluster_id": request["cluster_id"],
            "request_ids": [request["id"]],
        },
    )

    response = client.get(f"/requests/{request['id']}/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "action_planned"
    assert data["recommended_next_step"] == "Schedule group review session"
    assert "office hours" in data["message"].lower()


def test_get_request_status_returns_404_for_missing_request():
    response = client.get("/requests/999/status")

    assert response.status_code == 404
