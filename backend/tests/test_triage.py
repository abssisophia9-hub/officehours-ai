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


def test_triage_pipeline_on_red_black_submission():
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
        response = client.post(
            "/requests/",
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
        triage = data["triage"] or data["oracle"]
        assert triage is not None
        assert data["triage"] is not None
        assert data["oracle"] is not None  # legacy alias
        assert "Red-Black" in triage["analyzer"]["category"]
        assert triage["analyzer"]["difficulty"] in {"EASY", "MEDIUM", "HARD"}
        assert "trees" in triage["analyzer"]["tags"] or "red-black" in triage[
            "analyzer"
        ]["tags"]
        assert triage["matcher"]["assigned_ta"] == "Alice Chen"
        assert triage["matcher"]["alternative_ta"]
        assert triage["synthesizer"]["student_hint"]
        assert triage["synthesizer"]["teaching_approach"]
        assert data["assigned_ta"] == "Alice Chen"
        assert triage["elapsed_ms"] is not None
        assert {step["agent"] for step in triage["steps"]} == {
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

        metrics = client.get("/analytics/triage-metrics").json()
        assert (metrics.get("triage_runs") or metrics.get("oracle_runs")) >= 1
        assert metrics["matched_assignments"] >= 1
        assert metrics["time_saved_minutes"] >= 0
        legacy = client.get("/analytics/oracle-metrics").json()
        assert legacy["oracle_runs"] == metrics["triage_runs"]

        roster = client.get(
            "/ta/roster/",
            headers={"Authorization": f"Bearer {alice['token']}"},
        ).json()
        assert any(ta["name"] == "Alice Chen" for ta in roster)


def test_lifetime_confusion_uses_approved_kb_only():
    with TestClient(app) as client:
        created = client.post(
            "/requests/",
            json={
                "text": "Please explain red-black tree rotations after deletion.",
                "anonymous": True,
                "course": "CSC 2302",
            },
        ).json()
        entries = client.get("/knowledge/?status=pending_review").json()
        entry = next(
            item for item in entries if item["source_request_id"] == created["id"]
        )
        client.patch(f"/knowledge/{entry['id']}", json={"status": "approved"})

        lifetime = client.get("/analytics/lifetime-confusion").json()
        assert lifetime["topics"]
        assert any(
            "Red-Black" in topic["topic"] or "tree" in topic["topic"].lower()
            for topic in lifetime["topics"]
        ) or lifetime["topics"][0]["approved_count"] >= 1
