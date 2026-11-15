"""Revision Agent: LLM-in-loop (mocked) + rule-based fallback."""

import os
import re

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
from app.services.revision_search import (
    clear_resource_cache,
    looks_like_clickbait,
    looks_like_short,
    youtube_search,
)
from app.services.revision_service import (
    MAX_CHECKED_LINKS,
    MAX_LLM_CALLS,
    MAX_RESOURCES,
    MAX_SEARCHES,
    build_revision_plan,
    clear_plan_resource_cache,
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
    clear_resource_cache()
    clear_plan_resource_cache()


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
        "app.services.revision_service.resource_search",
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
    assert "Plan built from your scores and preference" in body["mode_label"]
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

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
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

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
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
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["resources"] == []
    assert any(
        "couldn't find resources right now" in n.lower() for n in body["notes"]
    )
    assert len(body["time_slots"]) >= 1


def test_resources_are_web_only_never_course_kb(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["resources"] == []
    assert all(r.get("source") != "course KB" for r in body["resources"])
    assert not any("course kb" in (n or "").lower() for n in body["notes"])


def test_preferences_drive_different_queries(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    seen: dict[str, list[str]] = {}

    def fake_search(query, **_kwargs):
        return []

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)

    for pref in ("visual_structural", "step_by_step"):
        queries: list[str] = []

        def capture(query, **_kwargs):
            queries.append(query)
            return []

        monkeypatch.setattr("app.services.revision_service.resource_search", capture)
        body = client.post(
            "/revision/plan",
            headers=headers,
            json=_plan_payload(course_id, preference=pref),
        ).json()
        assert body["preference"] == pref
        assert queries
        seen[pref] = list(queries)

    visual = " ".join(seen["visual_structural"]).lower()
    steps = " ".join(seen["step_by_step"]).lower()
    assert "diagram" in visual or "visualization" in visual
    assert "step" in steps
    assert seen["visual_structural"] != seen["step_by_step"]


def test_fallback_empty_state_copy(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "false")
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["mode"] == "rule-based fallback"
    assert body["resources"] == []
    assert (
        "We couldn't find resources right now. Try again later." in body["notes"]
    )


def test_plan_slots_follow_deadline_horizon(monkeypatch):
    """Slot day_offsets follow chosen deadlines — not a hardcoded 7-day window."""
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    for horizon in (1, 3, 7, 14, 30):
        body = client.post(
            "/revision/plan",
            headers=headers,
            json=_plan_payload(
                course_id,
                deadlines=[
                    {
                        "topic": "Trees & red-black",
                        "due_in_days": max(1, horizon // 3) or 1,
                        "label": "Primary focus",
                    },
                    {
                        "topic": "Hashing",
                        "due_in_days": horizon,
                        "label": "Second focus",
                    },
                ],
            ),
        ).json()
        offsets = [int(s["day_offset"]) for s in body["time_slots"]]
        assert offsets, f"expected slots for horizon={horizon}"
        assert max(offsets) == horizon, (
            f"horizon={horizon} produced max day_offset={max(offsets)}"
        )
        assert all(0 <= d <= horizon for d in offsets)


def test_llm_off_is_rule_based_and_skips_provider(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("complete_gemini must not be called when LLM off")

    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "false")
    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
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

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
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
    assert "Plan built with the Pedagogy Agent" in plan.mode_label
    assert len(search_queries) >= 2
    assert any(step.action == "search" for step in plan.iterations)
    assert any(r.url and "Red-black" in (r.title or "") for r in plan.resources)


def test_mocked_llm_stop_early(monkeypatch):
    calls = {"n": 0}

    def think_fn(_obs):
        calls["n"] += 1
        return {"action": "stop", "query": None}

    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
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
        "app.services.revision_service.resource_search",
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
    # Iteration notes stay student-safe (no invalid-model / llm jargon).
    assert any(
        "simple planner" in (step.note or "").lower()
        or "scores and preference" in (step.note or "").lower()
        for step in plan.iterations
    )
    assert not any(
        re.search(r"llm_|invalid model|fallback|gate:", step.note or "", re.I)
        for step in plan.iterations
    )


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

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
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
    monkeypatch.delenv("PEDAGOGY_GEMINI_API_KEY", raising=False)

    def boom(*_a, **_k):
        raise RuntimeError("GEMINI_API_KEY missing")

    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
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

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
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


def _arm_revision_llm(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "true")
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    monkeypatch.setenv("OFFICEHOURS_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("OFFICEHOURS_GEMINI_FREE_TIER_ACK", "true")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-not-real")


def _fill_window(user_id: int | None, course_id: int | None, *, times: int) -> None:
    checks = agent_policy._window_checks(user_id, course_id)
    for _ in range(times):
        assert agent_policy._WINDOWS.allow_all(checks) is None


def test_per_user_cap_falls_back_to_rules(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    _arm_revision_llm(monkeypatch)
    user_id = 9001
    _fill_window(user_id, course_id, times=agent_policy.user_per_minute())

    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("complete_gemini must not run when user window is full")

    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )

    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=user_id,
        )
    finally:
        db.close()

    assert calls["n"] == 0
    assert plan.mode == "rule-based fallback"
    assert "Plan built from your scores and preference" in plan.mode_label
    assert any(
        "scores and preference" in (n or "").lower() or "unavailable" in (n or "").lower()
        for n in plan.notes
    ) or any(step.thinker == "rules" for step in plan.iterations)
    assert not any(
        re.search(r"user_per_minute|budget:|llm_|gate:", text or "", re.I)
        for text in list(plan.notes) + [step.note for step in plan.iterations]
    )


def test_per_course_cap_falls_back_to_rules(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    _arm_revision_llm(monkeypatch)
    user_id = 9002
    # Fill only the course day window (leave per-user room empty by using a fresh user).
    course_checks = [
        check
        for check in agent_policy._window_checks(user_id, course_id)
        if check[0] == "course_per_day"
    ]
    assert course_checks
    for _ in range(agent_policy.course_per_day()):
        assert agent_policy._WINDOWS.allow_all(course_checks) is None

    calls = {"n": 0}

    def boom(*_a, **_k):
        calls["n"] += 1
        raise AssertionError("complete_gemini must not run when course window is full")

    monkeypatch.setattr("app.services.revision_service.complete_gemini", boom)
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )

    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id)),
            user_id=user_id,
        )
    finally:
        db.close()

    assert calls["n"] == 0
    assert plan.mode == "rule-based fallback"
    assert "Plan built from your scores and preference" in plan.mode_label
    assert any(step.thinker == "rules" for step in plan.iterations)
    assert not any(
        re.search(r"course_per_day|budget:|llm_|gate:", text or "", re.I)
        for text in list(plan.notes) + [step.note for step in plan.iterations]
    )


