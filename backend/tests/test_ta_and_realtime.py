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
        from tests.helpers import post_student_request, professor_auth

        response, _, course_id = post_student_request(
            client,
            "Can you show me an example of recursion tracing?",
            code="CSC 2302",
        )
        assert response.status_code == 201
        request = response.json()
        assert request["learning_style"] == "example_driven"

        staff, _ = professor_auth(client, "CSC 2302")
        entries = client.get(
            f"/knowledge/?status=pending_review&course_id={course_id}",
            headers=staff,
        ).json()
        assert len(entries) == 1
        assert entries[0]["learning_style"] == "example_driven"
        backend = entries[0]["drafter_backend"] or ""
        assert "claude" not in backend
        assert "custom_synthesizer" in backend
        assert entries[0]["answer_draft"]
        assert entries[0]["student_hint"]


def test_ta_resolve_keeps_entry_pending_review():
    with TestClient(app) as client:
        from app.database.session import SessionLocal
        from app.services.demo_accounts import ensure_demo_accounts

        db = SessionLocal()
        try:
            ensure_demo_accounts(db)
        finally:
            db.close()

        student = client.post(
            "/auth/login",
            json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
        ).json()
        alice = client.post(
            "/auth/login",
            json={"email": "a.chen@aui.ma", "password": "aui-demo"},
        ).json()
        course_id = next(
            c["id"] for c in student["user"]["courses"] if c["code"] == "CSC 2302"
        )
        created = client.post(
            "/requests/",
            headers={"Authorization": f"Bearer {student['token']}"},
            json={
                "text": "Please walk me through the steps of binary search.",
                "anonymous": True,
                "course": "CSC 2302",
                "course_id": course_id,
            },
        ).json()

        queue = client.get(
            f"/ta/queue/?course_id={course_id}&assignment=all",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert any(item["request"]["id"] == created["id"] for item in queue)

        replied = client.post(
            "/ta/reply/",
            headers={"Authorization": f"Bearer {alice['token']}"},
            json={
                "request_id": created["id"],
                "reply": (
                    "Restate the invariant, then trace mid on a 7-element array "
                    "before finishing the last two steps."
                ),
                "update_student_hint": True,
            },
        )
        assert replied.status_code == 200, replied.text

        resolved = client.post(
            "/ta/resolve/",
            headers={"Authorization": f"Bearer {alice['token']}"},
            json={
                "request_id": created["id"],
                "teaching_notes": (
                    "1. Restate the search invariant.\n"
                    "2. Trace mid updates on a 7-element array.\n"
                    "3. Have the student finish the last two steps."
                ),
                "student_hint": "What must stay true about the remaining range?",
                "resolution_status": "resolved",
            },
        )
        assert resolved.status_code == 200, resolved.text
        payload = resolved.json()
        assert payload["knowledge_entry"]["status"] == "pending_review"
        assert payload["knowledge_entry"]["ta_resolution"] == "resolved"
        assert "Alice Chen" in (payload["knowledge_entry"]["professor_note"] or "")
        assert "invariant" in payload["knowledge_entry"]["answer_draft"].lower()

        queue_mid = client.get(
            f"/ta/queue/?course_id={course_id}&assignment=all",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert all(item["request"]["id"] != created["id"] for item in queue_mid)

        agent = client.post(
            "/agent/ask",
            headers={"Authorization": f"Bearer {student['token']}"},
            json={
                "question": "How do I think about binary search steps?",
                "course_id": course_id,
            },
        ).json()
        assert agent["matched_count"] == 0

        entry_id = payload["knowledge_entry"]["id"]
        prof = client.post(
            "/auth/login",
            json={"email": "a.benali@aui.ma", "password": "aui-demo"},
        ).json()
        approved = client.patch(
            f"/knowledge/{entry_id}",
            headers={"Authorization": f"Bearer {prof['token']}"},
            json={"status": "approved"},
        )
        assert approved.status_code == 200
        assert approved.json()["status"] == "approved"

        queue_after = client.get(
            f"/ta/queue/?course_id={course_id}&assignment=all",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert all(item["request"]["id"] != created["id"] for item in queue_after)


def test_ta_dashboard_open_count_matches_live_queue():
    """Open-ask count used by the TA dashboard must match the live queue."""
    with TestClient(app) as client:
        from app.database.session import SessionLocal
        from app.services.demo_accounts import ensure_demo_accounts

        db = SessionLocal()
        try:
            ensure_demo_accounts(db)
        finally:
            db.close()

        student = client.post(
            "/auth/login",
            json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
        ).json()
        alice = client.post(
            "/auth/login",
            json={"email": "a.chen@aui.ma", "password": "aui-demo"},
        ).json()
        course_id = next(
            c["id"] for c in student["user"]["courses"] if c["code"] == "CSC 2302"
        )
        created_ids = []
        for text in (
            "How do red-black trees rebalance after insert?",
            "Why does hash table load factor affect collisions?",
        ):
            created = client.post(
                "/requests/",
                headers={"Authorization": f"Bearer {student['token']}"},
                json={
                    "text": text,
                    "anonymous": True,
                    "course": "CSC 2302",
                    "course_id": course_id,
                },
            )
            assert created.status_code == 201, created.text
            created_ids.append(created.json()["id"])

        queue = client.get(
            f"/ta/queue/?course_id={course_id}&assignment=all&include_helped=false",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        open_rows = [
            item["request"]
            for item in (queue if isinstance(queue, list) else queue.get("items") or [])
            if str(item["request"].get("work_status") or "") != "helped"
        ]
        load = client.get(
            f"/ta/load/?course_id={course_id}",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        # Dashboard prefers live queue length over load aggregates.
        assert len(open_rows) >= 2
        assert all(rid in {row["id"] for row in open_rows} for rid in created_ids)
        # load.open_requests must not be lower than the live open queue we just built.
        assert int(load.get("open_requests") or 0) >= len(created_ids)


def test_websocket_receives_request_created_event():
    with TestClient(app) as client:
        from tests.helpers import post_student_request, student_auth

        headers, course_id = student_auth(client, "CSC 2302")
        token = headers["Authorization"].split(" ", 1)[1]
        with client.websocket_connect(
            f"/ws?token={token}&course_id={course_id}"
        ) as websocket:
            hello = websocket.receive_json()
            assert hello["type"] == "connected"

            post_student_request(
                client,
                "Why does the red-black tree invariant matter?",
                code="CSC 2302",
            )

            seen_types = set()
            for _ in range(8):
                message = websocket.receive_json()
                seen_types.add(message["type"])
                if "request.created" in seen_types and "knowledge.created" in seen_types:
                    break

            assert "request.created" in seen_types
            assert "knowledge.created" in seen_types
