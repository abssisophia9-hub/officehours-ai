"""Pedagogy Agent Gemini key preference vs Study Agent (GEMINI_API_KEY only)."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from app.ai import agent_policy
from app.ai.gemini_client import complete_gemini
from app.services.revision_service import (
    _llm_gate,
    _pedagogy_gemini_api_key,
    _think,
)

# Placeholders only — never real secrets. Compared in assertions; not logged.
_PEDAGOGY = "pedagogy-placeholder-not-real"
_STUDY = "study-placeholder-not-real"


def setup_function():
    agent_policy.reset_policy_state()


def _arm_gates(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "true")
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    monkeypatch.setenv("OFFICEHOURS_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("OFFICEHOURS_GEMINI_FREE_TIER_ACK", "true")


def test_pedagogy_prefers_own_key(monkeypatch):
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", _PEDAGOGY)
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    assert _pedagogy_gemini_api_key() == _PEDAGOGY


def test_pedagogy_falls_back_to_shared_key(monkeypatch):
    monkeypatch.delenv("PEDAGOGY_GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    assert _pedagogy_gemini_api_key() == _STUDY


def test_pedagogy_blank_own_key_falls_back(monkeypatch):
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", "   ")
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    assert _pedagogy_gemini_api_key() == _STUDY


def test_llm_gate_accepts_pedagogy_key_alone(monkeypatch):
    _arm_gates(monkeypatch)
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", _PEDAGOGY)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert _llm_gate(user_id=1, course_id=1, llm_calls=0) is None


def test_llm_gate_accepts_shared_fallback(monkeypatch):
    _arm_gates(monkeypatch)
    monkeypatch.delenv("PEDAGOGY_GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    assert _llm_gate(user_id=1, course_id=1, llm_calls=0) is None


def test_llm_gate_no_key_when_both_missing(monkeypatch):
    _arm_gates(monkeypatch)
    monkeypatch.delenv("PEDAGOGY_GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert _llm_gate(user_id=1, course_id=1, llm_calls=0) == "no_key"


def test_think_passes_pedagogy_key_to_complete_gemini(monkeypatch):
    _arm_gates(monkeypatch)
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", _PEDAGOGY)
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    seen: dict[str, str | None] = {}

    def capture(_system, _user, **kwargs):
        seen["api_key"] = kwargs.get("api_key")
        return SimpleNamespace(
            text=json.dumps({"action": "stop", "query": None}),
            model="mock-model",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
        )

    monkeypatch.setattr("app.services.revision_service.complete_gemini", capture)
    decision, thinker, _note, meta = _think(
        {
            "live_link_count": 0,
            "remaining_searches": 2,
            "preference": "video",
            "weakest": {"topic": "trees", "level": "high"},
        },
        user_id=1,
        course_id=1,
        llm_calls=0,
        think_fn=None,
        force_rules=False,
    )
    assert thinker == "llm"
    assert decision["action"] == "stop"
    assert meta.get("called") is True
    assert seen["api_key"] == _PEDAGOGY


def test_think_passes_fallback_key_when_pedagogy_unset(monkeypatch):
    _arm_gates(monkeypatch)
    monkeypatch.delenv("PEDAGOGY_GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    seen: dict[str, str | None] = {}

    def capture(_system, _user, **kwargs):
        seen["api_key"] = kwargs.get("api_key")
        return SimpleNamespace(
            text=json.dumps({"action": "stop", "query": None}),
            model="mock-model",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
        )

    monkeypatch.setattr("app.services.revision_service.complete_gemini", capture)
    _think(
        {
            "live_link_count": 0,
            "remaining_searches": 2,
            "preference": "video",
            "weakest": {"topic": "trees", "level": "high"},
        },
        user_id=1,
        course_id=1,
        llm_calls=0,
        think_fn=None,
        force_rules=False,
    )
    assert seen["api_key"] == _STUDY


def test_study_complete_gemini_ignores_pedagogy_key(monkeypatch):
    """Study path (no api_key arg) reads GEMINI_API_KEY only."""
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    monkeypatch.setenv("PEDAGOGY_GEMINI_API_KEY", _PEDAGOGY)
    monkeypatch.setenv("OFFICEHOURS_LLM_RPM", "100")
    headers_seen: list[str] = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": json.dumps({"supports": True})}]}}
                    ],
                    "usageMetadata": {
                        "promptTokenCount": 1,
                        "candidatesTokenCount": 1,
                    },
                    "modelVersion": "gemini-3.5-flash-lite",
                }
            ).encode()

    def fake_urlopen(request, timeout=0):
        headers_seen.append(request.get_header("X-goog-api-key"))
        return _Resp()

    monkeypatch.setattr("app.ai.gemini_client.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("app.ai.gemini_client._throttle", lambda: None)

    complete_gemini("sys", "user", schema={"type": "object", "properties": {}})
    assert len(headers_seen) == 1
    assert headers_seen[0] == _STUDY
    assert headers_seen[0] != _PEDAGOGY


def test_complete_gemini_override_uses_passed_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", _STUDY)
    monkeypatch.setenv("OFFICEHOURS_LLM_RPM", "100")
    headers_seen: list[str] = []

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return json.dumps(
                {
                    "candidates": [
                        {"content": {"parts": [{"text": "{}"}]}}
                    ],
                    "usageMetadata": {},
                }
            ).encode()

    def fake_urlopen(request, timeout=0):
        headers_seen.append(request.get_header("X-goog-api-key"))
        return _Resp()

    monkeypatch.setattr("app.ai.gemini_client.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("app.ai.gemini_client._throttle", lambda: None)

    complete_gemini(
        "sys",
        "user",
        schema={"type": "object", "properties": {}},
        api_key=_PEDAGOGY,
    )
    assert headers_seen[0] == _PEDAGOGY
