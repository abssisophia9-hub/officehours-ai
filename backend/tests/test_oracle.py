import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ANALYZER_BACKEND"] = "ml"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_oracle_pipeline_on_red_black_submission():
    with TestClient(app) as client:
        from app.database.session import SessionLocal
        from app.services.demo_accounts import ensure_demo_accounts

        db = SessionLocal()
        try:
            ensure_demo_accounts(db)
        finally:
            db.close()

        alice = client.post(
            "/auth/login",
            json={"email": "a.chen@aui.ma", "password": "aui-demo"},
        ).json()
        course_id = next(
            c["id"] for c in alice["user"]["courses"] if c["code"] == "CSC 2302"
        )
        student = client.post(
            "/auth/login",
            json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
        ).json()
        response = client.post(
            "/requests/",
            headers={"Authorization": f"Bearer {student['token']}"},
            json={
                "text": (
                    "I'm getting infinite recursion in my red-black tree delete "
                    "fixup. The parent pointer seems correct but rotation isn't "
                    "balancing properly."
                ),
                "anonymous": False,
                "student_id": "117400",
                "student_name": "Alex Smith",
                "course": "CSC 2302",
                "course_id": course_id,
                "code_snippet": (
                    "def delete_fixup(self, node):\n"
                    "    while node != self.root and node.color == BLACK:\n"
                    "        if node == node.parent.left:\n"
                    "            sibling = node.parent.right\n"
                ),
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["student_name"] == "Alex Smith"
        assert data["course"] == "CSC 2302"
        assert data["code_snippet"]
        assert data["oracle"] is not None
        assert "Red-Black" in data["oracle"]["analyzer"]["category"]
        assert data["oracle"]["analyzer"]["difficulty"] in {"EASY", "MEDIUM", "HARD"}
        assert "trees" in data["oracle"]["analyzer"]["tags"] or "red-black" in data[
            "oracle"
        ]["analyzer"]["tags"]
        assert data["oracle"]["matcher"]["assigned_ta"] == "Alice Chen"
        assert data["oracle"]["matcher"]["alternative_ta"]
        assert data["oracle"]["synthesizer"]["student_hint"]
        assert data["oracle"]["synthesizer"]["teaching_approach"]
        assert data["assigned_ta"] == "Alice Chen"
        assert data["oracle"]["elapsed_ms"] is not None
        assert {step["agent"] for step in data["oracle"]["steps"]} == {
            "analyzer",
            "matcher",
            "synthesizer",
        }
        assert data["category"] in {
            "conceptual_question",
            "project_submission",
            "uncategorized",
        }

        queue = client.get(
            f"/ta/queue/?course_id={course_id}&assignment=all",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert any(item["request"]["id"] == data["id"] for item in queue)
        item = next(item for item in queue if item["request"]["id"] == data["id"])
        assert item["request"]["assigned_ta"] == "Alice Chen"
        assert item["knowledge_entry"]["student_hint"]
        assert "claude" not in (item["knowledge_entry"].get("drafter_backend") or "")

        metrics = client.get(
            "/analytics/oracle-metrics",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert metrics["oracle_runs"] >= 1
        assert metrics["matched_assignments"] >= 1
        assert metrics["time_saved_minutes"] >= 0

        roster = client.get(
            "/ta/roster/",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert any(ta["name"] == "Alice Chen" for ta in roster)


def test_lifetime_confusion_uses_approved_kb_only():
    with TestClient(app) as client:
        from tests.helpers import post_student_request, professor_auth

        created, _, course_id = post_student_request(
            client,
            "Please explain red-black tree rotations after deletion.",
            code="CSC 2302",
        )
        created = created.json()
        staff, _ = professor_auth(client, "CSC 2302")
        entries = client.get(
            f"/knowledge/?status=pending_review&course_id={course_id}",
            headers=staff,
        ).json()
        entry = next(
            item for item in entries if item["source_request_id"] == created["id"]
        )
        client.patch(
            f"/knowledge/{entry['id']}",
            headers=staff,
            json={"status": "approved"},
        )

        lifetime = client.get("/analytics/lifetime-confusion", headers=staff).json()
        assert lifetime["topics"]
        assert any(
            "Red-Black" in topic["topic"] or "tree" in topic["topic"].lower()
            for topic in lifetime["topics"]
        ) or lifetime["topics"][0]["approved_count"] >= 1
