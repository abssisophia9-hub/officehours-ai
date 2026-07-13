import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["USE_MOCK_CLAUDE"] = "true"
os.environ["OFFICEHOURS_ANALYZER_BACKEND"] = "ml"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_oracle_pipeline_on_red_black_submission():
    with TestClient(app) as client:
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
                "course": "CS 400",
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
        assert data["course"] == "CS 400"
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

        queue = client.get("/ta/queue/").json()
        assert any(item["request"]["id"] == data["id"] for item in queue)
        item = next(item for item in queue if item["request"]["id"] == data["id"])
        assert item["request"]["assigned_ta"] == "Alice Chen"
        assert item["knowledge_entry"]["student_hint"]

        metrics = client.get("/analytics/oracle-metrics").json()
        assert metrics["oracle_runs"] >= 1
        assert metrics["matched_assignments"] >= 1
        assert metrics["time_saved_minutes"] >= 0

        roster = client.get("/ta/roster/").json()
        assert any(ta["name"] == "Alice Chen" for ta in roster)


def test_lifetime_confusion_uses_approved_kb_only():
    with TestClient(app) as client:
        created = client.post(
            "/requests/",
            json={
                "text": "Please explain red-black tree rotations after deletion.",
                "anonymous": True,
                "course": "CS 400",
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
