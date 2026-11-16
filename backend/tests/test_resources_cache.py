"""Resources YouTube cache: shared topic pool, TTL, persist, singleflight, failures, quota."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_LLM_ENABLED"] = "false"
os.environ["OFFICEHOURS_REVISION_WEB"] = "true"
os.environ["OFFICEHOURS_LEARNING_STYLE_BACKEND"] = "rules"

import app.services.revision_search as revision_search
from app.models.revision import RevisionPlanRequest
from app.services.revision_search import (
    clear_resource_cache,
    reset_youtube_unit_counters,
    resource_search,
    youtube_topic_pool,
    youtube_unit_counters,
)
from app.services.revision_service import (
    build_revision_plan,
    clear_plan_resource_cache,
)


SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


def _fake_search_payload(*video_ids: str):
    items = []
    for i, vid in enumerate(video_ids, start=1):
        items.append(
            {
                "id": {"videoId": vid},
                "snippet": {
                    "title": f"Red-black tree tutorial {i}",
                    "channelTitle": f"Channel {i}",
                    "description": "red-black tree data structure tutorial",
                },
            }
        )
    return {"items": items}


def _fake_videos_payload(*video_ids: str):
    return {
        "items": [
            {"id": vid, "contentDetails": {"duration": "PT10M"}}
            for vid in video_ids
        ]
    }


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | list | None = None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise revision_search.httpx.HTTPStatusError(
                "err",
                request=revision_search.httpx.Request("GET", "https://example.test"),
                response=revision_search.httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


def setup_function(tmp_path_factory=None):
    # pytest injects tmp_path via fixtures on test functions; setup_function
    # alone cannot. Each test calls _prep(tmp_path).
    pass


def _prep(monkeypatch, tmp_path: Path):
    cache_path = tmp_path / "resources_cache.json"
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-youtube-key-not-real")
    monkeypatch.setenv("OFFICEHOURS_REVISION_WEB", "true")
    monkeypatch.setenv("OFFICEHOURS_YOUTUBE_CACHE_TTL_SECONDS", "3600")
    monkeypatch.setenv("OFFICEHOURS_RESOURCES_FAILURE_CACHE_TTL_SECONDS", "30")
    monkeypatch.setenv("OFFICEHOURS_YOUTUBE_SEARCH_DAILY_LIMIT", "100")
    monkeypatch.setenv("OFFICEHOURS_YOUTUBE_OTHER_UNITS_DAILY_LIMIT", "10000")
    monkeypatch.setattr(revision_search, "_CACHE_PATH", cache_path)
    revision_search._persist_loaded = False
    clear_resource_cache()
    clear_plan_resource_cache()
    reset_youtube_unit_counters()
    return cache_path


def _install_http(monkeypatch, handler):
    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url, params=None):
            return handler(url, params or {})

    monkeypatch.setattr(revision_search, "_client", lambda **k: _FakeClient())


def test_one_youtube_search_per_topic_shared_across_preferences(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    calls = {"search": 0, "videos": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            return _FakeResponse(200, _fake_search_payload("aaa111", "bbb222"))
        if url.startswith(VIDEOS_URL):
            calls["videos"] += 1
            return _FakeResponse(200, _fake_videos_payload("aaa111", "bbb222"))
        return _FakeResponse(404, {})

    _install_http(monkeypatch, handler)

    a = resource_search(
        "Trees animated diagram visualization",
        preference="visual_structural",
        topic="Trees & red-black",
        max_results=4,
    )
    b = resource_search(
        "Trees worked tutorial step by step",
        preference="step_by_step",
        topic="Trees & red-black",
        max_results=4,
    )
    assert calls["search"] == 1
    assert calls["videos"] == 1
    assert {h["url"] for h in a if h.get("kind") == "video"} == {
        h["url"] for h in b if h.get("kind") == "video"
    }
    counters = youtube_unit_counters()
    assert counters["search_list"] == 1
    assert counters["videos_list"] == 1
    assert counters["cache_hits_youtube"] >= 1


def test_youtube_cache_survives_restart(monkeypatch, tmp_path):
    cache_path = _prep(monkeypatch, tmp_path)
    calls = {"search": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            return _FakeResponse(200, _fake_search_payload("ccc333"))
        if url.startswith(VIDEOS_URL):
            return _FakeResponse(200, _fake_videos_payload("ccc333"))
        return _FakeResponse(404, {})

    _install_http(monkeypatch, handler)
    first = youtube_topic_pool("Hashing", max_results=3)
    assert first and calls["search"] == 1
    assert cache_path.is_file()

    # Simulate process restart: clear in-memory state but keep the file.
    revision_search._cache.clear()
    revision_search._inflight.clear()
    revision_search._persist_loaded = False
    reset_youtube_unit_counters()

    second = youtube_topic_pool("Hashing", max_results=3)
    assert calls["search"] == 1
    assert [h["url"] for h in second] == [h["url"] for h in first]
    assert youtube_unit_counters()["cache_hits_youtube"] >= 1


def test_singleflight_identical_simultaneous_requests(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    started = threading.Event()
    release = threading.Event()
    calls = {"search": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            started.set()
            release.wait(timeout=2)
            return _FakeResponse(200, _fake_search_payload("ddd444"))
        if url.startswith(VIDEOS_URL):
            return _FakeResponse(200, _fake_videos_payload("ddd444"))
        return _FakeResponse(404, {})

    _install_http(monkeypatch, handler)

    results: list[list] = [[], []]

    def worker(idx: int):
        results[idx] = youtube_topic_pool("Amortized analysis", max_results=2)

    t1 = threading.Thread(target=worker, args=(0,))
    t2 = threading.Thread(target=worker, args=(1,))
    t1.start()
    assert started.wait(timeout=2)
    t2.start()
    time.sleep(0.05)
    release.set()
    t1.join(timeout=3)
    t2.join(timeout=3)
    assert calls["search"] == 1
    assert results[0] and results[1]
    assert [h["url"] for h in results[0]] == [h["url"] for h in results[1]]


def test_failures_cached_briefly(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    monkeypatch.setenv("OFFICEHOURS_RESOURCES_FAILURE_CACHE_TTL_SECONDS", "60")
    calls = {"search": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            return _FakeResponse(403, {"error": {"message": "quota"}})
        return _FakeResponse(404, {})

    _install_http(monkeypatch, handler)
    assert youtube_topic_pool("Trees & red-black") == []
    assert youtube_topic_pool("Trees & red-black") == []
    assert calls["search"] == 1


def test_quota_guard_blocks_near_limit(monkeypatch, tmp_path):
    _prep(monkeypatch, tmp_path)
    monkeypatch.setenv("OFFICEHOURS_YOUTUBE_SEARCH_DAILY_LIMIT", "6")  # headroom 5 → stop at 1
    clear_resource_cache()
    reset_youtube_unit_counters()
    # Spend the only allowed call.
    revision_search._quota_search_list = 1
    revision_search._persist_loaded = True
    calls = {"search": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            return _FakeResponse(200, _fake_search_payload("eee555"))
        return _FakeResponse(404, {})

    _install_http(monkeypatch, handler)
    assert youtube_topic_pool("Trees & red-black") == []
    assert calls["search"] == 0
    assert youtube_unit_counters()["search_list_blocked_quota"] >= 1


def test_repeat_plan_build_costs_zero_youtube_units(monkeypatch, tmp_path):
    """MEASURED: cold plan burns search+videos units; warm repeat burns 0."""
    # Import app.main so all ORM models register on Base before create_all
    # (isolated runs of this file otherwise miss agent_gold_labels, etc.).
    from app.main import app as _app  # noqa: F401
    from app.database.session import SessionLocal
    from app.services.demo_accounts import ensure_demo_accounts
    from app.database.session import Base, engine

    _prep(monkeypatch, tmp_path)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()

    calls = {"search": 0, "videos": 0}

    def handler(url, params):
        if url.startswith(SEARCH_URL):
            calls["search"] += 1
            return _FakeResponse(200, _fake_search_payload("fff666", "ggg777"))
        if url.startswith(VIDEOS_URL):
            calls["videos"] += 1
            return _FakeResponse(200, _fake_videos_payload("fff666", "ggg777"))
        # Articles / link checks
        return _FakeResponse(200, [])

    _install_http(monkeypatch, handler)
    monkeypatch.setattr(
        "app.services.revision_service.link_ok",
        lambda *_a, **_k: True,
    )
    # Avoid Wikipedia/DDG network in this measurement.
    monkeypatch.setattr(
        revision_search,
        "article_search",
        lambda *_a, **_k: [
            {
                "kind": "article",
                "title": "Red-black tree",
                "url": "https://en.wikipedia.org/wiki/Red-black_tree",
                "snippet": "red-black tree data structure",
                "query": "trees",
                "provider": "wikipedia",
                "channel": "Wikipedia",
            }
        ],
    )

    payload = RevisionPlanRequest(
        course_id=1,
        preference="step_by_step",
        available_minutes_today=120,
        grades=[
            {
                "topic": "Trees & red-black",
                "weakness": "high",
                "assignment_kind": "text",
            }
        ],
        deadlines=[{"topic": "Trees & red-black", "due_in_days": 3, "label": "Quiz"}],
    )

    reset_youtube_unit_counters()
    db = SessionLocal()
    try:
        plan1 = build_revision_plan(db, payload, user_id=1)
    finally:
        db.close()
    cold = youtube_unit_counters()
    cold_search = cold["search_list"]
    cold_videos = cold["videos_list"]
    assert cold_search >= 1
    assert plan1.resources

    # Repeat identical plan (same topic+preference): plan cache → 0 new YT units.
    reset_youtube_unit_counters()
    db = SessionLocal()
    try:
        plan2 = build_revision_plan(db, payload, user_id=1)
    finally:
        db.close()
    warm = youtube_unit_counters()
    assert warm["search_list"] == 0
    assert warm["videos_list"] == 0
    assert plan2.resources

    # Different preference, same topic: shared YT pool → still 0 new search.list.
    clear_plan_resource_cache()
    reset_youtube_unit_counters()
    payload2 = payload.model_copy(update={"preference": "visual_structural"})
    db = SessionLocal()
    try:
        plan3 = build_revision_plan(db, payload2, user_id=1)
    finally:
        db.close()
    other_pref = youtube_unit_counters()
    assert other_pref["search_list"] == 0
    assert other_pref["videos_list"] == 0
    assert plan3.resources

    evidence = {
        "cold_search_list": cold_search,
        "cold_videos_list": cold_videos,
        "repeat_same_pref_search_list": 0,
        "repeat_same_pref_videos_list": 0,
        "other_pref_same_topic_search_list": 0,
        "other_pref_same_topic_videos_list": 0,
        "http_search_calls_total": calls["search"],
        "note": "Official units: search.list=1/call (100/day bucket); videos.list=1/call.",
    }
    # Write under pytest tmp_path only — never hardcode /cursor/stores (CI has no write access).
    out = tmp_path / "repeat-plan-units-measured.json"
    out.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["cold_search_list"] == cold_search


def test_longer_youtube_ttl_default():
    assert revision_search._DEFAULT_YOUTUBE_CACHE_TTL == 21600
    assert revision_search.youtube_cache_ttl_seconds() >= 1800
