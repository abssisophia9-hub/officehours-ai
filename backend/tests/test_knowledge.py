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


def test_create_request_seeds_pending_knowledge_entry():
    response = client.post(
        "/requests/",
        json={
            "text": "I am confused about recursion and binary search base cases.",
            "anonymous": True,
        },
    )
    assert response.status_code == 201
    request = response.json()
    assert request["urgency"] in {"low", "medium", "high", "urgent"}

    entries = client.get("/knowledge/?status=pending_review").json()
    assert len(entries) == 1
    assert entries[0]["source_request_id"] == request["id"]
    assert entries[0]["status"] == "pending_review"
    assert entries[0]["student_hint"]
    assert entries[0]["answer_draft"]


def test_agent_only_uses_approved_entries():
    created = client.post(
        "/requests/",
        json={
            "text": "Please explain recursion tracing with binary search.",
            "anonymous": True,
        },
    ).json()

    pending = client.get("/knowledge/?status=pending_review").json()
    entry_id = pending[0]["id"]

    # Pending drafts must not answer students.
    blocked = client.post(
        "/agent/ask",
        json={"question": "How does recursion work with binary search?"},
    ).json()
    assert blocked["matched_count"] == 0
    assert "do not have a professor-approved answer" in blocked["answer"].lower()

    approved = client.patch(
        f"/knowledge/{entry_id}",
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
    assert approved.json()["reviewed_at"] is not None

    answered = client.post(
        "/agent/ask",
        json={"question": "Can you help with recursion and binary search?"},
    ).json()
    assert answered["matched_count"] >= 1
    assert answered["used_approved_kb_only"] is True
    assert "base case" in answered["answer"].lower()
    assert answered["sources"][0]["entry"]["id"] == entry_id
    assert answered["student_hint"]


def test_reject_keeps_entry_out_of_agent():
    client.post(
        "/requests/",
        json={"text": "Explain dynamic programming memoization.", "anonymous": True},
    )
    entry_id = client.get("/knowledge/").json()[0]["id"]
    client.patch(f"/knowledge/{entry_id}", json={"status": "rejected"})

    response = client.post(
        "/agent/ask",
        json={"question": "How does memoization work in dynamic programming?"},
    ).json()
    assert response["matched_count"] == 0


def test_struggle_heatmap_and_escalations():
    for text in (
        "I need help understanding recursion.",
        "Can we review recursion again?",
        "Still confused about recursion base cases.",
    ):
        client.post("/requests/", json={"text": text, "anonymous": True})

    heatmap = client.get("/analytics/struggle-heatmap").json()
    assert heatmap["total_requests"] == 3
    assert any(cell["count"] >= 1 for cell in heatmap["cells"])

    escalations = client.get("/analytics/escalations").json()
    assert isinstance(escalations, list)
    assert any("Recurring topic" in item["reason"] for item in escalations)
