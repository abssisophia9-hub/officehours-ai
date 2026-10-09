"""Cluster → shared group meeting → student status surfaces time/place."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts
from tests.helpers import post_student_request, professor_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def test_group_meeting_appears_on_every_cluster_request_status():
    first, headers, _ = post_student_request(
        client,
        "Red-black tree delete fixup loops forever after uncle rotation.",
        code="CSC 2302",
        help_mode="face_to_face",
    )
    second, _, _ = post_student_request(
        client,
        "My red-black deletion fixup never terminates on uncle rotation.",
        code="CSC 2302",
        anonymous=False,
        student_name="Sara",
        help_mode="face_to_face",
    )
    first = first.json()
    second = second.json()
    staff, _ = professor_auth(client, "CSC 2302")

    response = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": f"group-cluster-{first.get('cluster_id') or first['id']}",
            "action_kind": "group_session",
            "action_title": "Group review: Red-Black Tree Deletion",
            "status": "approved",
            "cluster_id": first.get("cluster_id"),
            "request_ids": [first["id"], second["id"]],
            "meeting_title": "RB deletion board session",
            "meeting_when": "Thu 4:00–4:30 PM",
            "meeting_place": "Building 8 · Room 204",
        },
    )
    assert response.status_code == 201, response.text
    plan = response.json()["action_plan"]
    assert plan["meeting"]["when"] == "Thu 4:00–4:30 PM"
    assert plan["meeting"]["place"] == "Building 8 · Room 204"
    assert "RB deletion" in plan["student_update"]

    for request_id in (first["id"], second["id"]):
        status = client.get(
            f"/requests/{request_id}/status", headers=headers
        ).json()
        assert status["status"] == "action_planned"
        assert status["headline"] == "Group meeting scheduled"
        assert status["meeting_title"] == "RB deletion board session"
        assert status["meeting_when"] == "Thu 4:00–4:30 PM"
        assert status["meeting_place"] == "Building 8 · Room 204"
        assert status["group_meeting"]["place"] == "Building 8 · Room 204"
        assert "Thu 4:00" in status["message"] or "shared group meeting" in status["message"].lower()


def test_group_session_without_meeting_fields_still_works():
    created, headers, _ = post_student_request(
        client,
        "Please explain AVL double rotation after insert.",
        code="CSC 2302",
    )
    created = created.json()
    staff, _ = professor_auth(client, "CSC 2302")
    response = client.post(
        "/actions/recommendations/",
        headers=staff,
        json={
            "card_id": "group-legacy",
            "action_kind": "group_session",
            "action_title": "Review AVL rotations",
            "status": "approved",
            "request_ids": [created["id"]],
        },
    )
    assert response.status_code == 201
    assert response.json()["action_plan"]["meeting"] is None
    status = client.get(
        f"/requests/{created['id']}/status", headers=headers
    ).json()
    assert status["status"] == "action_planned"
    assert status["meeting_title"] is None
