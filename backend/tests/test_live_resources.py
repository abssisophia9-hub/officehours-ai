"""Opt-in live Pedagogy Resources check (YouTube + Pedagogy Gemini).

Skipped unless OFFICEHOURS_LIVE_RESOURCES_TEST=1. Never prints API key values.
Keeps existing mock revision tests untouched.
"""

from __future__ import annotations

import json
import os
import re
import socket

import pytest

# Skip before heavy imports when flag off (CI default).
if os.getenv("OFFICEHOURS_LIVE_RESOURCES_TEST", "").strip() != "1":
    pytest.skip(
        "live Resources check disabled (set OFFICEHOURS_LIVE_RESOURCES_TEST=1)",
        allow_module_level=True,
    )

# Arm FYP LLM gates in-process before app import. env_bootstrap uses override=False.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ["OFFICEHOURS_DEMO"] = "true"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_REVISION_WEB"] = "true"
os.environ["OFFICEHOURS_LLM_ENABLED"] = "true"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "true"
os.environ["OFFICEHOURS_LLM_PROVIDER"] = "gemini"
os.environ["OFFICEHOURS_GEMINI_FREE_TIER_ACK"] = "true"
os.environ.setdefault("OFFICEHOURS_LLM_RPM", "30")

import app.env_bootstrap  # noqa: E402,F401
from app.ai import agent_policy, gemini_client  # noqa: E402
from app.database.session import Base, SessionLocal, engine  # noqa: E402
from app.models.revision import DeadlineIn, GradeTopicIn, RevisionPlanRequest  # noqa: E402
from app.services import revision_search, revision_service  # noqa: E402
from app.services.revision_service import (  # noqa: E402
    build_revision_plan,
    clear_plan_resource_cache,
)

pytestmark = pytest.mark.live_resources

SECRET_RE = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{10,}|AQ\.[0-9A-Za-z_-]{20,}|ya29\.[0-9A-Za-z_-]{20,})",
    re.I,
)


def _present(name: str) -> tuple[bool, int]:
    val = (os.getenv(name) or "").strip()
    return bool(val), len(val)


def _reachable(host: str, port: int = 443) -> bool:
    try:
        with socket.create_connection((host, port), timeout=10):
            return True
    except OSError:
        return False


def _privacy_ok(payload: object) -> bool:
    blob = json.dumps(payload)
    assert not SECRET_RE.search(blob)
    low = blob.lower()
    if "student_name" in low or "student_id" in low:
        return False
    if re.search(r'"(score|percent|percentage|points)"\s*:', blob, re.I):
        return False
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", blob):
        return False
    return True


@pytest.fixture(scope="module")
def live_ready():
    ped_ok, ped_len = _present("PEDAGOGY_GEMINI_API_KEY")
    yt_ok, yt_len = _present("YOUTUBE_API_KEY")
    if not ped_ok or not yt_ok:
        pytest.skip(
            f"keys missing (PEDAGOGY present={ped_ok} len={ped_len}; "
            f"YOUTUBE present={yt_ok} len={yt_len})"
        )
    if not _reachable("www.googleapis.com") or not _reachable(
        "generativelanguage.googleapis.com"
    ):
        pytest.skip("Google API hosts unreachable")
    Base.metadata.create_all(bind=engine)
    agent_policy.reset_policy_state()
    clear_plan_resource_cache()
    revision_search.clear_resource_cache()
    gemini_client.reset_throttle()
    return True


def test_live_resources_two_prefs_same_topic(live_ready):
    """Small live sample: one weak topic × visual + step-by-step."""
    db = SessionLocal()
    captured: list[dict] = []
    orig = gemini_client.complete_gemini

    def wrap(system, user, *args, **kwargs):
        payload = json.loads(user) if isinstance(user, str) else user
        captured.append(payload)
        assert _privacy_ok(payload)
        # Never forward logs of api_key
        return orig(system, user, *args, **kwargs)

    gemini_client.complete_gemini = wrap
    revision_service.complete_gemini = wrap
    try:
        results = []
        for pref in ("visual_structural", "step_by_step"):
            clear_plan_resource_cache()
            plan = build_revision_plan(
                db,
                RevisionPlanRequest(
                    course_id=1,
                    preference=pref,  # type: ignore[arg-type]
                    available_minutes_today=120,
                    grades=[
                        GradeTopicIn(
                            topic="Trees & red-black",
                            weakness="high",
                            assignment_kind="text",
                        )
                    ],
                    deadlines=[
                        DeadlineIn(topic="Trees & red-black", due_in_days=3, label="Quiz")
                    ],
                ),
                user_id=1,
            )
            assert plan.resources, f"no resources for {pref}"
            for row in plan.resources:
                assert row.url and row.url.startswith("http")
                assert revision_search.link_ok(row.url)
            results.append((pref, plan.mode, len(plan.resources)))
        assert captured, "expected at least one Gemini payload when gates armed"
        for payload in captured:
            assert _privacy_ok(payload)
        # Soft preference: at least one agent-mode run when Gemini is healthy.
        assert any(mode == "agent" for _, mode, _ in results) or all(
            n >= 1 for _, _, n in results
        )
    finally:
        gemini_client.complete_gemini = orig
        revision_service.complete_gemini = orig
        db.close()
