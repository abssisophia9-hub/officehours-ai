"""Revision Agent: LLM-in-loop (mocked) + rule-based fallback."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_LLM_ENABLED"] = "false"
os.environ["OFFICEHOURS_REVISION_WEB"] = "false"
os.environ["OFFICEHOURS_LEARNING_STYLE_BACKEND"] = "rules"

from fastapi.testclient import TestClient

from app.ai import agent_policy
from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.revision import RevisionPlanRequest
from app.services.demo_accounts import ensure_demo_accounts
from app.services.revision_service import (
    MAX_CHECKED_LINKS,
    MAX_LLM_CALLS,
    MAX_SEARCHES,
    build_revision_plan,
)
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
    agent_policy.reset_policy_state()


def _plan_payload(course_id, **extra):
    body = {
        "course_id": course_id,
        "preference": "step_by_step",
        "available_minutes_today": 120,
        "grades": [
            {
                "topic": "Trees & red-black",
                "weakness": "high",
                "assignment_kind": "text",
            },
            {
                "topic": "Hashing",
                "weakness": "med",
                "assignment_kind": "text",
            },
        ],
        "deadlines": [
            {"topic": "Trees & red-black", "due_in_days": 3, "label": "Quiz"},
            {"topic": "Hashing", "due_in_days": 7, "label": "Practice"},
        ],
    }
    body.update(extra)
    return body


def _assert_no_scores(body: dict) -> None:
    blob = str(body)
    assert "score" not in blob.lower() or "score" not in body
    for key in ("score", "grades", "weight", "student_name", "student_id"):
        assert key not in body


def test_no_grades_still_returns_plan(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "app.services.revision_service.link_ok",
        lambda *_a, **_k: False,
    )
    response = client.post(
        "/revision/plan",
        headers=headers,
        json={"course_id": course_id, "preference": "conceptual", "grades": []},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mode"] == "rule-based fallback"
    assert "Planning mode: rule-based fallback" in body["mode_label"]
    assert isinstance(body["resources"], list)
    assert len(body["time_slots"]) >= 1
    _assert_no_scores(body)


def test_synthetic_grades_rank_high_weakness_first(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    queries: list[str] = []

    def fake_search(query, **_kwargs):
        queries.append(query)
        return [
            {
                "kind": "article",
                "title": f"Guide to {query}",
                "url": f"https://en.wikipedia.org/wiki/Red-black_tree?q={len(queries)}",
                "snippet": "red-black tree tutorial step by step",
                "query": query,
                "provider": "wikipedia",
            }
        ]

    monkeypatch.setattr("app.services.revision_service.article_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: True)

    response = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["focus_topics"][0] == "Trees & red-black"
    assert "score" not in body
    joined = " ".join(queries).lower()
    assert "trees" in joined or "red-black" in joined or "red" in joined
    assert "step" in joined
    assert all("62" not in q and "score" not in q.lower() for q in queries)
    assert body["ask_draft"]
    assert "Quiet ask" in body["ask_draft"]


def test_failed_link_absent_from_resources(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")

    def fake_search(query, **_kwargs):
        return [
            {
                "kind": "article",
                "title": "Broken red-black page",
                "url": "https://example.invalid/broken-rb",
                "snippet": "red-black tree",
                "query": query,
                "provider": "wikipedia",
            }
        ]

    monkeypatch.setattr("app.services.revision_service.article_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: False)

    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    urls = [r.get("url") for r in body["resources"] if r.get("url")]
    assert "https://example.invalid/broken-rb" not in urls


def test_empty_search_does_not_invent_urls(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda *_a, **_k: [],
    )
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert all(not r.get("url") or r.get("source") == "course KB" for r in body["resources"])
    assert any("no live web" in n.lower() for n in body["notes"])
    assert len(body["time_slots"]) >= 1


def test_llm_off_is_rule_based_and_skips_provider(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("complete_gemini must not be called when LLM off")

    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "false")
    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda *_a, **_k: [],
    )
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["mode"] == "rule-based fallback"
    assert calls["n"] == 0
    assert all(step["thinker"] == "rules" for step in body["iterations"])


def test_not_enrolled_and_staff_forbidden():
    headers, user = login(client, "a.benali@aui.ma")
    course_id = next(c["id"] for c in user["courses"] if c["code"] == "CSC 2302")
    denied = client.post(
        "/revision/plan",
        headers=headers,
        json={"course_id": course_id, "preference": "conceptual"},
    )
    assert denied.status_code == 403

    ta_headers, ta_user = login(client, "a.chen@aui.ma")
    ta_course = next(c["id"] for c in ta_user["courses"] if c["code"] == "CSC 2302")
    ta_denied = client.post(
        "/revision/plan",
        headers=ta_headers,
        json={"course_id": ta_course},
    )
    assert ta_denied.status_code == 403


def test_mocked_llm_search_again_then_resources(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    decisions = iter(
        [
            {"action": "search", "query": "red-black tree step by step"},
            {"action": "search", "query": "red-black tree tutorial"},
            {"action": "stop", "query": None},
        ]
    )

    def think_fn(_obs):
        return next(decisions)

    search_queries: list[str] = []

    def fake_search(query, **_kwargs):
        search_queries.append(query)
        idx = len(search_queries)
        return [
            {
                "kind": "article",
                "title": f"Red-black tree article {idx}",
                "url": f"https://en.wikipedia.org/wiki/Red-black_tree#{idx}",
                "snippet": "red-black tree balancing",
                "query": query,
                "provider": "wikipedia",
            }
        ]

    monkeypatch.setattr("app.services.revision_service.article_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: True)

    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=1,
            think_fn=think_fn,
        )
    finally:
        db.close()

    assert plan.mode == "agent"
    assert "Planning mode: agent" in plan.mode_label
    assert len(search_queries) >= 2
    assert any(step.action == "search" for step in plan.iterations)
    assert any(r.url and "Red-black" in (r.title or "") for r in plan.resources)


def test_mocked_llm_stop_early(monkeypatch):
    calls = {"n": 0}

    def think_fn(_obs):
        calls["n"] += 1
        return {"action": "stop", "query": None}

    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("search should not run")),
    )

    headers, course_id = student_auth(client, "CSC 3374")
    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=1,
            think_fn=think_fn,
        )
    finally:
        db.close()

    assert calls["n"] == 1
    assert plan.iterations[0].action == "stop"
    assert plan.caps["searches"] == 0


def test_invalid_llm_output_falls_back_to_rules(monkeypatch):
    def think_fn(_obs):
        return {"action": "explode", "query": 123}

    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda query, **_k: [
            {
                "kind": "article",
                "title": "Red-black tree",
                "url": "https://en.wikipedia.org/wiki/Red-black_tree",
                "snippet": "red-black tree",
                "query": query,
                "provider": "wikipedia",
            }
        ],
    )
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: True)

    headers, course_id = student_auth(client, "CSC 3374")
    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=1,
            think_fn=think_fn,
        )
    finally:
        db.close()

    assert plan.mode == "rule-based fallback"
    assert any(step.thinker == "rules" for step in plan.iterations)
    assert any("invalid" in (step.note or "").lower() for step in plan.iterations)


def test_invented_url_dropped(monkeypatch):
    """Resources may only use URLs returned by search."""

    def think_fn(_obs):
        return {"action": "search", "query": "red-black tree"}

    def fake_search(query, **_kwargs):
        return [
            {
                "kind": "article",
                "title": "Real hit",
                "url": "https://en.wikipedia.org/wiki/Red-black_tree",
                "snippet": "red-black tree",
                "query": query,
                "provider": "wikipedia",
            },
            {
                "kind": "article",
                "title": "Invented should never stick if not checked path",
                "url": "https://evil.example/invented",
                "snippet": "red-black",
                "query": query,
                "provider": "wikipedia",
            },
        ]

    # Only the Wikipedia URL passes link check; invent a post-hoc resource by
    # also ensuring a non-search URL cannot appear via response mutation path.
    def fake_link(url: str) -> bool:
        return url == "https://en.wikipedia.org/wiki/Red-black_tree"

    monkeypatch.setattr("app.services.revision_service.article_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", fake_link)

    headers, course_id = student_auth(client, "CSC 3374")
    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=1,
            think_fn=think_fn,
        )
    finally:
        db.close()

    urls = [r.url for r in plan.resources if r.url]
    assert "https://en.wikipedia.org/wiki/Red-black_tree" in urls
    assert "https://evil.example/not-from-search" not in urls
    # Failed link-check invent path
    assert "https://evil.example/invented" not in urls


def test_no_key_falls_back(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "true")
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    monkeypatch.setenv("OFFICEHOURS_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("OFFICEHOURS_GEMINI_FREE_TIER_ACK", "true")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def boom(*_a, **_k):
        raise RuntimeError("GEMINI_API_KEY missing")

    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.article_search",
        lambda *_a, **_k: [],
    )

    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["mode"] == "rule-based fallback"
    assert any("fallback" in n.lower() or "gate" in n.lower() or "key" in n.lower() for n in body["notes"]) or any(
        step["thinker"] == "rules" for step in body["iterations"]
    )


def test_caps_hold_with_greedy_llm(monkeypatch):
    llm_calls = {"n": 0}
    searches = {"n": 0}
    checks = {"n": 0}

    def think_fn(_obs):
        llm_calls["n"] += 1
        return {"action": "search", "query": f"red-black tree pass {llm_calls['n']}"}

    def fake_search(query, **_kwargs):
        searches["n"] += 1
        base = searches["n"]
        return [
            {
                "kind": "article",
                "title": f"Red-black {base}-{i}",
                "url": f"https://en.wikipedia.org/wiki/Red-black_tree#{base}-{i}",
                "snippet": "red-black tree",
                "query": query,
                "provider": "wikipedia",
            }
            for i in range(3)
        ]

    def fake_link(_url: str) -> bool:
        checks["n"] += 1
        return True

    monkeypatch.setattr("app.services.revision_service.article_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", fake_link)

    headers, course_id = student_auth(client, "CSC 3374")
    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=1,
            think_fn=think_fn,
        )
    finally:
        db.close()

    assert llm_calls["n"] <= MAX_LLM_CALLS
    assert plan.caps["llm_calls"] <= MAX_LLM_CALLS
    assert searches["n"] <= MAX_SEARCHES
    assert plan.caps["searches"] <= MAX_SEARCHES
    assert checks["n"] <= MAX_CHECKED_LINKS
    assert plan.caps["checked_links"] <= MAX_CHECKED_LINKS
    web = [r for r in plan.resources if r.url]
    assert len(web) <= MAX_CHECKED_LINKS