def test_youtube_missing_key_returns_empty(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setenv("OFFICEHOURS_REVISION_WEB", "true")
    assert youtube_search("red-black tree tutorial") == []


def test_shorts_and_clickbait_filters():
    assert looks_like_short("Cool tip #shorts", "https://www.youtube.com/watch?v=abc")
    assert looks_like_short("Normal", "https://youtu.be/abc", duration_seconds=45)
    assert not looks_like_short(
        "Red-black trees explained",
        "https://www.youtube.com/watch?v=abc",
        duration_seconds=600,
    )
    assert looks_like_clickbait("YOU WONT BELIEVE THIS TREE HACK!!!")
    assert not looks_like_clickbait("Red-black tree insertion tutorial")


def test_rank_fn_only_picks_search_urls(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")

    def think_fn(_obs):
        return {"action": "search", "query": "red-black tree worked tutorial"}

    def fake_search(query, **_kwargs):
        return [
            {
                "kind": "video",
                "title": "Red-black tree animation",
                "url": "https://www.youtube.com/watch?v=realvideo1",
                "snippet": "animated diagram of red-black trees",
                "query": query,
                "provider": "youtube",
                "channel": "CS Academy",
            },
            {
                "kind": "article",
                "title": "Red-black tree",
                "url": "https://en.wikipedia.org/wiki/Red-black_tree",
                "snippet": "red-black tree data structure",
                "query": query,
                "provider": "wikipedia",
                "channel": "Wikipedia",
            },
        ]

    def rank_fn(payload):
        # Invent an id that does not exist - must be ignored.
        return {
            "picks": [
                {"id": "2", "why": "Clear article overview for this topic."},
                {"id": "99", "why": "https://evil.example/fake"},
                {"id": "1", "why": "Animated walkthrough for a visual learner."},
            ]
        }

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: True)

    db = SessionLocal()
    try:
        plan = build_revision_plan(
            db,
            RevisionPlanRequest(**_plan_payload(course_id, preference="visual_structural")),
            user_id=1,
            think_fn=think_fn,
            rank_fn=rank_fn,
        )
    finally:
        db.close()

    urls = [r.url for r in plan.resources if r.url]
    assert "https://evil.example/fake" not in urls
    assert "https://en.wikipedia.org/wiki/Red-black_tree" in urls
    assert "https://www.youtube.com/watch?v=realvideo1" in urls
    assert all(u in {
        "https://en.wikipedia.org/wiki/Red-black_tree",
        "https://www.youtube.com/watch?v=realvideo1",
    } for u in urls)
    assert len(plan.resources) <= MAX_RESOURCES
    assert all("http" not in (r.why or "").lower() or "https://evil" not in (r.why or "") for r in plan.resources)


def test_missing_youtube_and_empty_search_empty_state(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    body = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id),
    ).json()
    assert body["resources"] == []
    assert (
        "We couldn't find resources right now. Try again later." in body["notes"]
    )


