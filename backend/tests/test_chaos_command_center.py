"""Tests for office-hours chaos command center features."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _post(text, *, course="CSC 2302", course_id=1, anonymous=True, **extra):
    payload = {
        "text": text,
        "anonymous": anonymous,
        "course": course,
        "course_id": course_id,
        **extra,
    }
    response = client.post("/requests/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_course_scoped_clustering_groups_repeats():
    first = _post("I am stuck on binary search high bound for the last element.")
    second = _post("Binary search fails on the last array element — high bound wrong?")
    other_course = _post(
        "Binary search fails on the last array element — high bound wrong?",
        course="CSC 3323",
        course_id=2,
    )
    assert first["cluster_id"] == second["cluster_id"]
    # Same wording in another course should not join CSC 2302 cluster space for new IDs
    # (may share numeric id by coincidence if both start at 1 — verify via analytics)
    cs2302 = client.get("/analytics/clusters?course_id=1&course=CSC%202302")
    assert cs2302.status_code == 200
    body = cs2302.json()
    assert body["total_requests"] == 2
    assert any(cluster["request_count"] >= 2 for cluster in body["clusters"])
    assert other_course["course"] == "CSC 3323"


def test_faq_from_cluster_and_group_suggestion():
    _post("How do hash tables handle collisions with chaining?")
    _post("Hash table collisions and chaining explanation please")
    _post("Hash tables collisions chaining — what happens in each bucket?")
    clusters = client.get("/analytics/clusters?course=CSC%202302").json()["clusters"]
    assert clusters
    target = max(clusters, key=lambda item: item["request_count"])
    assert target["request_count"] >= 2
    assert target["suggested_action"] in {"group_session", "faq"}

    faq = client.post(
        "/knowledge/from-cluster",
        json={"cluster_id": target["cluster_id"], "course": "CSC 2302", "course_id": 1},
    )
    assert faq.status_code == 201
    data = faq.json()
    assert data["status"] == "pending_review"
    assert "FAQ" in data["question_text"]
    assert data["cluster_id"] == target["cluster_id"]


def test_course_material_ingest_feeds_kb_agent():
    from app.services.demo_accounts import DEMO_PASSWORD

    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    course_id = next(
        c["id"] for c in login.json()["user"]["courses"] if c["code"] == "CSC 2302"
    )

    ingest = client.post(
        "/knowledge/materials",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Week 4 Hashing",
            "content": (
                "Hash tables map keys to buckets.\n\n"
                "Collisions are handled with chaining or open addressing.\n\n"
                "Chaining stores a linked list in each bucket."
            ),
            "course_id": course_id,
            "course": "CSC 2302",
            "source": "slides",
            "auto_approve": True,
        },
    )
    assert ingest.status_code == 201
    assert ingest.json()["chunks_created"] >= 1

    answer = client.post(
        "/agent/ask",
        json={
            "question": "How do hash tables handle collisions?",
            "course_id": course_id,
        },
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["matched_count"] >= 1
    assert "collision" in body["answer"].lower() or "chaining" in body["answer"].lower()


def test_anonymous_strips_identity_and_sensitive_flags():
    created = _post(
        "I am overwhelmed and panicking about failing the class, need help privately.",
        anonymous=True,
        student_id="should-not-persist",
        student_name="Hidden Student",
    )
    assert created["anonymous"] is True
    assert created["student_id"] is None
    assert created["student_name"] is None
    assert created["sensitive"] is True
    assert "private" in (created["recommended_action"] or "").lower()

    escalations = client.get("/analytics/escalations?course=CSC%202302").json()
    assert any(item["sensitive"] for item in escalations)
