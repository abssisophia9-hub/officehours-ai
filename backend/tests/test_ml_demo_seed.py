"""CSC 3347 demo seed: approved notes, classmate sketches, rooms."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.auth import Course, CourseMembership, User
from app.models.help_room import HelpPost, HelpReply
from app.models.knowledge import KnowledgeEntry
from app.models.peer_notes import PeerNote
from app.services.demo_accounts import ensure_demo_accounts
from app.services.ml_demo_seed import (
    CLASSMATE_LABEL,
    COURSE_CODE,
    COURSE_ONLY_TOKEN,
    COURSE_TITLE,
    DEMO_MARK,
    PEER_ONLY_TOKEN,
    seed_ml_demo,
)

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _seed():
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def _login(email: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": "aui-demo"},
    )
    assert response.status_code == 200
    return response.json()["token"]


def _course_id(token: str, code: str) -> int:
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    match = [course for course in me["courses"] if course["code"] == code]
    assert match
    return match[0]["id"]


def test_demo_off_does_not_create_the_machine_learning_course(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    db = SessionLocal()
    try:
        seed_ml_demo(db)
        assert db.query(User).filter(User.email == "l.chraibi@aui.ma").count() == 0
        assert db.query(Course).filter(Course.code == COURSE_CODE).count() == 0
    finally:
        db.close()


def test_seed_creates_people_notes_and_rooms_once():
    _seed()
    db = SessionLocal()
    try:
        seed_ml_demo(db)
        course = db.query(Course).filter(Course.code == COURSE_CODE).one()
        assert course.title == COURSE_TITLE
        roles = {
            row.role
            for row in db.query(CourseMembership)
            .filter(CourseMembership.course_id == course.id)
            .all()
        }
        assert roles == {"professor", "ta", "student"}
        memberships = (
            db.query(CourseMembership)
            .filter(CourseMembership.course_id == course.id)
            .all()
        )
        assert sum(row.role == "professor" for row in memberships) == 1
        assert sum(row.role == "ta" for row in memberships) == 1
        assert sum(row.role == "student" for row in memberships) == 4
        for row in memberships:
            user = db.get(User, row.user_id)
            assert user is not None
            assert "(demo)" in user.display_name
            assert user.bio and user.bio.startswith("Demo account.")

        materials = (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.course_id == course.id)
            .all()
        )
        assert materials
        assert {row.status for row in materials} == {"approved"}
        assert {row.entry_kind for row in materials} == {"course_material"}
        names = {row.source_filename for row in materials}
        assert names == {
            "parametric_methods.md",
            "multivariate_gaussians.md",
            "mahalanobis_and_outliers.md",
        }
        assert all(DEMO_MARK in (row.tags or "") for row in materials)
        assert all(DEMO_MARK in (row.professor_note or "") for row in materials)
        blob = "\n".join(row.answer_draft for row in materials)
        assert COURSE_ONLY_TOKEN in blob
        assert PEER_ONLY_TOKEN not in blob

        notes = db.query(PeerNote).filter(PeerNote.course_id == course.id).all()
        assert len(notes) == 3
        assert {note.caption for note in notes} == {CLASSMATE_LABEL}
        assert all(note.about.startswith("Demo.") for note in notes)
        authors = {note.author_user_id for note in notes}
        assert len(authors) == 3

        posts = db.query(HelpPost).filter(HelpPost.course_id == course.id).all()
        assert len(posts) == 8
        assert all(DEMO_MARK in (post.tags_json or "") for post in posts)
        solved = [post for post in posts if post.status == "solved"]
        assert len(solved) == 1
        open_posts = [post for post in posts if post.status == "open"]
        reply_counts = {
            post.id: db.query(HelpReply).filter(HelpReply.post_id == post.id).count()
            for post in posts
        }
        assert sum(reply_counts[post.id] == 0 for post in open_posts) == 3
        assert sum(reply_counts[post.id] > 0 for post in open_posts) == 4
        replies = (
            db.query(HelpReply)
            .filter(HelpReply.post_id.in_([post.id for post in posts]))
            .all()
        )
        posts_by_id = {post.id: post for post in posts}
        assert replies
        assert all(reply.author_user_id != posts_by_id[reply.post_id].author_user_id for reply in replies)
        assert sum(reply.accepted for reply in replies) == 1

        post_count = len(posts)
        note_count = len(notes)
        material_count = len(materials)
    finally:
        db.close()

    db = SessionLocal()
    try:
        seed_ml_demo(db)
        course = db.query(Course).filter(Course.code == COURSE_CODE).one()
        assert db.query(HelpPost).filter(HelpPost.course_id == course.id).count() == post_count
        assert db.query(PeerNote).filter(PeerNote.course_id == course.id).count() == note_count
        assert (
            db.query(KnowledgeEntry).filter(KnowledgeEntry.course_id == course.id).count()
            == material_count
        )
    finally:
        db.close()


def test_classmate_notes_are_not_in_the_study_agent():
    _seed()
    token = _login("l.chraibi@aui.ma")
    course_id = _course_id(token, COURSE_CODE)
    headers = {"Authorization": f"Bearer {token}"}

    hidden = client.post(
        "/agent/ask",
        headers=headers,
        json={"question": f"What is {PEER_ONLY_TOKEN}?", "course_id": course_id},
    ).json()
    assert hidden["matched_count"] == 0
    assert hidden["should_seek_help"] is True
    assert PEER_ONLY_TOKEN not in hidden["answer"]

    visible = client.post(
        "/agent/ask",
        headers=headers,
        json={"question": f"What is {COURSE_ONLY_TOKEN}?", "course_id": course_id},
    ).json()
    assert visible["matched_count"] >= 1
    assert visible["should_seek_help"] is False
    assert COURSE_ONLY_TOKEN in visible["answer"]

    notes = client.get(
        f"/peer-notes/?course_id={course_id}",
        headers=headers,
    ).json()
    assert len(notes) == 3
    assert {note["caption"] for note in notes} == {CLASSMATE_LABEL}


def test_student_of_another_course_cannot_read_the_ml_seed():
    _seed()
    outsider = _login("s.elidrissi@aui.ma")
    member = _login("l.chraibi@aui.ma")
    course_id = _course_id(member, COURSE_CODE)
    headers = {"Authorization": f"Bearer {outsider}"}

    notes = client.get(f"/peer-notes/?course_id={course_id}", headers=headers)
    assert notes.status_code == 403

    rooms = client.get(f"/help-room/?course_id={course_id}", headers=headers)
    assert rooms.status_code == 403

    ask = client.post(
        "/agent/ask",
        headers=headers,
        json={"question": f"What is {COURSE_ONLY_TOKEN}?", "course_id": course_id},
    )
    assert ask.status_code == 403
