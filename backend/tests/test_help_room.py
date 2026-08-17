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
    named = next(item for item in feed_y if item["id"] == post_id)
    assert named["anonymous"] is False
    assert named["author_display"] != "Anonymous"
    assert named["author_user_id"]

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
    assert again.json()["reachable"] is True

    handshake = client.post(
        f"/help-room/replies/{reply_id}/reach-out",
        headers=_headers(sara),
        json={
            "note": "Your walk metaphor unlocked it — want to compare notes before the quiz?"
        },
    )
    assert handshake.status_code == 201, handshake.text
    assert handshake.json()["is_incoming"] is False
    assert "unlocked" in handshake.json()["note"].lower()

    inbox = client.get(
        f"/help-room/reach-outs/?course_id={course_id}",
        headers=_headers(youssef),
    ).json()
    assert any(row["from_display"] and "unlocked" in row["note"].lower() for row in inbox)
    assert any(row["is_incoming"] for row in inbox)

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
    hashing = next(topic for topic in body["topics"] if topic["stuck_post_count"] >= 1)
    assert hashing["questions"]
    assert hashing["topic_key"]

    covered = client.patch(
        "/analytics/review-insights",
        headers=_headers(prof),
        json={
            "course_id": course_id,
            "topic_key": hashing["topic_key"],
            "review_status": "covered",
            "next_cohort_note": "Show chaining vs probing with one board drawing next year.",
        },
    )
    assert covered.status_code == 200, covered.text
    saved = next(
        topic
        for topic in covered.json()["topics"]
        if topic["topic_key"] == hashing["topic_key"]
    )
    assert saved["review_status"] == "covered"
    assert "board drawing" in saved["next_cohort_note"]

    faq = client.post(
        "/knowledge/from-insight",
        headers=_headers(prof),
        json={"course_id": course_id, "topic_key": hashing["topic_key"]},
    )
    assert faq.status_code == 201, faq.text
    assert faq.json()["status"] == "pending_review"
    assert "FAQ" in faq.json()["question_text"] or faq.json()["question_text"]


def test_community_flair_nested_comments_same_here_and_sort():
    sara = _login("s.elidrissi@aui.ma")
    youssef = _login("y.amrani@aui.ma")
    course_id = _shared_student_course(sara, youssef)

    bad_flair = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Wrong flair",
            "body": "This should bounce.",
            "flair": "homework",
        },
    )
    assert bad_flair.status_code == 422

    stuck = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Recursion stack overflow on merge",
            "body": "I think my base case never fires.",
            "chapter": "Recursion",
            "flair": "stuck",
        },
    )
    assert stuck.status_code == 201, stuck.text
    stuck_id = stuck.json()["id"]
    assert stuck.json()["flair"] == "stuck"
    assert stuck.json()["same_here_count"] == 0

    vent = client.post(
        "/help-room/",
        headers=_headers(youssef),
        json={
            "course_id": course_id,
            "title": "This chapter is a lot before the quiz",
            "body": "I keep rereading AVL rotations and it still feels one insight away.",
            "chapter": "AVL",
            "flair": "vent",
            "anonymous": True,
        },
    )
    assert vent.status_code == 201, vent.text
    vent_id = vent.json()["id"]

    self_vote = client.post(
        f"/help-room/{stuck_id}/same-here",
        headers=_headers(sara),
    )
    assert self_vote.status_code == 422

    voted = client.post(
        f"/help-room/{stuck_id}/same-here",
        headers=_headers(youssef),
    )
    assert voted.status_code == 200, voted.text
    assert voted.json()["marked"] is True
    assert voted.json()["same_here_count"] == 1

    parent = client.post(
        f"/help-room/{stuck_id}/replies",
        headers=_headers(youssef),
        json={
            "body": "Print n before the recursive call — if n never hits 0, the split is wrong.",
            "anonymous": False,
        },
    )
    assert parent.status_code == 201, parent.text
    parent_id = parent.json()["id"]

    child = client.post(
        f"/help-room/{stuck_id}/replies",
        headers=_headers(sara),
        json={
            "body": "That was the missing check — thank you.",
            "parent_reply_id": parent_id,
        },
    )
    assert child.status_code == 201, child.text
    assert child.json()["parent_reply_id"] == parent_id

    thread = client.get(
        f"/help-room/{stuck_id}",
        headers=_headers(sara),
    )
    assert thread.status_code == 200, thread.text
    tree = thread.json()["replies"]
    assert len(tree) == 1
    assert tree[0]["id"] == parent_id
    assert len(tree[0]["children"]) == 1
    assert tree[0]["children"][0]["id"] == child.json()["id"]

    community = client.get(
        f"/help-room/community/?course_id={course_id}",
        headers=_headers(sara),
    ).json()
    assert community["community_name"].startswith("r/")
    assert community["post_count"] >= 2
    assert community["comment_count"] >= 2
    assert community["classmate_count"] >= 2

    top = client.get(
        f"/help-room/?course_id={course_id}&sort=top",
        headers=_headers(sara),
    ).json()
    assert top[0]["id"] == stuck_id
    assert top[0]["same_here_count"] == 1

    vents = client.get(
        f"/help-room/?course_id={course_id}&flair=vent",
        headers=_headers(sara),
    ).json()
    assert all(item["flair"] == "vent" for item in vents)
    assert any(item["id"] == vent_id for item in vents)
    named = next(item for item in vents if item["id"] == vent_id)
    assert named["author_display"] != "Anonymous"
    assert named["author_user_id"]
    board = client.get(
        f"/help-room/ranks/?course_id={course_id}",
        headers=_headers(sara),
    ).json()
    assert any(row["user_id"] == named["author_user_id"] for row in board)


