"""FYP defense hardening: queue auth, WS scope, claim lock, desk filter."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_RATE_LIMIT"] = "false"

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


def _login(email: str) -> dict:
    body = client.post(
        "/auth/login",
        json={"email": email, "password": "aui-demo"},
    ).json()
    return {
        "token": body["token"],
        "headers": {"Authorization": f"Bearer {body['token']}"},
        "user": body["user"],
    }


def _course(user: dict, code: str) -> int:
    return next(c["id"] for c in user["courses"] if c["code"] == code)


def _ask(student: dict, course_id: int, text: str) -> int:
    created = client.post(
        "/requests/",
        headers=student["headers"],
        json={
            "text": text,
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_student_cannot_read_ta_queue_via_course_string():
    student = _login("s.elidrissi@aui.ma")
    leaked = client.get(
        "/ta/queue/?course=CSC%202302",
        headers=student["headers"],
    )
    assert leaked.status_code == 422
    course_id = _course(student["user"], "CSC 2302")
    staff_only = client.get(
        f"/ta/queue/?course_id={course_id}",
        headers=student["headers"],
    )
    assert staff_only.status_code == 403


def test_desk_filter_shows_assigned_backup_and_unassigned():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    rid = _ask(
        student,
        course_id,
        "Why is dequeue O(n) on a Python list used as a queue?",
    )
    desk = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=desk",
        headers=alice["headers"],
    )
    assert desk.status_code == 200, desk.text
    ids = [item["request"]["id"] for item in desk.json()]
    assert rid in ids
    assert all(item["help_coach"] is None for item in desk.json())


def test_second_ta_cannot_steal_claim():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    bob = _login("b.martinez@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    rid = _ask(student, course_id, "Hash collisions on insert — anyone?")
    first = client.post(
        "/ta/claim/",
        headers=alice["headers"],
        json={"request_id": rid},
    )
    assert first.status_code == 200, first.text
    assert first.json()["request"]["claimed_by_user_id"] == alice["user"]["id"]
    second = client.post(
        "/ta/claim/",
        headers=bob["headers"],
        json={"request_id": rid},
    )
    assert second.status_code == 409


def test_websocket_rejects_anonymous_and_other_course():
    student = _login("s.elidrissi@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    other = _course(student["user"], "CSC 3374")

    with client.websocket_connect("/ws") as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"

    with client.websocket_connect(
        f"/ws?token={student['token']}&course_id={course_id}"
    ) as websocket:
        hello = websocket.receive_json()
        assert hello["type"] == "connected"
        assert hello["payload"]["course_id"] == course_id

    alice = _login("a.chen@aui.ma")
    # Alice is not a member of every Sara course (e.g. some liberal-arts codes).
    # A non-member token + foreign course_id must not subscribe.
    with client.websocket_connect(
        f"/ws?token={alice['token']}&course_id={other}"
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "error"


def test_help_coach_is_on_select_not_list():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    rid = _ask(student, course_id, "Explain AVL rotations after a double imbalance.")
    queue = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=alice["headers"],
    ).json()
    item = next(row for row in queue if row["request"]["id"] == rid)
    assert item["help_coach"] is None
    coach = client.get(
        f"/ta/coach/?request_id={rid}",
        headers=alice["headers"],
    )
    assert coach.status_code == 200, coach.text
    assert coach.json()["teaching_approach"]
    denied = client.get(
        f"/ta/coach/?request_id={rid}",
        headers=student["headers"],
    )
    assert denied.status_code == 403


def test_student_sees_only_own_asks_not_classmate_queue():
    sara = _login("s.elidrissi@aui.ma")
    youssef = _login("y.amrani@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _course(sara["user"], "CSC 3374")
    created = client.post(
        "/requests/",
        headers=sara["headers"],
        json={
            "text": "Why does a Python list used as a queue make dequeue O(n)?",
            "anonymous": True,
            "course": "CSC 3374",
            "course_id": course_id,
        },
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    mine = client.get(
        f"/requests/?course_id={course_id}",
        headers=sara["headers"],
    )
    assert mine.status_code == 200
    assert rid in [row["id"] for row in mine.json()]

    classmate = client.get(
        f"/requests/?course_id={course_id}",
        headers=youssef["headers"],
    )
    assert classmate.status_code == 200
    assert rid not in [row["id"] for row in classmate.json()]

    hidden = client.get(f"/requests/{rid}", headers=youssef["headers"])
    assert hidden.status_code == 404

    receipt = client.get(f"/requests/{rid}/status", headers=youssef["headers"])
    assert receipt.status_code == 200
    assert receipt.json()["request_code"] == rid

    # Alice staffs 2302, not 3374 — she must not read the full row.
    assert client.get(f"/requests/{rid}", headers=alice["headers"]).status_code == 404

    prof = _login("a.benali@aui.ma")
    full = client.get(f"/requests/{rid}", headers=prof["headers"])
    assert full.status_code == 200
    assert full.json()["id"] == rid


def test_agent_cites_faq_title_not_entry_id():
    from app.database.session import SessionLocal
    from app.models.knowledge import KnowledgeEntry
    from app.services.kb_agent_service import answer_from_knowledge_base

    student = _login("s.elidrissi@aui.ma")
    course_id = _course(student["user"], "CSC 3374")
    db = SessionLocal()
    try:
        primary = KnowledgeEntry(
            question_text="Week 4 hashing slides — open addressing",
            answer_draft="Open addressing stores a colliding key in the next free slot.",
            student_hint="Walk the next buckets.",
            status="approved",
            course_id=course_id,
            material_source="slides",
            entry_kind="course_material",
            source_filename="week4-hashing.pdf",
            page_number=4,
            chunk_index=1,
        )
        related = KnowledgeEntry(
            question_text="Week 4 hashing slides — linear probing",
            answer_draft="Linear probing walks consecutive buckets until empty.",
            student_hint="Start at the hash index.",
            status="approved",
            course_id=course_id,
            material_source="slides",
            entry_kind="course_material",
            source_filename="week4-hashing.pdf",
            page_number=4,
            chunk_index=2,
        )
        db.add_all([primary, related])
        db.commit()
        body = answer_from_knowledge_base(
            db,
            "Week 4 hashing slides — open addressing",
            course_id=course_id,
        )
    finally:
        db.close()
    assert body.should_seek_help is False
    assert "week4-hashing.pdf, p. 4, chunk 1" in body.answer
    assert "#" not in body.answer.split(":")[0]
    assert "Related approved material:" in body.answer
    assert "#1 (" not in body.answer
