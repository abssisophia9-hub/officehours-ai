#!/usr/bin/env python3
"""Run the Study Agent Orchestrator against a fake checker and print one row per outcome.

No network and no API key. Retrieval is stubbed, so this does not score real
course text and does not change the 0.42 cutoff. Run from the repo root:

    backend/venv/bin/python scripts/demo_orchestration.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
for _secret in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
    os.environ.pop(_secret, None)

from app.ai.agent_policy import reset_policy_state, run_study_agent
from app.models.knowledge import KnowledgeEntry
from app.services.kb_agent_service import (
    CHECK_MISS_ANSWER,
    NO_MATCH_ANSWER,
    search_approved_entries,
)
from app.ai.agent_policy import BUSY_ANSWER

NOW = datetime.now(timezone.utc)
DRAFT = "The stack pop returns the top value."
QUOTE = "returns the top value."
COURSE_ID = 4242
USER_ID = 7

POLICY_KEYS = (
    "OFFICEHOURS_LLM_ENABLED",
    "OFFICEHOURS_ALLOW_EXTERNAL_LLM",
    "OFFICEHOURS_DEMO",
    "OFFICEHOURS_LLM_PROVIDER",
    "OFFICEHOURS_GEMINI_FREE_TIER_ACK",
    "OFFICEHOURS_LLM_MAX_QUESTION_CHARS",
    "OFFICEHOURS_LLM_MAX_CHUNKS",
    "OFFICEHOURS_LLM_MAX_INPUT_TOKENS",
    "OFFICEHOURS_LLM_MAX_OUTPUT_TOKENS",
    "OFFICEHOURS_LLM_MAX_ANSWER_CHARS",
    "OFFICEHOURS_LLM_TIMEOUT_SECONDS",
    "OFFICEHOURS_LLM_USER_PER_MINUTE",
    "OFFICEHOURS_LLM_USER_PER_DAY",
    "OFFICEHOURS_LLM_COURSE_PER_DAY",
    "OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY",
    "OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY",
    "OFFICEHOURS_LLM_BREAKER_FAILURES",
    "OFFICEHOURS_LLM_BREAKER_MINUTES",
    "OFFICEHOURS_LLM_CACHE_TTL_SECONDS",
    "GEMINI_MODEL",
    "ANTHROPIC_MODEL",
)


class FakeClient:
    """Scripted checker. complete() never opens a socket."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = 0

    def complete(self, *, system, user):
        del system, user
        self.calls += 1
        if not self.steps:
            raise AssertionError("the Orchestrator made a model call that was not scripted")
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        text = step if isinstance(step, str) else json.dumps(step)
        return SimpleNamespace(
            text=text,
            model="fake-model",
            input_tokens=10,
            output_tokens=4,
            latency_ms=8.0,
        )


def _entry(**overrides) -> KnowledgeEntry:
    fields = {
        "id": 11,
        "question_text": "Notes — part 1",
        "answer_draft": DRAFT,
        "student_hint": "Check the top pointer.",
        "tags": "",
        "status": "approved",
        "source_filename": "notes.pdf",
        "page_number": 3,
        "chunk_index": 2,
        "course_id": COURSE_ID,
        "entry_kind": "course_material",
        "created_at": NOW,
        "updated_at": NOW,
    }
    fields.update(overrides)
    return KnowledgeEntry(**fields)


def _passed():
    return {
        "answerable": True,
        "supporting_chunk_id": 11,
        "answer": "It returns the top value.",
        "quote": QUOTE,
    }


def _supports():
    return {"supports": True}


def _verified():
    """Quote check, then the entailment yes. A shown answer is two calls."""
    return [_passed(), _supports()]


def _refused():
    return {
        "answerable": False,
        "supporting_chunk_id": None,
        "answer": None,
        "quote": None,
    }


def _arm(overrides: dict[str, str | None] | None = None, *, reset: bool = True) -> None:
    for key in POLICY_KEYS:
        os.environ.pop(key, None)
    os.environ["OFFICEHOURS_LLM_ENABLED"] = "true"
    os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "true"
    os.environ["OFFICEHOURS_DEMO"] = "true"
    os.environ["OFFICEHOURS_LLM_PROVIDER"] = "gemini"
    os.environ["OFFICEHOURS_GEMINI_FREE_TIER_ACK"] = "true"
    for key, value in (overrides or {}).items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
    if reset:
        reset_policy_state()


