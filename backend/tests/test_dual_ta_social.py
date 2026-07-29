"""Course-scoped dual-TA matching, queue filters, solidarity, study-buddy."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import DEMO_PASSWORD

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _login(email: str) -> dict:
    payload = client.post(
        "/auth/login",
        json={"email": email, "password": DEMO_PASSWORD},
    ).json()
    return payload


def test_course_has_two_tas_and_matcher_stays_in_course():
    student = _login("s.elidrissi@aui.ma")
    course = next(c for c in student["user"]["courses"] if c["code"] == "CSC 2302")
    load = client.get(f"/ta/load/?course_id={course['id']}").json()
    assert load["ta_count"] == 2
    names = {ta["name"] for ta in load["tas"]}
    assert names == {"Alice Chen", "Bob Martinez"}

    created = client.post(
        "/requests/",
        json={
            "text": "In CSC 2302 I am stuck on red-black tree deletion fixup rotations.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course["id"],
            "help_mode": "message",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["assigned_ta"] in names
    if body["alternative_ta"]:
        assert body["alternative_ta"] in names
        assert body["alternative_ta"] != body["assigned_ta"]


def test_ta_queue_mine_vs_backup_filters():
    student = _login("s.elidrissi@aui.ma")
    course = next(c for c in student["user"]["courses"] if c["code"] == "CSC 2302")
    created = client.post(
        "/requests/",
        json={
            "text": "Hash table chaining vs open addressing for collisions?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course["id"],
        },
    ).json()
    primary = created["assigned_ta"]
    backup = created["alternative_ta"]

    mine = client.get(
        f"/ta/queue/?course_id={course['id']}&assignment=mine&ta_name={primary}"
    ).json()
    assert any(item["request"]["id"] == created["id"] for item in mine)

    if backup:
        as_backup = client.get(
            f"/ta/queue/?course_id={course['id']}&assignment=backup&ta_name={backup}"
        ).json()
        assert any(item["request"]["id"] == created["id"] for item in as_backup)


def test_solidarity_and_study_buddy_for_non_sensitive_cluster():
    student = _login("s.elidrissi@aui.ma")
    course = next(c for c in student["user"]["courses"] if c["code"] == "CSC 2302")
    first = client.post(
        "/requests/",
        json={
            "text": "How do AVL rotations keep BST height logarithmic after insert?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course["id"],
        },
    ).json()
    # Force same topic cluster so solidarity is deterministic in tests.
    second = client.post(
        "/requests/",
        json={
            "text": "My BST insert keeps unbalancing — how do rotations keep height logarithmic?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course["id"],
            "cluster_id": first["cluster_id"],
        },
    ).json()
    assert second["cluster_id"] == first["cluster_id"]
    assert second["similar_asks_this_week"] >= 1
    assert second["solidarity_message"]
    assert second["study_buddy_eligible"] is True

    status = client.post(
        f"/requests/{second['id']}/study-buddy",
        json={"request_id": second["id"]},
    ).json()
    assert status["opted_in"] is True
    assert status["eligible"] is True

    # Sensitive asks cannot peer-match.
    stress = client.post(
        "/requests/",
        json={
            "text": "I am panicking about failing and need private emotional support.",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course["id"],
        },
    ).json()
    blocked = client.post(
        f"/requests/{stress['id']}/study-buddy",
        json={"request_id": stress["id"]},
    ).json()
    assert blocked["eligible"] is False
    assert blocked["opted_in"] is False
    assert first["id"]


def test_priya_and_sam_demo_accounts_exist():
    priya = _login("p.nair@aui.ma")
    assert any(c["role"] == "ta" for c in priya["user"]["courses"])
    sam = _login("s.ortiz@aui.ma")
    assert any(c["role"] == "ta" for c in sam["user"]["courses"])
