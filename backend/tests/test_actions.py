import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import post_student_request, professor_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _staff():
    return professor_auth(client, "CSC 3374")


def test_create_recommendation_decision_generates_action_plan():
    staff, _ = _staff()
    client.post(
        "/office-hours/",
        headers=staff,
        json={
            "day": "Monday",
            "start": "10:00",
            "end": "11:30",
            "location": "Room 204",
        },
    )

    first, _, _ = post_student_request(
        client,
        "I am confused about recursion and binary search.",
        anonymous=False,
        student_id="117027",
        student_name="Sara",
    )
    second, _, _ = post_student_request(
        client, "Can we review recursion tracing in office hours?"
    )
    first = first.json()
    second = second.json()

    response = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group_session:recursion:cluster-1",
            "action_kind": "group_session",
            "action_title": "Review in office hours; schedule a group session if repeated",
            "status": "approved",
            "cluster_id": first["cluster_id"],
            "professor_note": "Start with recursion tracing examples.",
            "request_ids": [first["id"], second["id"]],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "approved"
    assert data["request_ids"] == [first["id"], second["id"]]
    assert data["action_plan"]["plan_type"] == "group_session"
    assert data["action_plan"]["privacy"]["identified_requests"] == 1
    assert data["action_plan"]["privacy"]["anonymous_requests"] == 1


def test_export_recommendation_calendar_returns_ics_file():
    staff, _ = _staff()
    client.post(
        "/office-hours/",
        headers=staff,
        json={
            "day": "Tuesday",
            "start": "13:00",
            "end": "14:00",
            "location": "Room 101",
        },
    )
    request, _, _ = post_student_request(
        client, "Can we review graph algorithms before the final?"
    )
    request = request.json()
    decision = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group_session:graphs:cluster-1",
            "action_kind": "group_session",
            "action_title": "Schedule group review session",
            "status": "approved",
            "cluster_id": request["cluster_id"],
            "request_ids": [request["id"]],
        },
    ).json()

    response = client.get(
        f"/actions/recommendations/{decision['id']}/calendar.ics",
        headers=staff,
    )
    assert response.status_code == 200
    assert "BEGIN:VCALENDAR" in response.text


def test_export_recommendation_calendar_requires_office_hours():
    staff, _ = _staff()
    request, _, _ = post_student_request(client, "Need help with integration.")
    request = request.json()
    decision = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group_session:integration:cluster-1",
            "action_kind": "group_session",
            "action_title": "Schedule group review session",
            "status": "approved",
            "request_ids": [request["id"]],
        },
    ).json()

    response = client.get(
        f"/actions/recommendations/{decision['id']}/calendar.ics",
        headers=staff,
    )
    assert response.status_code == 404


def test_list_recommendation_decisions_returns_saved_entries():
    staff, _ = _staff()
    request, _, _ = post_student_request(
        client, "I am confused about recursion and binary search."
    )
    request = request.json()
    created = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group_session:recursion:cluster-1",
            "action_kind": "group_session",
            "action_title": "Review in office hours",
            "status": "approved",
            "cluster_id": request["cluster_id"],
            "request_ids": [request["id"]],
        },
    ).json()

    response = client.get("/actions/recommendations/", headers=staff)
    assert response.status_code == 200
    assert response.json()[0]["id"] == created["id"]


def test_create_recommendation_decision_requires_existing_requests():
    staff, _ = _staff()
    response = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "missing",
            "action_kind": "manual_review",
            "action_title": "Review manually",
            "status": "approved",
            "request_ids": [999],
        },
    )
    assert response.status_code == 404
