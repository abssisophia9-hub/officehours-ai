import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import post_student_request, professor_auth, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_get_request_status_for_queued_request():
    created, headers, _ = post_student_request(client, "Can you explain BFS vs DFS?")
    created = created.json()
    response = client.get(f"/requests/{created['id']}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["request_code"] == created["id"]
    assert data["status"] == "queued"
    assert data["anonymous_submission"] is True
    assert "student_id" not in data


def test_get_request_status_hides_identity_for_identified_request():
    created, headers, _ = post_student_request(
        client,
        "Need help with my grade.",
        anonymous=False,
        student_id="117027",
        student_name="Sara",
    )
    created = created.json()
    response = client.get(f"/requests/{created['id']}/status", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["anonymous_submission"] is False
    assert "117027" not in response.text


def test_get_request_status_reflects_approved_action_plan():
    request, headers, _ = post_student_request(
        client, "Can we review recursion before the final?"
    )
    request = request.json()
    staff, _ = professor_auth(client, "CSC 3374")
    client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group_session:recursion:cluster-1",
            "action_kind": "group_session",
            "action_title": "Schedule group review session",
            "status": "approved",
            "cluster_id": request["cluster_id"],
            "request_ids": [request["id"]],
        },
    )
    response = client.get(f"/requests/{request['id']}/status", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "action_planned"


def test_get_request_status_returns_404_for_missing_request():
    headers, _ = student_auth(client)
    response = client.get("/requests/999/status", headers=headers)
    assert response.status_code == 404
