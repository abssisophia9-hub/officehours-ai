import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ.pop("CANVAS_BASE_URL", None)
os.environ.pop("CANVAS_ACCESS_TOKEN", None)

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import DEMO_PASSWORD


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _professor_client():
    client = TestClient(app)
    login = client.post(
        "/auth/login",
        json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    course_id = next(
        c["id"] for c in login.json()["user"]["courses"] if c["code"] == "CS 400"
    )
    return client, token, course_id


def test_canvas_sync_feeds_course_kb_agent():
    client, token, course_id = _professor_client()
    headers = {"Authorization": f"Bearer {token}"}

    status = client.get(
        f"/knowledge/canvas/status?course_id={course_id}",
        headers=headers,
    )
    assert status.status_code == 200
    body = status.json()
    assert body["mode"] == "local"
    assert body["canvas_course_id"] == "4001"
    assert len(body["available_files"]) >= 1

    sync = client.post(
        "/knowledge/canvas/sync",
        headers=headers,
        json={"course_id": course_id, "auto_approve": True},
    )
    assert sync.status_code == 201
    payload = sync.json()
    assert payload["chunks_created"] >= 1
    assert payload["files_seen"] >= 1

    # Second sync should skip already-imported Canvas files.
    again = client.post(
        "/knowledge/canvas/sync",
        headers=headers,
        json={"course_id": course_id, "auto_approve": True},
    )
    assert again.status_code == 201
    assert again.json()["chunks_created"] == 0
    assert len(again.json()["skipped"]) >= 1

    answer = client.post(
        "/agent/ask",
        json={
            "question": "How do hash tables handle collisions?",
            "course_id": course_id,
        },
    )
    assert answer.status_code == 200
    data = answer.json()
    assert data["matched_count"] >= 1
    assert "collision" in data["answer"].lower() or "chaining" in data["answer"].lower()


def test_materials_require_professor_auth_and_strict_course_scope():
    client, token, course_id = _professor_client()
    headers = {"Authorization": f"Bearer {token}"}

    denied = client.post(
        "/knowledge/materials",
        json={
            "title": "Nope",
            "content": "This should fail without a bearer token for professor ingest.",
            "course_id": course_id,
            "source": "slides",
        },
    )
    assert denied.status_code == 401

    ingest = client.post(
        "/knowledge/materials",
        headers=headers,
        json={
            "title": "Week 4 Hashing",
            "content": (
                "Hash tables map keys to buckets.\n\n"
                "Collisions are handled with chaining or open addressing.\n\n"
                "Chaining stores a linked list in each bucket."
            ),
            "course_id": course_id,
            "course": "CS 400",
            "source": "slides",
            "auto_approve": True,
        },
    )
    assert ingest.status_code == 201
    assert ingest.json()["chunks_created"] >= 1

    # Other course should not see CS 400 materials when scoped.
    other = next(
        c["id"]
        for c in client.get("/auth/me", headers=headers).json()["courses"]
        if c["code"] == "CS 330"
    )
    miss = client.post(
        "/agent/ask",
        json={"question": "How do hash tables handle collisions?", "course_id": other},
    ).json()
    assert miss["matched_count"] == 0

    hit = client.post(
        "/agent/ask",
        json={
            "question": "How do hash tables handle collisions?",
            "course_id": course_id,
        },
    ).json()
    assert hit["matched_count"] >= 1


def test_student_cannot_sync_canvas():
    client = TestClient(app)
    login = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": DEMO_PASSWORD},
    )
    token = login.json()["token"]
    course_id = login.json()["user"]["courses"][0]["id"]
    response = client.post(
        "/knowledge/canvas/sync",
        headers={"Authorization": f"Bearer {token}"},
        json={"course_id": course_id, "auto_approve": True},
    )
    assert response.status_code == 403
