import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import professor_auth, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_unauthenticated_agent_and_stamp_are_rejected():
    assert client.post("/agent/ask", json={"question": "What is hashing?", "course_id": 1}).status_code == 401
    assert client.post("/requests/", json={"text": "help", "anonymous": True, "course_id": 1}).status_code == 401
    assert client.patch("/knowledge/1", json={"status": "approved"}).status_code == 401
    assert client.get("/analytics/struggle-heatmap").status_code == 401


def test_create_request_seeds_pending_knowledge_entry():
    headers, course_id = student_auth(client)
    response = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "I am confused about recursion and binary search base cases.",
            "anonymous": True,
            "course_id": course_id,
            "course": "CSC 3374",
        },
    )
    assert response.status_code == 201
    request = response.json()
    assert request["urgency"] in {"low", "medium", "high", "urgent"}

    prof_headers, _ = professor_auth(client, "CSC 3374")
    entries = client.get(
        f"/knowledge/?status=pending_review&course_id={course_id}",
        headers=prof_headers,
    ).json()
    assert len(entries) == 1
    assert entries[0]["source_request_id"] == request["id"]
    assert entries[0]["status"] == "pending_review"
    assert entries[0]["student_hint"]
    assert entries[0]["answer_draft"]


def test_agent_only_uses_approved_entries():
    student_headers, course_id = student_auth(client)
    created = client.post(
        "/requests/",
        headers=student_headers,
        json={
            "text": "Please explain recursion tracing with binary search.",
            "anonymous": True,
            "course_id": course_id,
            "course": "CSC 3374",
        },
    ).json()
    assert created["id"]

    prof_headers, _ = professor_auth(client, "CSC 3374")
    pending = client.get(
        f"/knowledge/?status=pending_review&course_id={course_id}",
        headers=prof_headers,
    ).json()
    entry_id = pending[0]["id"]

    blocked = client.post(
        "/agent/ask",
        headers=student_headers,
        json={
            "question": "How does recursion work with binary search?",
            "course_id": course_id,
        },
    ).json()
    assert blocked["matched_count"] == 0
    assert blocked["should_seek_help"] is True
    assert "quiet ask" in blocked["answer"].lower()

    approved = client.patch(
        f"/knowledge/{entry_id}",
        headers=prof_headers,
        json={
            "status": "approved",
            "answer_draft": (
                "Teaching approach: start from the base case, then show how each "
                "recursive call halves the search space."
            ),
            "student_hint": "Think about what happens when the search range becomes empty.",
            "professor_note": "Canonical recursion FAQ",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    answered = client.post(
        "/agent/ask",
        headers=student_headers,
        json={
            "question": "Can you help with recursion and binary search?",
            "course_id": course_id,
        },
    ).json()
    assert answered["matched_count"] >= 1
    assert answered["should_seek_help"] is False
    assert "base case" in answered["answer"].lower()


def test_kb_miss_encourages_quiet_ask_not_guessing():
    headers, course_id = student_auth(client)
    response = client.post(
        "/agent/ask",
        headers=headers,
        json={
            "question": "What is the midterm date for quantum blockchain yoga?",
            "course_id": course_id,
        },
    ).json()
    assert response["matched_count"] == 0
    assert response["should_seek_help"] is True
    assert "quiet ask" in response["answer"].lower()


def test_reject_keeps_entry_out_of_agent():
    student_headers, course_id = student_auth(client)
    client.post(
        "/requests/",
        headers=student_headers,
        json={
            "text": "Explain dynamic programming memoization.",
            "anonymous": True,
            "course_id": course_id,
            "course": "CSC 3374",
        },
    )
    prof_headers, _ = professor_auth(client, "CSC 3374")
    entry_id = client.get(
        f"/knowledge/?status=pending_review&course_id={course_id}",
        headers=prof_headers,
    ).json()[0]["id"]
    client.patch(
        f"/knowledge/{entry_id}",
        headers=prof_headers,
        json={"status": "rejected"},
    )

    response = client.post(
        "/agent/ask",
        headers=student_headers,
        json={
            "question": "How does memoization work in dynamic programming?",
            "course_id": course_id,
        },
    ).json()
    assert response["matched_count"] == 0


def test_struggle_heatmap_and_escalations():
    headers, course_id = student_auth(client)
    for text in (
        "I need help understanding recursion.",
        "Can we review recursion again?",
        "Still confused about recursion base cases.",
    ):
        client.post(
            "/requests/",
            headers=headers,
            json={"text": text, "anonymous": True, "course_id": course_id, "course": "CSC 3374"},
        )

    prof_headers, _ = professor_auth(client, "CSC 3374")
    heatmap = client.get(
        f"/analytics/struggle-heatmap?course_id={course_id}",
        headers=prof_headers,
    ).json()
    assert heatmap["total_requests"] == 3
    assert any(cell["count"] >= 1 for cell in heatmap["cells"])

    escalations = client.get(
        f"/analytics/escalations?course_id={course_id}",
        headers=prof_headers,
    ).json()
    assert isinstance(escalations, list)
