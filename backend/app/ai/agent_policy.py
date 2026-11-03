"""Study-agent orchestration.

The pipeline validates the question, retrieves approved course material, and
applies the budgets. A quote check may accept one chunk or refuse. A pass
then takes one entailment verdict: the quote must fully support the answer.
Only an entailment miss may ask the model for one recovery (reformulate,
widen, narrow, or abstain), and only inside a hard cap of three attempts.
Nothing is shown unless the quote check and the entailment check both pass.

``OFFICEHOURS_LLM_ENABLED`` defaults to false. While it is false the agent
is today's retrieval-only path. A limit or an open circuit breaker returns
busy and does not fall back to an unverified retrieval draft.

Numbers and the reason for each default live in ``docs/AGENT_POLICY.md``.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from app.ai.claude_client import (
    ANSWER_CHECK_SYSTEM,
    AnswerCheckClient,
    AnswerCheckResult,
    _material_chunks,
    choose_recovery,
    judge_entailment,
    verify_course_answer,
)
from app.services.rate_limit import RateLimiter

logger = logging.getLogger("officehours.agent_policy")

PROMPT_VERSION = "study-answer-check-v1"
GATE_VERSION = "study-entailment-v1+recovery-v1"

# Student-facing closed set. ``staff`` is the existing below-cutoff reply.
OUTCOMES = ("answer", "refuse", "staff", "busy")

BUSY_ANSWER = (
    "The study assistant is busy right now, so I will not guess from the notes.\n\n"
    "Use Quiet ask (anonymous) or reach out to your TA / professor in office hours."
)

_WINDOWS = RateLimiter()
_CACHE: dict[str, dict[str, Any]] = {}
_BUDGET = {"day": "", "calls": 0, "tokens": 0}
_BREAKER = {"failures": 0, "open_until": 0.0}

_LOG_OUTCOMES = {
    "answered",
    "refused_by_model",
    "failed_closed_error",
    "quota",
    "busy",
    "cache_hit",
}


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def llm_enabled() -> bool:
    return os.getenv("OFFICEHOURS_LLM_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def max_question_chars() -> int:
    return _positive_int("OFFICEHOURS_LLM_MAX_QUESTION_CHARS", 2000)


def max_chunks() -> int:
    return _positive_int("OFFICEHOURS_LLM_MAX_CHUNKS", 3)


def max_input_tokens() -> int:
    return _positive_int("OFFICEHOURS_LLM_MAX_INPUT_TOKENS", 3000)


def max_output_tokens() -> int:
    return _positive_int("OFFICEHOURS_LLM_MAX_OUTPUT_TOKENS", 400)


def max_answer_chars() -> int:
    return _positive_int("OFFICEHOURS_LLM_MAX_ANSWER_CHARS", 600)


def timeout_seconds() -> float:
    return float(_positive_int("OFFICEHOURS_LLM_TIMEOUT_SECONDS", 10))


def user_per_minute() -> int:
    return _positive_int("OFFICEHOURS_LLM_USER_PER_MINUTE", 4)


def user_per_day() -> int:
    return _positive_int("OFFICEHOURS_LLM_USER_PER_DAY", 30)


def course_per_day() -> int:
    return _positive_int("OFFICEHOURS_LLM_COURSE_PER_DAY", 150)


def global_calls_per_day() -> int:
    return _positive_int("OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY", 200)


def global_tokens_per_day() -> int:
    return _positive_int("OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY", 200_000)


def breaker_failures() -> int:
    return _positive_int("OFFICEHOURS_LLM_BREAKER_FAILURES", 3)


def breaker_minutes() -> int:
    return _positive_int("OFFICEHOURS_LLM_BREAKER_MINUTES", 5)


def cache_ttl_seconds() -> int:
    return _positive_int("OFFICEHOURS_LLM_CACHE_TTL_SECONDS", 3600)


def agent_max_attempts() -> int:
    """Hard cap of 2 or 3 quote-check attempts. Default is 3."""
    value = _positive_int("OFFICEHOURS_AGENT_MAX_ATTEMPTS", 3)
    return min(3, max(2, value))


def reset_policy_state() -> None:
    """Clear in-process budgets, the breaker, and the cache. Tests and the eval use this."""
    _WINDOWS.reset()
    _CACHE.clear()
    _BUDGET["day"] = ""
    _BUDGET["calls"] = 0
    _BUDGET["tokens"] = 0
    _BREAKER["failures"] = 0
    _BREAKER["open_until"] = 0.0


def normalize_question(question: str) -> str:
    return " ".join((question or "").lower().split())


def _blank(outcome: str, *, limit: str | None = None) -> dict[str, Any]:
    return {
        "called": False,
        "latency_ms": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model": None,
        "outcome": outcome,
        "error_type": limit,
        "prompt_version": PROMPT_VERSION,
        "limit": limit or "-",
    }


def _log(outcome: str, result: AnswerCheckResult | None, *, limit: str | None) -> None:
    if outcome not in _LOG_OUTCOMES and outcome not in {
        "staff",
        "disabled",
        "flag_off",
        "demo_off",
        "provider_off",
        "ack_off",
    }:
        outcome = "failed_closed_error"
    model = "-"
    latency = 0.0
    input_tokens = 0
    output_tokens = 0
    if result is not None:
        model = result.model or "-"
        latency = result.latency_ms
        input_tokens = result.input_tokens
        output_tokens = result.output_tokens
    logger.info(
        "agent_policy outcome=%s model=%s latency_ms=%.1f input_tokens=%s output_tokens=%s limit=%s",
        outcome,
        model,
        latency,
        input_tokens,
        output_tokens,
        limit or "-",
    )


def _remember(records: list[dict[str, Any]] | None, record: dict[str, Any]) -> None:
    if records is not None:
        records.append(record)


def _busy_response(approved_only: bool):
    from app.services.kb_agent_service import NO_MATCH_HINT
    from app.models.knowledge import AgentAskResponse

    return AgentAskResponse(
        answer=BUSY_ANSWER,
        student_hint=NO_MATCH_HINT,
        confidence=0.0,
        matched_count=0,
        sources=[],
        used_approved_kb_only=approved_only,
        should_seek_help=True,
    )


def _staff_response(sources, approved_only: bool):
    from app.services.kb_agent_service import NO_MATCH_ANSWER, NO_MATCH_HINT
    from app.models.knowledge import AgentAskResponse

    return AgentAskResponse(
        answer=NO_MATCH_ANSWER,
        student_hint=NO_MATCH_HINT,
        confidence=round(sources[0].similarity, 4) if sources else 0.0,
        matched_count=0,
        sources=[],
        used_approved_kb_only=approved_only,
        should_seek_help=True,
    )


def _roll_budget() -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if _BUDGET["day"] != day:
        _BUDGET["day"] = day
        _BUDGET["calls"] = 0
        _BUDGET["tokens"] = 0


def _budget_block() -> str | None:
    _roll_budget()
    if _BUDGET["calls"] >= global_calls_per_day():
        return "global_calls"
    if _BUDGET["tokens"] >= global_tokens_per_day():
        return "global_tokens"
    return None


def _note_spend(input_tokens: int, output_tokens: int) -> None:
    _roll_budget()
    _BUDGET["calls"] += 1
    _BUDGET["tokens"] += max(0, input_tokens) + max(0, output_tokens)


_GUARD_OUTCOMES = {"flag_off", "demo_off", "provider_off", "ack_off"}


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _model_calls_allowed() -> bool:
    """External flag and demo mode. A blocked flag spends nothing."""
    from app.services.demo_mode import demo_mode

    return _truthy("OFFICEHOURS_ALLOW_EXTERNAL_LLM") and demo_mode()


def _provider_ready(answer_checker: AnswerCheckClient | None) -> bool:
    """An injected client skips provider selection. A live call needs a provider.

    Gemini also needs the free-tier acknowledgement. Checked before the budget
    so a missing provider does not spend a slot or open the breaker.
    """
    if answer_checker is not None:
        return True
    provider = os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower()
    if provider not in {"gemini", "claude"}:
        return False
    if provider == "gemini":
        return _truthy("OFFICEHOURS_GEMINI_FREE_TIER_ACK")
    return True


def breaker_open() -> bool:
    return time.monotonic() < _BREAKER["open_until"]


def _note_success() -> None:
    _BREAKER["failures"] = 0
    _BREAKER["open_until"] = 0.0


def _note_failure() -> None:
    _BREAKER["failures"] += 1
    if _BREAKER["failures"] >= breaker_failures():
        _BREAKER["open_until"] = time.monotonic() + breaker_minutes() * 60
        _BREAKER["failures"] = 0


def estimate_input_tokens(question: str, chunks: list[dict[str, Any]]) -> int:
    """Chars/4 of the system prompt plus the JSON the checker actually sends."""
    material = _material_chunks(chunks)
    payload = json.dumps({"question": question, "chunks": material}, ensure_ascii=False)
    return (len(ANSWER_CHECK_SYSTEM) + len(payload)) // 4 + 1


def _window_checks(user_id: int | None, course_id: int | None) -> list[tuple[str, str, int, int]]:
    checks: list[tuple[str, str, int, int]] = []
    if user_id is not None:
        checks.append(("user_per_minute", f"llm-user-min:{user_id}", user_per_minute(), 60))
        checks.append(("user_per_day", f"llm-user-day:{user_id}", user_per_day(), 86_400))
    if course_id is not None:
        checks.append(("course_per_day", f"llm-course-day:{course_id}", course_per_day(), 86_400))
    return checks


def _cache_key(
    course_id: int | None,
    question: str,
    chunks: list[dict[str, Any]],
    model: str,
) -> str:
    identity = "|".join(
        [
            str(course_id if course_id is not None else "-"),
            normalize_question(question),
            ",".join(
                f"{chunk.get('chunk_id')}:{chunk.get('status') or 'approved'}" for chunk in chunks
            ),
            model,
            PROMPT_VERSION,
            GATE_VERSION,
        ]
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _configured_model() -> str:
    provider = os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower()
    if provider == "claude":
        return os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5").strip() or "claude-haiku-5-5"
    from app.ai.gemini_client import gemini_model

    return gemini_model()


def _cache_get(key: str) -> dict[str, Any] | None:
    row = _CACHE.get(key)
    if row is None:
        return None
    if time.monotonic() - float(row["stored_at"]) > cache_ttl_seconds():
        _CACHE.pop(key, None)
        return None
    return row


def invalidate_chunks(chunk_ids: list[int] | tuple[int, ...]) -> None:
    """Drop cached decisions that cited a chunk whose approval changed."""
    if not chunk_ids:
        return
    doomed = {int(chunk_id) for chunk_id in chunk_ids}
    stale = [
        key
        for key, row in _CACHE.items()
        if doomed.intersection(row.get("chunk_ids") or ())
    ]
    for key in stale:
        _CACHE.pop(key, None)


def _policy_outcome(result: AnswerCheckResult) -> str:
    if result.outcome == "passed":
        return "answered"
    if result.outcome == "not_answerable":
        return "refused_by_model"
    return "failed_closed_error"


def _is_failure(result: AnswerCheckResult) -> bool:
    return result.outcome not in {"passed", "not_answerable", *_GUARD_OUTCOMES}


def _live_checker(answer_checker: AnswerCheckClient | None) -> AnswerCheckClient:
    """One client for the quote check, the entailment verdict, and recovery."""
    if answer_checker is not None:
        return answer_checker
    from app.ai.claude_client import AnthropicAnswerCheckClient, GeminiAnswerCheckClient

    provider = os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower()
    if provider == "claude":
        return AnthropicAnswerCheckClient()
    return GeminiAnswerCheckClient()


def _chunks_from_sources(sources, limit: int) -> list[dict[str, Any]]:
    """Chunk dicts the quote check accepts. Six is the widen ceiling."""
    ceiling = min(max(int(limit), 1), 6)
    chunks = []
    for hit in list(sources)[:ceiling]:
        entry = hit.entry
        chunks.append(
            {
                "chunk_id": entry.id,
                "file": entry.source_filename or "",
                "page": entry.page_number,
                "text": entry.answer_draft or "",
                "status": entry.status or "approved",
            }
        )
    return chunks


def _absorb(totals: dict[str, Any], result: AnswerCheckResult) -> None:
    totals["input_tokens"] += max(0, result.input_tokens)
    totals["output_tokens"] += max(0, result.output_tokens)
    totals["latency_ms"] += max(0.0, float(result.latency_ms))


def _spent(result: AnswerCheckResult, totals: dict[str, Any]) -> AnswerCheckResult:
    """Same decision, with the tokens and latency of every call on this question."""
    return AnswerCheckResult(
        outcome=result.outcome,
        called=result.called,
        answer=result.answer,
        quote=result.quote,
        supporting_chunk_id=result.supporting_chunk_id,
        model=result.model,
        input_tokens=totals["input_tokens"],
        output_tokens=totals["output_tokens"],
        latency_ms=totals["latency_ms"],
        error_type=result.error_type,
    )


def _cache_row(result: AnswerCheckResult, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "stored_at": time.monotonic(),
        "outcome": result.outcome,
        "answer": result.answer,
        "quote": result.quote,
        "supporting_chunk_id": result.supporting_chunk_id,
        "model": result.model,
        "chunk_ids": tuple(chunk["chunk_id"] for chunk in chunks),
    }


def _finish_quote_check(
    result: AnswerCheckResult,
    sources,
    chunks: list[dict[str, Any]],
    key: str,
    approved_only: bool,
    check_records: list[dict[str, Any]] | None,
):
    """A quote check that did not pass. Entailment is not called."""
    from app.services.kb_agent_service import _check_miss

    record = result.as_record()
    record["prompt_version"] = PROMPT_VERSION
    record["limit"] = "answer_length" if result.outcome == "answer_too_long" else "-"
    if result.outcome == "not_answerable":
        _CACHE[key] = _cache_row(result, chunks)
    _remember(check_records, record)
    _log(
        _policy_outcome(result),
        result,
        limit=record["limit"] if record["limit"] != "-" else None,
    )
    return _check_miss(sources, approved_only)


def _finish_supported(
    result: AnswerCheckResult,
    sources,
    chunks: list[dict[str, Any]],
    key_chunks: list[dict[str, Any]],
    key: str,
    approved_only: bool,
    check_records: list[dict[str, Any]] | None,
    totals: dict[str, Any],
    attempt: int,
    recoveries: list[str],
):
    """Show the answer only after the quote check and the entailment check pass."""
    from app.services.kb_agent_service import _checked_answer, _cite_entry

    chosen = next(hit for hit in sources if hit.entry.id == result.supporting_chunk_id)
    logged = _spent(result, totals)
    record = logged.as_record()
    record["prompt_version"] = PROMPT_VERSION
    record["outcome"] = "passed"
    record["limit"] = "-"
    record["short_answer"] = result.answer or ""
    record["quote"] = result.quote or ""
    record["citation"] = _cite_entry(chosen.entry)
    record["attempts"] = attempt
    record["recoveries"] = list(recoveries)
    seen_ids = []
    for chunk in list(key_chunks) + list(chunks):
        chunk_id = chunk["chunk_id"]
        if chunk_id not in seen_ids:
            seen_ids.append(chunk_id)
    _CACHE[key] = _cache_row(result, [{"chunk_id": chunk_id} for chunk_id in seen_ids])
    _remember(check_records, record)
    _log("answered", logged, limit=None)
    return _checked_answer(
        sources,
        approved_only=approved_only,
        answer=result.answer or "",
        quote=result.quote or "",
        chunk_id=result.supporting_chunk_id,
    )


def run_study_agent(
    db,
    question: str,
    *,
    top_k: int = 3,
    course_id: int | None = None,
    approved_only: bool = True,
    course_scoped: bool = True,
    answer_checker: AnswerCheckClient | None = None,
    check_records: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
):
    """Fixed pipeline. Retrieval and the 0.42 cutoff stay in the knowledge service."""
    from app.models.knowledge import KnowledgeSearchHit
    from app.services.kb_agent_service import (
        ABSTAIN_ANSWER,
        WEAK_MATCH_CONFIDENCE,
        _checked_answer,
        _check_miss,
        _retrieval_answer,
        search_approved_entries,
    )
    from app.services.knowledge_service import to_out

    enabled = llm_enabled()
    if enabled and len(question or "") > max_question_chars():
        record = _blank("quota", limit="question_length")
        _remember(check_records, record)
        _log("quota", None, limit="question_length")
        return _busy_response(approved_only)

    matches = search_approved_entries(
        db,
        question,
        top_k=top_k,
        course_id=course_id,
        approved_only=approved_only,
        course_scoped=course_scoped,
        course_material_only=True,
    )
    sources = [
        KnowledgeSearchHit(entry=to_out(entry), similarity=round(similarity, 4))
        for entry, similarity in matches
    ]

    if not sources or sources[0].similarity < WEAK_MATCH_CONFIDENCE:
        _remember(check_records, _blank("below_cutoff"))
        _log("staff", None, limit="-")
        return _staff_response(sources, approved_only)

    if not enabled:
        _remember(check_records, _blank("disabled", limit="kill_switch"))
        _log("disabled", None, limit="kill_switch")
        return _retrieval_answer(sources, approved_only)

    chunks = _chunks_from_sources(sources, max_chunks())

    if not _model_calls_allowed() or not _provider_ready(answer_checker):
        result = verify_course_answer(question, chunks, client=answer_checker, emit_log=False)
        record = result.as_record()
        record["prompt_version"] = PROMPT_VERSION
        record["limit"] = result.outcome
        _remember(check_records, record)
        _log(result.outcome, result, limit=result.outcome)
        return _retrieval_answer(sources, approved_only)

    if breaker_open():
        record = _blank("busy", limit="circuit_breaker")
        _remember(check_records, record)
        _log("busy", None, limit="circuit_breaker")
        return _busy_response(approved_only)

    window_checks = _window_checks(user_id, course_id)
    blocked = _budget_block() or _WINDOWS.blocking(window_checks)
    if blocked is None and estimate_input_tokens(question, chunks) > max_input_tokens():
        blocked = "input_tokens"
    if blocked is not None:
        record = _blank("quota", limit=blocked)
        _remember(check_records, record)
        _log("quota", None, limit=blocked)
        return _busy_response(approved_only)

    model_name = _configured_model()
    key = _cache_key(course_id, question, chunks, model_name)
    cached = _cache_get(key)
    if cached is not None:
        result = AnswerCheckResult(
            outcome=cached["outcome"],
            called=False,
            answer=cached.get("answer"),
            quote=cached.get("quote"),
            supporting_chunk_id=cached.get("supporting_chunk_id"),
            model=cached.get("model"),
        )
        record = result.as_record()
        record["prompt_version"] = PROMPT_VERSION
        record["limit"] = "-"
        record["checker_outcome"] = cached["outcome"]
        record["outcome"] = "cache_hit"
        if result.outcome == "passed":
            record["short_answer"] = result.answer or ""
            record["quote"] = result.quote or ""
        _remember(check_records, record)
        _log("cache_hit", result, limit="-")
        if result.outcome == "passed" and result.supporting_chunk_id is not None:
            return _checked_answer(
                sources,
                approved_only=approved_only,
                answer=result.answer or "",
                quote=result.quote or "",
                chunk_id=result.supporting_chunk_id,
            )
        return _check_miss(sources, approved_only)

    spent = _WINDOWS.allow_all(window_checks)
    if spent is not None:
        record = _blank("quota", limit=spent)
        _remember(check_records, record)
        _log("quota", None, limit=spent)
        return _busy_response(approved_only)

    checker = _live_checker(answer_checker)
    search_question = question
    top_k_now = min(top_k, max_chunks())
    key_chunks = list(chunks)
    recoveries: list[str] = []
    totals = {"input_tokens": 0, "output_tokens": 0, "latency_ms": 0.0}

    for attempt in range(1, agent_max_attempts() + 1):
        if attempt > 1:
            if _budget_block() is not None or breaker_open():
                record = _blank("busy", limit=_budget_block() or "circuit_breaker")
                _remember(check_records, record)
                _log("busy", None, limit=record["limit"])
                return _busy_response(approved_only)
            matches = search_approved_entries(
                db,
                search_question,
                top_k=top_k_now,
                course_id=course_id,
                approved_only=approved_only,
                course_scoped=course_scoped,
                course_material_only=True,
            )
            sources = [
                KnowledgeSearchHit(entry=to_out(entry), similarity=round(similarity, 4))
                for entry, similarity in matches
            ]
            if not sources or sources[0].similarity < WEAK_MATCH_CONFIDENCE:
                _remember(check_records, _blank("below_cutoff"))
                _log("staff", None, limit="-")
                return _staff_response(sources, approved_only)
            chunks = _chunks_from_sources(sources, top_k_now)
            if estimate_input_tokens(search_question, chunks) > max_input_tokens():
                record = _blank("quota", limit="input_tokens")
                _remember(check_records, record)
                _log("quota", None, limit="input_tokens")
                return _busy_response(approved_only)

        result = verify_course_answer(search_question, chunks, client=checker, emit_log=False)
        if result.outcome in _GUARD_OUTCOMES:
            record = result.as_record()
            record["prompt_version"] = PROMPT_VERSION
            record["limit"] = result.outcome
            _remember(check_records, record)
            _log(result.outcome, result, limit=result.outcome)
            return _retrieval_answer(sources, approved_only)

        if (
            result.outcome == "passed"
            and isinstance(result.answer, str)
            and len(result.answer) > max_answer_chars()
        ):
            result = AnswerCheckResult(
                outcome="answer_too_long",
                called=True,
                model=result.model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                latency_ms=result.latency_ms,
                error_type="answer_length",
            )

        _absorb(totals, result)
        _note_spend(result.input_tokens, result.output_tokens)
        if result.outcome != "passed" or result.supporting_chunk_id is None:
            if _is_failure(result):
                _note_failure()
            else:
                _note_success()
            return _finish_quote_check(
                result,
                sources,
                chunks,
                key,
                approved_only,
                check_records,
            )

        if _budget_block() is not None:
            record = _blank("busy", limit=_budget_block() or "global_calls")
            _remember(check_records, record)
            _log("busy", None, limit=record["limit"])
            return _busy_response(approved_only)

        entailment = judge_entailment(result.answer or "", result.quote or "", checker)
        _absorb(totals, entailment)
        _note_spend(entailment.input_tokens, entailment.output_tokens)
        if entailment.outcome == "supported":
            _note_success()
            return _finish_supported(
                result,
                sources,
                chunks,
                key_chunks,
                key,
                approved_only,
                check_records,
                totals,
                attempt,
                recoveries,
            )
        if entailment.outcome != "unsupported":
            _note_failure()
            record = _spent(entailment, totals).as_record()
            record["prompt_version"] = PROMPT_VERSION
            record["limit"] = "-"
            record["attempts"] = attempt
            record["recoveries"] = list(recoveries)
            _remember(check_records, record)
            _log("failed_closed_error", _spent(entailment, totals), limit=None)
            return _check_miss(sources, approved_only)

        if attempt >= agent_max_attempts():
            _note_success()
            record = _spent(result, totals).as_record()
            record["prompt_version"] = PROMPT_VERSION
            record["outcome"] = "unsupported"
            record["limit"] = "-"
            record["attempts"] = attempt
            record["recoveries"] = list(recoveries)
            _remember(check_records, record)
            _log("refused_by_model", _spent(result, totals), limit=None)
            return _check_miss(sources, approved_only)

        if _budget_block() is not None or breaker_open():
            record = _blank("busy", limit=_budget_block() or "circuit_breaker")
            _remember(check_records, record)
            _log("busy", None, limit=record["limit"])
            return _busy_response(approved_only)

        recovery = choose_recovery(
            checker,
            question=search_question,
            answer=result.answer or "",
            quote=result.quote or "",
        )
        _absorb(totals, recovery)
        _note_spend(recovery.input_tokens, recovery.output_tokens)
        if recovery.outcome == "abstain":
            _note_success()
            record = _spent(recovery, totals).as_record()
            record["prompt_version"] = PROMPT_VERSION
            record["outcome"] = "abstain"
            record["limit"] = "-"
            record["attempts"] = attempt
            record["recoveries"] = recoveries + ["abstain"]
            _remember(check_records, record)
            _log("refused_by_model", _spent(recovery, totals), limit=None)
            return _check_miss(sources, approved_only, answer=ABSTAIN_ANSWER)
        if recovery.outcome not in {"reformulate", "widen", "narrow"}:
            _note_failure()
            record = _spent(recovery, totals).as_record()
            record["prompt_version"] = PROMPT_VERSION
            record["limit"] = "-"
            record["attempts"] = attempt
            record["recoveries"] = list(recoveries)
            _remember(check_records, record)
            _log("failed_closed_error", _spent(recovery, totals), limit=None)
            return _check_miss(sources, approved_only)

        recoveries.append(recovery.outcome)
        if recovery.outcome == "reformulate":
            search_question = recovery.answer or search_question
        elif recovery.outcome == "widen":
            top_k_now = min(top_k_now + 2, 6)
        else:
            top_k_now = 1

    return _check_miss(sources, approved_only)
