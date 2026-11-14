"""TA staffing loop: claim, help, reply, backup handoff, auth."""

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


def test_ta_queue_requires_auth_and_course():
    assert client.get("/ta/queue/").status_code == 401
    token = _login("a.chen@aui.ma")
    assert (
        client.get("/ta/queue/", headers=_auth(token)).status_code == 422
    )


def test_claim_in_progress_helped_and_reply():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Walk me through open addressing vs chaining step by step.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    rid = created["id"]

    claimed = client.post(
        "/ta/claim/",
        headers=_auth(alice),
        json={"request_id": rid},
    )
    assert claimed.status_code == 200, claimed.text
    assert claimed.json()["request"]["work_status"] == "claimed"
    assert claimed.json()["request"]["claimed_by"] == "Alice Chen"

    released = client.post(
        "/ta/work-status/",
        headers=_auth(alice),
        json={"request_id": rid, "status": "open"},
    )
    assert released.status_code == 200, released.text
    assert released.json()["request"]["work_status"] == "open"
    assert not released.json()["request"]["claimed_by"]
    assert released.json()["request"]["claimed_by_user_id"] is None

    reclaimed = client.post(
        "/ta/claim/",
        headers=_auth(alice),
        json={"request_id": rid},
    )
    assert reclaimed.status_code == 200, reclaimed.text

    started = client.post(
        "/ta/work-status/",
        headers=_auth(alice),
        json={"request_id": rid, "status": "in_progress"},
    ).json()
    assert started["request"]["work_status"] == "in_progress"

    replied = client.post(
        "/ta/reply/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "reply": "Start with chaining — each slot holds a list of collisions.",
        },
    )
    assert replied.status_code == 200, replied.text
    assert "chaining" in replied.json()["request"]["ta_reply"].lower()

    status = client.get(f"/requests/{rid}/status", headers=_auth(student)).json()
    assert status["status"] == "ta_replied"
    assert "chaining" in (status["ta_reply"] or "").lower()
    assert "chaining" in (status["message"] or "").lower()

    helped = client.post(
        "/ta/work-status/",
        headers=_auth(alice),
        json={"request_id": rid, "status": "helped"},
    ).json()
    assert helped["request"]["work_status"] == "helped"

    # Helped asks leave the default open queue.
    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    assert all(item["request"]["id"] != rid for item in queue)


def test_resolve_without_reply_rejected_with_reply_ok():
    """New resolves require ta_reply (422); resolve after /ta/reply succeeds."""
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Walk me through how hash collisions are resolved with chaining.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
            "help_mode": "message",
        },
    ).json()
    rid = created["id"]

    claim = client.post(
        "/ta/claim/",
        headers=_auth(alice),
        json={"request_id": rid},
    )
    assert claim.status_code == 200, claim.text

    notes = (
        "1. Define the slot as a list.\n"
        "2. Trace insert under collision.\n"
        "3. Have the student finish lookup."
    )
    blocked = client.post(
        "/ta/resolve/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "teaching_notes": notes,
            "resolution_status": "resolved",
        },
    )
    assert blocked.status_code == 422, blocked.text
    assert "reply" in (blocked.json().get("detail") or "").lower()

    replied = client.post(
        "/ta/reply/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "reply": "Each bucket holds a list — walk insert, then lookup on a collision.",
        },
    )
    assert replied.status_code == 200, replied.text

    resolved = client.post(
        "/ta/resolve/",
        headers=_auth(alice),
        json={
            "request_id": rid,
            "teaching_notes": notes,
            "student_hint": "Where does the colliding key live after insert?",
            "resolution_status": "resolved",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["knowledge_entry"]["status"] == "pending_review"
    assert resolved.json()["knowledge_entry"]["ta_resolution"] == "resolved"


def test_backup_takeover_and_resolve_auth():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    bob = _login("b.martinez@aui.ma")
    course_id = _csc2302(student)

    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Red-black deletion fixup rotations confuse me.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    rid = created["id"]
    # Force Alice primary / Bob backup for a deterministic handoff.
    # If matcher already set them, use backup path; else claim as Alice then Bob takes.
    if created.get("alternative_ta") != "Bob Martinez":
        client.post("/ta/claim/", headers=_auth(alice), json={"request_id": rid})

    # Ensure Bob is backup: if Alice claimed as primary, Bob take-backup should work
    # only if he's listed as backup OR unassigned. Re-fetch queue as bob.
    # Manually set via claim as alice then bob take if he's backup.
    body = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    row = next(item for item in body if item["request"]["id"] == rid)
    primary = row["request"]["assigned_ta"]
    backup = row["request"]["alternative_ta"]

    if backup == "Bob Martinez":
        handoff = client.post(
            "/ta/take-backup/",
            headers=_auth(bob),
            json={"request_id": rid},
        )
        assert handoff.status_code == 200, handoff.text
        assert handoff.json()["request"]["assigned_ta"] == "Bob Martinez"
        resolver = bob
    else:
        resolver = alice if primary == "Alice Chen" else bob

    replied = client.post(
        "/ta/reply/",
        headers=_auth(resolver),
        json={
            "request_id": rid,
            "reply": "Start from the color invariant, then check the uncle cases.",
        },
    )
    assert replied.status_code == 200, replied.text

    resolved = client.post(
        "/ta/resolve/",
        headers=_auth(resolver),
        json={
            "request_id": rid,
            "teaching_notes": (
                "1. Restate the color invariant.\n"
                "2. Trace the uncle cases.\n"
                "3. Have the student finish the last rotation."
            ),
            "student_hint": "Which case are you in after deletion?",
            "resolution_status": "resolved",
        },
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["knowledge_entry"]["status"] == "pending_review"
    assert resolved.json()["knowledge_entry"]["ta_resolution"] == "resolved"

    # Student cannot hit TA resolve.
    denied = client.post(
        "/ta/resolve/",
        headers=_auth(student),
        json={
            "request_id": rid,
            "teaching_notes": "nope not a ta writing notes here now",
            "resolution_status": "resolved",
        },
    )
    assert denied.status_code == 403


def test_ask_triage_fields_present_on_queue_item():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _csc2302(student)
    created = client.post(
        "/requests/",
        headers=_auth(student),
        json={
            "text": "Show an example of recursion tracing on a small call tree.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=_auth(alice),
    ).json()
    item = next(row for row in queue if row["request"]["id"] == created["id"])
    assert item["learning_style"] or item["request"]["learning_style"]
    assert item["request"]["work_status"] == "open"
