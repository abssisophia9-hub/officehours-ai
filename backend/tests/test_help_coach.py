"""Help Coach — TA co-pilot while helping."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def _login(email: str) -> str:
    return client.post(
        "/auth/login",
        json={"email": email, "password": "aui-demo"},
    ).json()["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _csc2302(token: str) -> int:
    me = client.get("/auth/me", headers=_auth(token)).json()
    return next(c["id"] for c in me["courses"] if c["code"] == "CSC 2302")


def test_queue_includes_help_coach_and_similar_badge():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    first = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Red-black tree delete fixup loops forever after rotating uncle.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    second = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "My red-black deletion fixup never terminates on uncle rotation.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()

    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    by_id = {item["request"]["id"]: item for item in queue}
    assert first["id"] in by_id
    assert second["id"] in by_id

    coach = by_id[first["id"]]["help_coach"]
    assert coach is not None
    assert coach["teaching_approach"]
    assert isinstance(coach["socratic_steps"], list)
    assert len(coach["socratic_steps"]) >= 1
    # Same category / cluster should surface a similar-open cue.
    assert coach["similar_open_count"] >= 1
    assert any(peer["id"] == second["id"] for peer in coach["similar_open"])


def test_assist_draft_reply_socratic_and_rewrite():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Hash table open addressing vs chaining — when does clustering hurt?",
            "anonymous": False,
            "student_name": "Sara",
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    rid = created["id"]

    assert client.post("/ta/assist/", json={"request_id": rid}).status_code == 401

    draft = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "draft_reply"},
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    assert body["mode"] == "draft_reply"
    assert body["draft_reply"]
    assert "hash" in body["draft_reply"].lower() or "path" in body["draft_reply"].lower()
    assert body["help_coach"]["socratic_steps"]

    socratic = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "socratic", "focus": "clustering"},
    ).json()
    assert socratic["mode"] == "socratic"
    assert any("clustering" in step.lower() for step in socratic["socratic_steps"])

    rewrite = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "mode": "rewrite_reply",
            "current_reply": "Try chaining first then open addressing.",
        },
    ).json()
    assert rewrite["mode"] == "rewrite_reply"
    assert rewrite["draft_reply"]
    assert "chaining" in rewrite["draft_reply"].lower()


def test_refresh_teaching_updates_pending_draft():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Explain AVL rotations after a double imbalance on insert.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    rid = created["id"]

    refreshed = client.post(
        "/ta/assist/",
        headers=_auth(alice),
        json={"request_id": rid, "mode": "refresh_teaching"},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["teaching_approach"]

    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    item = next(row for row in queue if row["request"]["id"] == rid)
    assert item["knowledge_entry"] is not None
    assert item["knowledge_entry"]["answer_draft"]
    assert item["help_coach"]["teaching_approach"]


def test_student_cannot_use_help_coach_on_other_course():
    """Sara is student-only on CSC 2302 — assist must reject."""
    student = _login("s.elidrissi@aui.ma")
    course_id = _csc2302(student)
    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Quick BST height question for coach auth check.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    denied = client.post(
        "/ta/assist/",
        headers=_auth(student),
        json={"request_id": created["id"], "mode": "draft_reply"},
    )
    assert denied.status_code in {403, 401}
