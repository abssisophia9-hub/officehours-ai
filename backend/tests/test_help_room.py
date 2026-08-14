"""Stuck Room + professor review insights."""

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


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _student_course_id(token: str, *, prefer: str = "CSC 3323") -> int:
    me = client.get("/auth/me", headers=_headers(token)).json()
    courses = [c for c in me["courses"] if c["role"] == "student"]
    assert courses
    for course in courses:
        if course["code"] == prefer:
            return course["id"]
    return courses[0]["id"]


def _shared_student_course(token_a: str, token_b: str) -> int:
    a = client.get("/auth/me", headers=_headers(token_a)).json()
    b = client.get("/auth/me", headers=_headers(token_b)).json()
    a_ids = {c["id"] for c in a["courses"] if c["role"] == "student"}
    b_ids = {c["id"] for c in b["courses"] if c["role"] == "student"}
    shared = sorted(a_ids & b_ids)
    assert shared, "demo students should share at least one course"
    return shared[0]


def _professor_course(token: str, code: str = "CSC 2302") -> int:
    me = client.get("/auth/me", headers=_headers(token)).json()
    for course in me["courses"]:
        if course["role"] == "professor" and course["code"] == code:
            return course["id"]
    raise AssertionError("professor demo course missing")


def test_stuck_room_requires_student_and_auth():
    sara = _login("s.elidrissi@aui.ma")
    course_id = _student_course_id(sara, prefer="CSC 2302")

    unauth = client.get(f"/help-room/?course_id={course_id}")
    assert unauth.status_code == 401

    created = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Stuck on AVL imbalance after insert",
            "body": "I rotate left but the BF still looks wrong on the parent.",
            "chapter": "Chapter 5 — AVL",
            "anonymous": False,
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["title"].startswith("Stuck on AVL")
    assert created.json()["chapter"].startswith("Chapter 5")

    # Professor of the same course cannot read the social room (insights only).
    prof = _login("a.benali@aui.ma")
    blocked = client.get(
        f"/help-room/?course_id={course_id}",
        headers=_headers(prof),
    )
    assert blocked.status_code == 403

    # TA of CSC 2302 is not a classmate in that course.
    alice = _login("a.chen@aui.ma")
    ta_blocked = client.get(
        f"/help-room/?course_id={course_id}",
        headers=_headers(alice),
    )
    assert ta_blocked.status_code == 403


def test_reply_helpful_marks_rank_and_no_self_vote():
    sara = _login("s.elidrissi@aui.ma")
    youssef = _login("y.amrani@aui.ma")
    course_id = _shared_student_course(sara, youssef)

    post = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Hashing — why linear probing clusters",
            "body": "I understand collisions but not why primary clustering happens.",
            "chapter": "Hashing",
            "anonymous": True,
        },
    )
    assert post.status_code == 201, post.text
    post_id = post.json()["id"]
    # Author sees own name even when anonymous.
    assert post.json()["is_mine"] is True
    assert "elidrissi" in post.json()["author_display"].lower() or post.json()[
        "author_display"
    ]

    feed_y = client.get(
        f"/help-room/?course_id={course_id}",
        headers=_headers(youssef),
    ).json()
    anon = next(item for item in feed_y if item["id"] == post_id)
    assert anon["author_display"] == "Classmate"

    reply = client.post(
        f"/help-room/{post_id}/replies",
        headers=_headers(youssef),
        json={
            "body": "Try thinking of probing as a walk that other keys also take — "
            "once a cluster starts, new keys join the same walk.",
            "anonymous": False,
        },
    )
    assert reply.status_code == 201, reply.text
    reply_id = reply.json()["id"]

    self_mark = client.post(
        f"/help-room/replies/{reply_id}/helpful",
        headers=_headers(youssef),
    )
    assert self_mark.status_code == 422

    marked = client.post(
        f"/help-room/replies/{reply_id}/helpful",
        headers=_headers(sara),
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["marked"] is True
    assert marked.json()["helpful_count"] == 1

    # Toggle off then on again — still unique, not a like farm.
    client.post(
        f"/help-room/replies/{reply_id}/helpful",
        headers=_headers(sara),
    )
    again = client.post(
        f"/help-room/replies/{reply_id}/helpful",
        headers=_headers(sara),
    )
    assert again.json()["helpful_count"] == 1

    ranks = client.get(
        f"/help-room/ranks/?course_id={course_id}",
        headers=_headers(sara),
    ).json()
    assert ranks
    assert ranks[0]["helpful_points"] == 1
    assert ranks[0]["rank"] == 1

    deleted = client.delete(
        f"/help-room/{post_id}",
        headers=_headers(sara),
    )
    assert deleted.status_code == 204


def test_sensitive_topics_redirect_to_quiet_ask():
    sara = _login("s.elidrissi@aui.ma")
    course_id = _student_course_id(sara)
    blocked = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Grading dispute on midterm Q3",
            "body": "I want to change my grade, this is a grading dispute.",
            "anonymous": True,
        },
    )
    assert blocked.status_code == 422
    assert "Quiet ask" in blocked.json()["detail"]


def test_professor_review_insights_from_asks_and_stuck_room():
    sara = _login("s.elidrissi@aui.ma")
    prof = _login("a.benali@aui.ma")
    course_id = _professor_course(prof, "CSC 2302")

    first = client.post(
        "/requests/",
        json={
            "text": "How do hash tables handle collisions with chaining?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/requests/",
        json={
            "text": "Hash table collisions and chaining explanation please",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    )
    assert second.status_code == 201

    stuck = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Still stuck on chaining vs probing",
            "body": "I get buckets but not when to pick chaining.",
            "chapter": "Hashing",
        },
    )
    assert stuck.status_code == 201, stuck.text

    unauth = client.get(f"/analytics/review-insights?course_id={course_id}")
    assert unauth.status_code == 401

    student_denied = client.get(
        f"/analytics/review-insights?course_id={course_id}",
        headers=_headers(sara),
    )
    assert student_denied.status_code == 403

    insights = client.get(
        f"/analytics/review-insights?course_id={course_id}",
        headers=_headers(prof),
    )
    assert insights.status_code == 200, insights.text
    body = insights.json()
    assert body["stuck_post_total"] >= 1
    assert body["office_hours_total"] >= 2
    labels = {topic["label"].lower() for topic in body["topics"]}
    assert any("hash" in label for label in labels)
    assert any(topic["stuck_post_count"] >= 1 for topic in body["topics"])
    assert any(topic["office_hours_count"] >= 1 for topic in body["topics"])
    assert "review" in body["message"].lower() or "emphas" in body["message"].lower()
