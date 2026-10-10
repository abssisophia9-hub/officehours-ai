"""Revision Strategist: dossier from asks + web tools, not hardcoded links."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_STRATEGIST_WEB"] = "false"
os.environ["OFFICEHOURS_LEARNING_STYLE_BACKEND"] = "rules"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts
from app.services.strategist_service import _local_tool_loop
from tests.helpers import login, student_auth


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def test_plan_uses_tool_urls_not_hardcoded_3blue1brown(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "Can you draw the rotation after red-black delete_fixup? I need a diagram.",
            "anonymous": True,
            "course_id": course_id,
            "course": "CSC 3374",
        },
    )

    def fake_youtube(query, **_kwargs):
        return [
            {
                "kind": "youtube",
                "title": f"Visual RB trees for {query}",
                "url": "https://www.youtube.com/watch?v=toolhit1",
                "snippet": "diagram animation of rotations",
                "query": query,
            }
        ]

    def fake_articles(query, **_kwargs):
        return [
            {
                "kind": "article",
                "title": f"Red-black tree article ({query})",
                "url": "https://en.wikipedia.org/wiki/Red%E2%80%93black_tree",
                "snippet": "self-balancing binary search tree",
                "query": query,
            }
        ]

    monkeypatch.setattr("app.services.strategist_service.youtube_search", fake_youtube)
    monkeypatch.setattr("app.services.strategist_service.article_search", fake_articles)
    monkeypatch.setenv("OFFICEHOURS_STRATEGIST_WEB", "true")

    response = client.post(
        "/strategist/plan",
        headers=headers,
        json={
            "course_id": course_id,
            "grades": [
                {
                    "topic": "Trees & red-black",
                    "score": 62,
                    "weight": 35,
                    "source": "Canvas · Quiz 4",
                }
            ],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    urls = {item["url"] for item in body["resources"]}
    assert "https://www.youtube.com/watch?v=toolhit1" in urls
    assert "3Blue1Brown" not in str(body)
    assert body["dossier"]["ask_count"] >= 1
    assert body["dossier"]["dominant_style"] == "visual_structural"
    assert body["planner"] == "local-planner"
    assert any(call["tool"] == "youtube_search" for call in body["tool_calls"])
    assert "diagram" in " ".join(call["query"] for call in body["tool_calls"]).lower()
    assert len(body["today"]) == 3
    assert body["today"][0]["resource_url"] == "https://www.youtube.com/watch?v=toolhit1"
    assert "see it" in body["today"][0]["title"].lower()
    assert body["today_summary"]
    assert all(
        (block.get("resource_url") or "").startswith("http")
        or not block.get("resource_url")
        for block in body["today"]
    )


def test_visual_vs_step_queries_differ():
    seen: dict[str, list[str]] = {}

    def execute(tool, query):
        seen.setdefault(tool, []).append(query)
        return []

    _local_tool_loop("visual_structural", "Hashing", "find videos", execute)
    visual = list(seen["youtube_search"])
    seen.clear()
    _local_tool_loop("step_by_step", "Hashing", "find videos", execute)
    step = list(seen["youtube_search"])
    assert any("diagram" in q or "visual" in q for q in visual)
    assert any("step" in q for q in step)
    assert visual != step


def test_empty_tools_do_not_invent_urls(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr("app.services.strategist_service.youtube_search", lambda *_a, **_k: [])
    monkeypatch.setattr("app.services.strategist_service.article_search", lambda *_a, **_k: [])
    body = client.post(
        "/strategist/plan",
        headers=headers,
        json={"course_id": course_id},
    ).json()
    assert body["resources"] == []
    assert any("no structured hits" in note.lower() for note in body["notes"])
    assert len(body["today"]) == 3
    assert all(not block.get("resource_url") for block in body["today"])


def test_staff_cannot_run_student_strategist():
    headers, user = login(client, "a.benali@aui.ma")
    course_id = next(c["id"] for c in user["courses"] if c["code"] == "CSC 2302")
    denied = client.post(
        "/strategist/plan",
        headers=headers,
        json={"course_id": course_id},
    )
    assert denied.status_code == 403


def test_ta_cannot_run_student_strategist():
    headers, user = login(client, "a.chen@aui.ma")
    course_id = next(c["id"] for c in user["courses"] if c["code"] == "CSC 2302")
    denied = client.post(
        "/strategist/plan",
        headers=headers,
        json={"course_id": course_id},
    )
    assert denied.status_code == 403


def test_focus_picks_largest_weight_gap():
    headers, course_id = student_auth(client, "CSC 3374")
    body = client.post(
        "/strategist/plan",
        headers=headers,
        json={
            "course_id": course_id,
            "grades": [
                {
                    "topic": "Trees & red-black",
                    "score": 62,
                    "weight": 35,
                    "source": "Quiz 4",
                },
                {
                    "topic": "Hashing",
                    "score": 50,
                    "weight": 40,
                    "source": "Assignment 3",
                },
            ],
        },
    ).json()
    assert body["focus"]["topic"] == "Hashing"
    assert body["focus"]["gap"] == 1400.0


def test_student_goal_is_used_and_step_ask_gets_walkthrough():
    headers, course_id = student_auth(client, "CSC 3374")
    client.post(
        "/requests/",
        headers=headers,
        json={
            "text": "Walk me through the steps of hash table insert, first then probe.",
            "anonymous": True,
            "course_id": course_id,
            "course": "CSC 3374",
        },
    )
    body = client.post(
        "/strategist/plan",
        headers=headers,
        json={
            "course_id": course_id,
            "goal": "I only want a step-by-step hashing walkthrough",
            "grades": [
                {
                    "topic": "Hashing",
                    "score": 50,
                    "weight": 40,
                    "source": "Assignment 3",
                }
            ],
        },
    ).json()
    assert body["goal"] == "I only want a step-by-step hashing walkthrough"
    assert body["dossier"]["dominant_style"] == "step_by_step"
    assert "walkthrough" in body["today"][0]["title"].lower()
    assert all(not block.get("resource_url") for block in body["today"])
    assert "3Blue1Brown" not in str(body)
