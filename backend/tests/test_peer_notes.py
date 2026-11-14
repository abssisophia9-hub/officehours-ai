"""Peer study notes — share, like, comment, download."""

import io
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


def _student_course_id(token: str) -> int:
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    courses = [c for c in me["courses"] if c["role"] == "student"]
    assert courses
    # Prefer CSC 2302 when present
    for course in courses:
        if course["code"] == "CSC 2302":
            return course["id"]
    return courses[0]["id"]


def _shared_student_course(token_a: str, token_b: str) -> int:
    a = client.get("/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    b = client.get("/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()
    a_ids = {
        c["id"]
        for c in a["courses"]
        if c["role"] == "student"
    }
    b_ids = {c["id"] for c in b["courses"] if c["role"] == "student"}
    shared = sorted(a_ids & b_ids)
    assert shared, "demo students should share at least one course"
    return shared[0]


def test_upload_requires_about_and_auth():
    token = _login("s.elidrissi@aui.ma")
    course_id = _student_course_id(token)
    # Missing about via empty string rejected
    response = client.post(
        "/peer-notes/",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "course_id": str(course_id),
            "title": "AVL cheatsheet",
            "about": "",
        },
        files={"file": ("notes.txt", b"rotation tips", "text/plain")},
    )
    assert response.status_code == 422

    unauth = client.post(
        "/peer-notes/",
        data={
            "course_id": str(course_id),
            "title": "AVL cheatsheet",
            "about": "Week 5 rotations",
        },
        files={"file": ("notes.txt", b"rotation tips", "text/plain")},
    )
    assert unauth.status_code == 401


def test_share_like_comment_download_feed():
    sara = _login("s.elidrissi@aui.ma")
    youssef = _login("y.amrani@aui.ma")
    course_id = _shared_student_course(sara, youssef)

    created = client.post(
        "/peer-notes/",
        headers={"Authorization": f"Bearer {sara}"},
        data={
            "course_id": str(course_id),
            "title": "Hash table open addressing",
            "about": "Lecture 7 — probing vs chaining",
            "caption": "My cleaned board notes from Tuesday",
            "anonymous": "false",
        },
        files={
            "file": (
                "hashing.txt",
                b"Linear probing: look for next empty slot.\n",
                "text/plain",
            )
        },
    )
    assert created.status_code == 201, created.text
    note = created.json()
    assert note["title"] == "Hash table open addressing"
    assert "probing" in note["about"].lower()
    assert note["like_count"] == 0
    assert note["is_mine"] is True
    note_id = note["id"]

    feed = client.get(
        f"/peer-notes/?course_id={course_id}",
        headers={"Authorization": f"Bearer {youssef}"},
    ).json()
    assert any(item["id"] == note_id for item in feed)

    liked = client.post(
        f"/peer-notes/{note_id}/like",
        headers={"Authorization": f"Bearer {youssef}"},
    ).json()
    assert liked["liked"] is True
    assert liked["like_count"] == 1

    comment = client.post(
        f"/peer-notes/{note_id}/comments",
        headers={"Authorization": f"Bearer {youssef}"},
        json={"body": "This saved me before the quiz — thanks!", "anonymous": False},
    ).json()
    assert "quiz" in comment["body"]

    comments = client.get(
        f"/peer-notes/{note_id}/comments",
        headers={"Authorization": f"Bearer {sara}"},
    ).json()
    assert len(comments) == 1

    download = client.get(
        f"/peer-notes/{note_id}/download",
        headers={"Authorization": f"Bearer {youssef}"},
    )
    assert download.status_code == 200
    assert b"Linear probing" in download.content

    # Image upload + preview
    png_bytes = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    image = client.post(
        "/peer-notes/",
        headers={"Authorization": f"Bearer {sara}"},
        data={
            "course_id": str(course_id),
            "title": "Board photo — trees",
            "about": "In-class BST drawing",
            "anonymous": "true",
        },
        files={"file": ("board.png", io.BytesIO(png_bytes), "image/png")},
    )
    assert image.status_code == 201, image.text
    assert image.json()["is_image"] is True
    assert image.json()["anonymous"] is True
    # Classmate sees anonymous label
    feed2 = client.get(
        f"/peer-notes/?course_id={course_id}",
        headers={"Authorization": f"Bearer {youssef}"},
    ).json()
    anon = next(item for item in feed2 if item["id"] == image.json()["id"])
    assert anon["author_display"] == "Classmate"

    preview = client.get(
        f"/peer-notes/{image.json()['id']}/preview",
        headers={"Authorization": f"Bearer {youssef}"},
    )
    assert preview.status_code == 200

    # Non-member blocked
    outsider = _login("a.benali@aui.ma")
    # Professor is member of CSC 2302 — use a course they might not share.
    # Instead: create note on COM 1301 if Sara has it and professor doesn't.
    me_sara = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {sara}"}
    ).json()
    me_prof = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {outsider}"}
    ).json()
    sara_ids = {c["id"] for c in me_sara["courses"]}
    prof_ids = {c["id"] for c in me_prof["courses"]}
    only_sara = list(sara_ids - prof_ids)
    if only_sara:
        blocked = client.get(
            f"/peer-notes/?course_id={only_sara[0]}",
            headers={"Authorization": f"Bearer {outsider}"},
        )
        assert blocked.status_code == 403

    # Non-owner cannot delete Sara's note (Youssef is a classmate on the course).
    denied = client.delete(
        f"/peer-notes/{note_id}",
        headers={"Authorization": f"Bearer {youssef}"},
    )
    assert denied.status_code == 403

    deleted = client.delete(
        f"/peer-notes/{note_id}",
        headers={"Authorization": f"Bearer {sara}"},
    )
    assert deleted.status_code == 204
    # File is cleaned up — download after delete is gone.
    gone = client.get(
        f"/peer-notes/{note_id}/download",
        headers={"Authorization": f"Bearer {sara}"},
    )
    assert gone.status_code in {404, 410}