def test_preferences_drive_different_resource_results(monkeypatch):
    headers, course_id = student_auth(client, "CSC 3374")

    def fake_search(query, **_kwargs):
        q = query.lower()
        if "animated" in q or "diagram" in q or "visualization" in q:
            return [
                {
                    "kind": "video",
                    "title": "Red-black tree animated diagram",
                    "url": "https://www.youtube.com/watch?v=visualpref",
                    "snippet": "animated diagram red-black",
                    "query": query,
                    "provider": "youtube",
                    "channel": "Visual CS",
                }
            ]
        return [
            {
                "kind": "video",
                "title": "Red-black tree worked tutorial step by step",
                "url": "https://www.youtube.com/watch?v=steppref",
                "snippet": "worked tutorial step by step red-black",
                "query": query,
                "provider": "youtube",
                "channel": "Tutor CS",
            }
        ]

    monkeypatch.setattr("app.services.revision_service.resource_search", fake_search)
    monkeypatch.setattr("app.services.revision_service.link_ok", lambda *_a, **_k: True)

    visual = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id, preference="visual_structural"),
    ).json()
    clear_plan_resource_cache()
    steps = client.post(
        "/revision/plan",
        headers=headers,
        json=_plan_payload(course_id, preference="step_by_step"),
    ).json()

    v_urls = [r["url"] for r in visual["resources"] if r.get("url")]
    s_urls = [r["url"] for r in steps["resources"] if r.get("url")]
    assert v_urls != s_urls
    assert any("visualpref" in (u or "") for u in v_urls)
    assert any("steppref" in (u or "") for u in s_urls)


def test_policy_log_modes_omit_grades_and_names(monkeypatch, caplog):
    headers, course_id = student_auth(client, "CSC 3374")
    monkeypatch.setattr(
        "app.services.revision_service.resource_search",
        lambda *_a, **_k: [],
    )
    monkeypatch.setattr(
        "app.services.revision_service.link_ok",
        lambda *_a, **_k: False,
    )

    def _policy_lines():
        return [
            record.getMessage()
            for record in caplog.records
            if record.name == "officehours.agent_policy"
        ]

    with caplog.at_level("INFO", logger="officehours.agent_policy"):
        # Rule-based fallback path (LLM off default).
        fallback = client.post(
            "/revision/plan",
            headers=headers,
            json=_plan_payload(course_id),
        )
        assert fallback.status_code == 200
        assert fallback.json()["mode"] == "rule-based fallback"

        # Agent path via injected thinker (no provider HTTP).
        def think_fn(_obs):
            return {"action": "stop", "query": None}

        db = SessionLocal()
        try:
            agent_plan = build_revision_plan(
                db,
                RevisionPlanRequest(**_plan_payload(course_id)),
                user_id=1,
                think_fn=think_fn,
            )
        finally:
            db.close()
        assert agent_plan.mode == "agent"

    lines = _policy_lines()
    assert any("limit=rule-based fallback:" in line for line in lines)
    assert any("limit=agent:" in line for line in lines)
    blob = "\n".join(lines).lower()
    assert "sara" not in blob
    assert "youssef" not in blob
    assert "student_name" not in blob
    assert "score" not in blob
    assert "62" not in blob
    assert "red-black tree balancing" not in blob
