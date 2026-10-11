"""No-TA courses go to the professor. A course with a TA still uses Matcher."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.auth import Course, CourseMembership, User
from app.models.notification import Notification
from app.models.request import Request
from app.services.auth_service import hash_password
from tests.helpers import login, professor_auth, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _course_id(user, code):
    return next(course["id"] for course in user["courses"] if course["code"] == code)


def test_course_with_ta_still_assigns_a_ta():
    headers, user = login(client)
    course_id = _course_id(user, "CSC 2302")
    preview = client.get(
        f"/requests/routing?course_id={course_id}",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["destination"] == "ta"
    assert preview.json()["line"] == (
        "Goes to: a TA for CSC 2302 (matched automatically)"
    )

    created = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "How do I rotate a red-black tree after insert?",
            "anonymous": True,
            "student_name": "Sara El Idrissi",
            "student_id": "117400",
            "course": "CSC 2302",
            "course_id": course_id,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["assignee_role"] == "ta"
    assert body["assigned_ta"] in {"Alice Chen", "Bob Martinez"}
    assert body["student_name"] is None
    assert body["student_id"] is None

    professor_headers, _ = professor_auth(client, "CSC 2302")
    inbox = client.get("/notifications/", headers=professor_headers).json()
    routed = [
        item
        for item in inbox["items"]
        if item["request_id"] == body["id"] and item["kind"] == "routed"
    ]
    assert routed == []


def test_no_ta_course_assigns_professor_and_hides_quiet_ask_identity():
    headers, user = login(client)
    course_id = _course_id(user, "CSC 3390")
    preview = client.get(
        f"/requests/routing?course_id={course_id}",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["destination"] == "professor"
    assert preview.json()["assignee_name"] == "Prof. Amine Benali"
    assert preview.json()["line"] == (
        "Goes to: the professor of CSC 3390 (this course has no TA)"
    )

    created = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "What is the chemical formula of sodium chloride?",
            "anonymous": True,
            "student_name": "Sara El Idrissi",
            "student_id": "117400",
            "course": "CSC 3390",
            "course_id": course_id,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["assigned_ta"] == "Prof. Amine Benali"
    assert body["assignee_role"] == "professor"
    assert body["alternative_ta"] is None
    assert body["student_name"] is None
    assert body["student_id"] is None
    assert body["triage"]["matcher"]["assignee_role"] == "professor"

    status = client.get(f"/requests/{body['id']}/status", headers=headers)
    assert status.status_code == 200, status.text
    receipt = status.json()
    assert receipt["assigned_ta"] == "Prof. Amine Benali"
    assert receipt["assignee_role"] == "professor"
    assert "Prof. Amine Benali" in receipt["message"]
    assert "117400" not in status.text
    assert "Sara" not in receipt["message"]

    professor_headers, professor_course = professor_auth(client, "CSC 3390")
    assert professor_course == course_id
    visible = client.get(
        f"/requests/?course_id={course_id}",
        headers=professor_headers,
    )
    assert visible.status_code == 200, visible.text
    rows = visible.json()
    match = next(row for row in rows if row["id"] == body["id"])
    assert match["student_name"] is None
    assert match["student_id"] is None
    assert match["assigned_ta"] == "Prof. Amine Benali"

    inbox = client.get("/notifications/", headers=professor_headers).json()
    note = next(item for item in inbox["items"] if item["request_id"] == body["id"])
    assert note["kind"] == "routed"
    blob = f"{note['title']} {note['body']}"
    assert "CSC 3390" in blob
    assert "no TA" in note["body"]
    assert "Sara" not in blob
    assert "El Idrissi" not in blob
    assert "117400" not in blob


def test_several_professors_uses_lowest_user_id():
    headers, user = login(client)
    sara_id = user["id"]
    db = SessionLocal()
    try:
        course = Course(
            code="CSC 0002",
            title="Two professors",
            term="Spring 2026",
            is_active=True,
        )
        db.add(course)
        db.flush()
        zara = User(
            email="z.prof@aui.ma",
            password_hash=hash_password("aui-demo"),
            display_name="Zara Prof",
            is_active=True,
        )
        amy = User(
            email="a.prof@aui.ma",
            password_hash=hash_password("aui-demo"),
            display_name="Amy Prof",
            is_active=True,
        )
        db.add(zara)
        db.flush()
        db.add(amy)
        db.flush()
        assert zara.id < amy.id
        db.add(CourseMembership(course_id=course.id, user_id=zara.id, role="professor"))
        db.add(CourseMembership(course_id=course.id, user_id=amy.id, role="professor"))
        db.add(CourseMembership(course_id=course.id, user_id=sara_id, role="student"))
        db.commit()
        course_id = course.id
        amy_id = amy.id
        zara_id = zara.id
    finally:
        db.close()

    created = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "Which professor receives this when both are enrolled?",
            "anonymous": True,
            "course": "CSC 0002",
            "course_id": course_id,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["assigned_ta"] == "Zara Prof"
    assert created.json()["assignee_role"] == "professor"

    db = SessionLocal()
    try:
        notes = (
            db.query(Notification)
            .filter(Notification.request_id == created.json()["id"])
            .all()
        )
        assert [note.user_id for note in notes] == [zara_id]
        assert amy_id not in {note.user_id for note in notes}
    finally:
        db.close()


def test_course_with_neither_returns_error_and_stores_nothing():
    headers, user = login(client)
    sara_id = user["id"]
    db = SessionLocal()
    try:
        course = Course(
            code="CSC 0000",
            title="No staff",
            term="Spring 2026",
            is_active=True,
        )
        db.add(course)
        db.flush()
        db.add(CourseMembership(course_id=course.id, user_id=sara_id, role="student"))
        db.commit()
        course_id = course.id
        before = db.query(Request).count()
    finally:
        db.close()

    preview = client.get(
        f"/requests/routing?course_id={course_id}",
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["destination"] == "none"
    assert "no TA and no professor" in preview.json()["line"]

    created = client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "This ask must not be stored.",
            "anonymous": True,
            "student_name": "Sara El Idrissi",
            "student_id": "117400",
            "course": "CSC 0000",
            "course_id": course_id,
        },
    )
    assert created.status_code == 422, created.text
    assert "no TA and no professor" in created.json()["detail"]
    assert "cannot be sent" in created.json()["detail"]

    db = SessionLocal()
    try:
        assert db.query(Request).count() == before
        stored = (
            db.query(Request)
            .filter(Request.text == "This ask must not be stored.")
            .count()
        )
        assert stored == 0
    finally:
        db.close()


def test_student_can_open_labeled_demo_course():
    headers, course_id = student_auth(client, "CSC 3390")
    assert headers["Authorization"].startswith("Bearer ")
    assert course_id
