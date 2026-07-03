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


def test_create_recommendation_decision_generates_action_plan():
    client.post(
        "/office-hours/",
        json={
            "day": "Monday",
            "start": "10:00",
            "end": "11:30",
            "location": "Room 204",
        },
    )

    first = client.post(
        "/requests/",
        json={
            "text": "I am confused about recursion and binary search.",
            "anonymous": False,
            "student_id": "117027",
        },
    ).json()
    second = client.post(
        "/requests/",
        json={
            "text": "Can we review recursion tracing in office hours?",
            "anonymous": True,
        },
    ).json()

    response = client.post(
        "/actions/recommendations/",
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
    assert data["action_plan"]["agenda_item"]["format"] == "Open walk-in mini-session"
    assert data["action_plan"]["calendar"]["ics_ready"] is True
    assert data["action_plan"]["calendar"]["office_hours_window"]["location"] == "Room 204"
    assert data["action_plan"]["privacy"]["identified_requests"] == 1
    assert data["action_plan"]["privacy"]["anonymous_requests"] == 1


def test_export_recommendation_calendar_returns_ics_file():
    client.post(
        "/office-hours/",
        json={
            "day": "Tuesday",
            "start": "13:00",
            "end": "14:00",
            "location": "Room 101",
        },
    )
    request = client.post(
        "/requests/",
        json={
            "text": "Can we review graph algorithms before the final?",
            "anonymous": True,
        },
    ).json()
    decision = client.post(
        "/actions/recommendations/",
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
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/calendar")
    assert "BEGIN:VCALENDAR" in response.text
    assert "SUMMARY:" in response.text
    assert 'filename="officehours-action-' in response.headers["content-disposition"]


def test_export_recommendation_calendar_requires_office_hours():
    request = client.post(
        "/requests/",
        json={"text": "Need help with integration.", "anonymous": True},
    ).json()
    decision = client.post(
        "/actions/recommendations/",
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
    )

    assert response.status_code == 404


def test_create_recommendation_decision_requires_existing_requests():
    response = client.post(
        "/actions/recommendations/",
        json={
            "card_id": "missing",
            "action_kind": "manual_review",
            "action_title": "Review manually",
            "status": "approved",
            "request_ids": [999],
        },
    )

    assert response.status_code == 404
