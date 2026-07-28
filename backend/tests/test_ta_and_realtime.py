import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_create_request_infers_learning_style_and_drafts():
    with TestClient(app) as client:
        response = client.post(
            "/requests/",
            json={
                "text": "Can you show me an example of recursion tracing?",
                "anonymous": True,
            },
        )
        assert response.status_code == 201
        request = response.json()
        assert request["learning_style"] == "example_driven"

        entries = client.get("/knowledge/?status=pending_review").json()
        assert len(entries) == 1
        assert entries[0]["learning_style"] == "example_driven"
        backend = entries[0]["drafter_backend"] or ""
        assert "claude" not in backend
        assert "custom_synthesizer" in backend
        assert entries[0]["answer_draft"]
        assert entries[0]["student_hint"]


def test_ta_resolve_keeps_entry_pending_review():
    with TestClient(app) as client:
        created = client.post(
            "/requests/",
            json={
                "text": "Please walk me through the steps of binary search.",
                "anonymous": True,
            },
        ).json()

        queue = client.get("/ta/queue/").json()
        assert any(item["request"]["id"] == created["id"] for item in queue)

        resolved = client.post(
            "/ta/resolve/",
            json={
                "request_id": created["id"],
                "ta_name": "Alice Chen",
                "teaching_notes": (
                    "1. Restate the search invariant.\n"
                    "2. Trace mid updates on a 7-element array.\n"
                    "3. Have the student finish the last two steps."
                ),
                "student_hint": "What must stay true about the remaining range?",
                "resolution_status": "resolved",
            },
        )
        assert resolved.status_code == 200
        payload = resolved.json()
        assert payload["knowledge_entry"]["status"] == "pending_review"
        assert payload["knowledge_entry"]["ta_resolution"] == "resolved"
        assert "Alice Chen" in (payload["knowledge_entry"]["professor_note"] or "")
        assert "invariant" in payload["knowledge_entry"]["answer_draft"].lower()

        # A TA-resolved item leaves the active queue immediately — it is
        # waiting on the professor, not on another TA.
        queue_mid = client.get("/ta/queue/").json()
        assert all(item["request"]["id"] != created["id"] for item in queue_mid)

        agent = client.post(
            "/agent/ask",
            json={"question": "How do I think about binary search steps?"},
        ).json()
        assert agent["matched_count"] == 0

        entry_id = payload["knowledge_entry"]["id"]
        approved = client.patch(
            f"/knowledge/{entry_id}",
            json={"status": "approved"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        queue_after = client.get("/ta/queue/").json()
        assert all(item["request"]["id"] != created["id"] for item in queue_after)


def test_websocket_receives_request_created_event():
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            hello = websocket.receive_json()
            assert hello["type"] == "connected"

            client.post(
                "/requests/",
                json={
                    "text": "Why does the red-black tree invariant matter?",
                    "anonymous": True,
                },
            )

            seen_types = set()
            for _ in range(5):
                message = websocket.receive_json()
                seen_types.add(message["type"])
                if "request.created" in seen_types and "knowledge.created" in seen_types:
                    break

            assert "request.created" in seen_types
            assert "knowledge.created" in seen_types