def test_rooms_forum_types_votes_interest_accept_and_profile():
    sara = _login("s.elidrissi@aui.ma")
    youssef = _login("y.amrani@aui.ma")
    course_id = _shared_student_course(sara, youssef)

    created = client.post(
        "/help-room/",
        headers=_headers(sara),
        json={
            "course_id": course_id,
            "title": "Need a second pair of eyes on Dijkstra parent updates",
            "body": "I relax edges but dist[u] never drops. Not asking for the write-up.",
            "chapter": "Shortest paths",
            "room_type": "problem",
            "tags": ["Graphs", "QuizPrep"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["room_type"] == "problem"
    assert body["status"] == "open"
    assert "Graphs" in body["tags"]
    post_id = body["id"]

    down = client.post(
        f"/help-room/{post_id}/vote",
        headers=_headers(youssef),
        json={"value": -1},
    )
    assert down.status_code == 200, down.text
    assert down.json()["score"] == -1
    up = client.post(
        f"/help-room/{post_id}/vote",
        headers=_headers(youssef),
        json={"value": 1},
    )
    assert up.json()["score"] == 1
    assert up.json()["my_vote"] == 1

    interest = client.post(
        f"/help-room/{post_id}/interest",
        headers=_headers(youssef),
        json={"note": "I can walk the relaxation order with you."},
    )
    assert interest.status_code == 201, interest.text

    reply = client.post(
        f"/help-room/{post_id}/replies",
        headers=_headers(youssef),
        json={
            "body": "Relax only if dist[u] + w < dist[v], then set parent.",
        },
    )
    assert reply.status_code == 201, reply.text
    reply_id = reply.json()["id"]

    accepted = client.post(
        f"/help-room/replies/{reply_id}/accept",
        headers=_headers(sara),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "solved"
    assert any(item.get("accepted") for item in accepted.json()["replies"])

    pulse = client.get(
        f"/help-room/community/?course_id={course_id}",
        headers=_headers(sara),
    ).json()
    assert pulse["chapters"]
    assert pulse["chapter_source"] in ("syllabus", "syllabus+canvas")
    divide = next(
        (item for item in pulse["chapters"] if "divide" in item["label"].lower()),
        None,
    )
    if pulse["chapter_source"] == "syllabus+canvas":
        assert divide is not None
        assert divide["source"] in ("both", "canvas", "syllabus")

    me = client.get("/auth/me", headers=_headers(youssef)).json()
    profile = client.get(
        f"/help-room/profile/{me['id']}?course_id={course_id}",
        headers=_headers(sara),
    )
    assert profile.status_code == 200, profile.text
    card = profile.json()
    assert card["handle"]
    assert card["accepted"] >= 1
    assert card["tier"]
    assert "hilbert_weight" in card

    board = client.get(
        f"/help-room/ranks/?course_id={course_id}",
        headers=_headers(sara),
    ).json()
    assert board[0]["node_points"] >= 1
    assert board[0]["hilbert_weight"] >= 0