def _install_search(hits):
    calls = {"n": 0, "kwargs": None}

    def search(db, question, **kwargs):
        del db, question
        calls["n"] += 1
        calls["kwargs"] = kwargs
        return list(hits)

    import app.services.kb_agent_service as kb

    kb.search_approved_entries = search
    return calls


def _ask(question, client, hits, *, user_id=None, course_id=COURSE_ID):
    calls = _install_search(hits)
    records: list[dict] = []
    started = time.perf_counter()
    response = run_study_agent(
        None,
        question,
        course_id=course_id,
        answer_checker=client,
        check_records=records,
        user_id=user_id,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return response, records, calls, elapsed_ms


def _fired(record: dict) -> str:
    limit = record.get("limit") or "-"
    if limit != "-":
        return str(limit)
    error = record.get("error_type")
    return str(error) if error else "-"


def _row(scenario, response, records, client, search_calls, elapsed_ms, *, expect_calls, kind):
    if len(records) != 1:
        raise SystemExit(f"{scenario}: expected one check record, got {len(records)}")
    record = records[0]
    model_calls = 0 if client is None else client.calls
    if model_calls != expect_calls:
        raise SystemExit(f"{scenario}: model calls {model_calls}, expected {expect_calls}")
    _expect_kind(scenario, response, kind)
    return {
        "scenario": scenario,
        "outcome": record.get("outcome"),
        "model_calls": model_calls,
        "fired": _fired(record),
        "latency_ms": round(elapsed_ms, 1),
        "search_calls": search_calls,
    }


def _expect_kind(scenario, response, kind):
    text = response.answer or ""
    if kind == "checked":
        expected = "It returns the top value.\nbased on notes.pdf, p.3 approved by the professor"
        if text != expected or response.should_seek_help or response.matched_count != 1:
            raise SystemExit(f"{scenario}: checked reply was {text!r}")
    elif kind == "miss":
        if text != CHECK_MISS_ANSWER or not response.should_seek_help or response.matched_count != 0:
            raise SystemExit(f"{scenario}: fail-closed reply was {text!r}")
    elif kind == "staff":
        if not text.startswith(NO_MATCH_ANSWER) or not response.should_seek_help:
            raise SystemExit(f"{scenario}: staff reply was {text!r}")
    elif kind == "busy":
        if text != BUSY_ANSWER or not response.should_seek_help:
            raise SystemExit(f"{scenario}: busy reply was {text!r}")
    elif kind == "retrieval":
        if not text.startswith("Based on professor-approved course knowledge") or response.should_seek_help:
            raise SystemExit(f"{scenario}: retrieval reply was {text!r}")
    else:
        raise SystemExit(f"{scenario}: unknown kind {kind}")


def _strong():
    return [(_entry(), 0.8)]


def _once(scenario, question, steps, hits, *, overrides=None, user_id=None, expect_calls, kind, course_id=COURSE_ID):
    _arm(overrides)
    client = None if steps is None else FakeClient(steps)
    response, records, search, elapsed = _ask(
        question, client, hits, user_id=user_id, course_id=course_id
    )
    return _row(
        scenario,
        response,
        records,
        client,
        search["n"],
        elapsed,
        expect_calls=expect_calls,
        kind=kind,
    )


def _spend_then_block(scenario, *, overrides, user_id, course_id, fired, setup_steps=None, setup_calls=1):
    """Spend a one-slot budget, then require the next question to stay off the model.

    A window cap is charged once per question, so the setup question has to
    finish: quote check plus entailment. A global cap of one is spent by the
    quote check, and the entailment call is refused before it starts.
    """
    _arm(overrides)
    setup = FakeClient(list(setup_steps) if setup_steps is not None else [_passed()])
    _ask("What does stack pop return?", setup, _strong(), user_id=user_id, course_id=course_id)
    if setup.calls != setup_calls:
        raise SystemExit(f"{scenario}: setup call count {setup.calls}")
    client = FakeClient([_passed()])
    response, records, search, elapsed = _ask(
        "What does the second stack pop return?",
        client,
        _strong(),
        user_id=user_id,
        course_id=course_id,
    )
    row = _row(
        scenario,
        response,
        records,
        client,
        search["n"],
        elapsed,
        expect_calls=0,
        kind="busy",
    )
    if row["fired"] != fired:
        raise SystemExit(f"{scenario}: fired {row['fired']}, expected {fired}")
    return row


def run_scenarios() -> list[dict]:
    """Return one row per closed-outcome scenario. Restores the search function."""
    rows: list[dict] = []
    original_search = search_approved_entries
    original_urlopen = urllib.request.urlopen

    def _blocked_urlopen(*args, **kwargs):
        del args, kwargs
        raise AssertionError("demo_orchestration tried to use the network")

    urllib.request.urlopen = _blocked_urlopen
    try:
        _arm()
        client = FakeClient(_verified())
        response, records, search, elapsed = _ask(
            "What does stack pop return?", client, _strong(), user_id=USER_ID
        )
        if search["kwargs"].get("course_material_only") is not True:
            raise SystemExit("search was not course-material only")
        rows.append(
            _row(
                "answered_verified_quote",
                response,
                records,
                client,
                search["n"],
                elapsed,
                expect_calls=2,
                kind="checked",
            )
        )
        cached = FakeClient([_passed()])
        response, records, search, elapsed = _ask(
            "What does stack pop return?", cached, _strong(), user_id=USER_ID
        )
        rows.append(
            _row(
                "cache_hit",
                response,
                records,
                cached,
                search["n"],
                elapsed,
                expect_calls=0,
                kind="checked",
            )
        )

        rows.append(
            _once(
                "refused_by_model",
                "Does the note name a passphrase?",
                [_refused()],
                _strong(),
                expect_calls=1,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "below_0.42_cutoff",
                "What is the office-hours room?",
                [_passed()],
                [(_entry(), 0.41)],
                expect_calls=0,
                kind="staff",
            )
        )
        length = _once(
            "question_length",
            "q" * 2001,
            [_passed()],
            _strong(),
            expect_calls=0,
            kind="busy",
        )
        if length["search_calls"] != 0:
            raise SystemExit("question_length searched before refusing")
        if length["fired"] != "question_length":
            raise SystemExit(f"question_length fired {length['fired']}")
        rows.append(length)

        high = {
            "OFFICEHOURS_LLM_USER_PER_MINUTE": "100",
            "OFFICEHOURS_LLM_USER_PER_DAY": "100",
            "OFFICEHOURS_LLM_COURSE_PER_DAY": "100",
            "OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY": "100",
            "OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY": "100000",
        }
        rows.append(
            _spend_then_block(
                "user_per_minute",
                overrides={**high, "OFFICEHOURS_LLM_USER_PER_MINUTE": "1"},
                user_id=USER_ID,
                course_id=COURSE_ID,
                fired="user_per_minute",
                setup_steps=_verified(),
                setup_calls=2,
            )
        )
        rows.append(
            _spend_then_block(
                "user_per_day",
                overrides={**high, "OFFICEHOURS_LLM_USER_PER_DAY": "1"},
                user_id=USER_ID,
                course_id=COURSE_ID,
                fired="user_per_day",
                setup_steps=_verified(),
                setup_calls=2,
            )
        )
        rows.append(
            _spend_then_block(
                "course_per_day",
                overrides={**high, "OFFICEHOURS_LLM_COURSE_PER_DAY": "1"},
                user_id=None,
                course_id=COURSE_ID,
                fired="course_per_day",
                setup_steps=_verified(),
                setup_calls=2,
            )
        )
        rows.append(
            _spend_then_block(
                "global_calls",
                overrides={**high, "OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY": "1"},
                user_id=USER_ID,
                course_id=COURSE_ID,
                fired="global_calls",
            )
        )
        rows.append(
            _spend_then_block(
                "global_tokens",
                overrides={**high, "OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY": "1"},
                user_id=USER_ID,
                course_id=COURSE_ID,
                fired="global_tokens",
            )
        )
        rows.append(
            _once(
                "input_tokens",
                "What does stack pop return?",
                [_passed()],
                _strong(),
                overrides={"OFFICEHOURS_LLM_MAX_INPUT_TOKENS": "1"},
                expect_calls=0,
                kind="busy",
            )
        )

        _arm({"OFFICEHOURS_LLM_BREAKER_FAILURES": "1"})
        failed = FakeClient([RuntimeError("provider down")])
        response, records, search, elapsed = _ask(
            "What does stack pop return?", failed, _strong(), user_id=USER_ID
        )
        rows.append(
            _row(
                "provider_error",
                response,
                records,
                failed,
                search["n"],
                elapsed,
                expect_calls=1,
                kind="miss",
            )
        )
        blocked = FakeClient([_passed()])
        response, records, search, elapsed = _ask(
            "What does a second pop return?", blocked, _strong(), user_id=USER_ID
        )
        breaker = _row(
            "breaker_open",
            response,
            records,
            blocked,
            search["n"],
            elapsed,
            expect_calls=0,
            kind="busy",
        )
        if breaker["fired"] != "circuit_breaker":
            raise SystemExit(f"breaker fired {breaker['fired']}")
        rows.append(breaker)

        rows.append(
            _once(
                "timeout",
                "What does stack pop return?",
                [TimeoutError("timed out"), TimeoutError("timed out")],
                _strong(),
                expect_calls=2,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "invalid_json",
                "What does stack pop return?",
                ["this is not json"],
                _strong(),
                expect_calls=1,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "quote_not_in_chunk",
                "What does stack pop return?",
                [
                    {
                        "answerable": True,
                        "supporting_chunk_id": 11,
                        "answer": "It returns the top value.",
                        "quote": "a sentence that is not in the chunk",
                    }
                ],
                _strong(),
                expect_calls=1,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "unknown_chunk_id",
                "What does stack pop return?",
                [
                    {
                        "answerable": True,
                        "supporting_chunk_id": 999,
                        "answer": "It returns the top value.",
                        "quote": QUOTE,
                    }
                ],
                _strong(),
                expect_calls=1,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "answer_too_long",
                "What does stack pop return?",
                [
                    {
                        "answerable": True,
                        "supporting_chunk_id": 11,
                        "answer": "A" * 601,
                        "quote": QUOTE,
                    }
                ],
                _strong(),
                expect_calls=1,
                kind="miss",
            )
        )
        rows.append(
            _once(
                "kill_switch_off",
                "What does stack pop return?",
                None,
                _strong(),
                overrides={"OFFICEHOURS_LLM_ENABLED": "false"},
                expect_calls=0,
                kind="retrieval",
            )
        )
        rows.append(
            _once(
                "external_flag_off",
                "What does stack pop return?",
                None,
                _strong(),
                overrides={"OFFICEHOURS_ALLOW_EXTERNAL_LLM": "false"},
                expect_calls=0,
                kind="retrieval",
            )
        )
        rows.append(
            _once(
                "demo_mode_off",
                "What does stack pop return?",
                None,
                _strong(),
                overrides={"OFFICEHOURS_DEMO": "false"},
                expect_calls=0,
                kind="retrieval",
            )
        )
        rows.append(
            _once(
                "provider_off",
                "What does stack pop return?",
                None,
                _strong(),
                overrides={"OFFICEHOURS_LLM_PROVIDER": None},
                expect_calls=0,
                kind="retrieval",
            )
        )
        rows.append(
            _once(
                "free_tier_ack_off",
                "What does stack pop return?",
                None,
                _strong(),
                overrides={"OFFICEHOURS_GEMINI_FREE_TIER_ACK": None},
                expect_calls=0,
                kind="retrieval",
            )
        )
    finally:
        urllib.request.urlopen = original_urlopen
        import app.services.kb_agent_service as kb

        kb.search_approved_entries = original_search
        reset_policy_state()
    return rows


def main() -> int:
    rows = run_scenarios()
    print("fake_client network_blocked")
    print("scenario | outcome | model_calls | fired | latency_ms")
    for row in rows:
        print(
            f"{row['scenario']} | {row['outcome']} | {row['model_calls']} | "
            f"{row['fired']} | {row['latency_ms']:.1f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
