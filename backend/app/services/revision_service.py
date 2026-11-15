"""Revision Agent - observe → think → act(search) → check (max 3).

LLM think uses Gemini when gates allow; otherwise rule-based fallback.
Payloads never include names, scores, or grades - topic labels, weakness
level, preference, and public search titles/snippets only.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Callable
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.ai import agent_policy as policy
from app.ai.gemini_client import (
    DailyQuotaError,
    RateLimitExhausted,
    complete_gemini,
    gemini_model,
)
from app.ai.learning_style import LEARNING_STYLES
from app.models.revision import (
    DeadlineIn,
    GradeTopicIn,
    IterationTraceOut,
    ResourceOut,
    RevisionPlanOut,
    RevisionPlanRequest,
    TimeSlotOut,
)
from app.services.revision_search import link_ok, resource_search

logger = logging.getLogger("officehours.revision")

MAX_ITERATIONS = 3
MAX_LLM_CALLS = 3
MAX_SEARCHES = 6
MAX_CHECKED_LINKS = 5
SEARCHES_PER_ITERATION = 2
MIN_LIVE_LINKS_TO_STOP = 3
MIN_RESOURCES = 3
MAX_RESOURCES = 5

WEAKNESS_RANK = {"high": 3, "med": 2, "low": 1}


def _pedagogy_gemini_api_key() -> str:
    """Prefer PEDAGOGY_GEMINI_API_KEY; fall back to GEMINI_API_KEY. Never log."""
    pedagogy = (os.getenv("PEDAGOGY_GEMINI_API_KEY") or "").strip()
    if pedagogy:
        return pedagogy
    return (os.getenv("GEMINI_API_KEY") or "").strip()

# Preference → search phrasing (YouTube + articles). Visual favors diagrams /
# animation; step-by-step favors worked tutorials; examples favor worked examples.
STYLE_QUERY_HINTS = {
    "visual_structural": "animated diagram visualization",
    "step_by_step": "worked tutorial step by step",
    "example_driven": "worked example",
    "conceptual": "intuition explained",
    "unknown": "introduction",
}

STYLE_LABELS = {
    "visual_structural": "visual / structural",
    "step_by_step": "step-by-step",
    "example_driven": "example-driven",
    "conceptual": "conceptual",
    "unknown": "general",
}

STYLE_WHY = {
    "visual_structural": "Matches a visual preference with diagrams or animation.",
    "step_by_step": "Matches a step-by-step preference with a worked tutorial.",
    "example_driven": "Matches an example-based preference with a worked example.",
    "conceptual": "Matches a conceptual preference with a clear explanation.",
    "unknown": "Solid overview for this weak topic.",
}

EDU_CHANNEL_HINTS = (
    "khan",
    "mit",
    "ocw",
    "university",
    "crash course",
    "crashcourse",
    "freecodecamp",
    "computerphile",
    "numberphile",
    "3blue1brown",
    "wikipedia",
    "academy",
)

REVISION_THINK_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string"},
        "query": {"type": "string", "nullable": True},
    },
    "required": ["action", "query"],
}

REVISION_THINK_SYSTEM = (
    "You plan the next search step for a campus revision study plan. "
    "Reply with JSON only: action is search, drop, or stop; query is a "
    "short public web search string when action is search, else null. "
    "Use only topic labels, weakness levels, learning preference, and "
    "public search titles/snippets already provided. Never invent URLs. "
    "Never ask for or use student names, scores, or grades."
)

REVISION_RANK_SCHEMA = {
    "type": "object",
    "properties": {
        "picks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["id", "why"],
            },
        }
    },
    "required": ["picks"],
}

REVISION_RANK_SYSTEM = (
    "You rank study resources for a campus revision plan. "
    "Reply with JSON only: picks is an array of {id, why}. "
    "Choose 3 to 5 ids from the candidate list only. Never invent ids or URLs. "
    "Prefer educational channels and mixed sources (at most two from the same "
    "channel or site; include an article or tutorial when one is in the list). "
    "Match the learning preference. why is one plain sentence that only "
    "restates facts from that candidate's title or snippet — no outside claims. "
    "Never use student names, scores, or grades."
)

# Display names for common article hosts (source label "Article · …").
_KNOWN_SITE_NAMES = {
    "wikipedia.org": "Wikipedia",
    "khanacademy.org": "Khan Academy",
    "ocw.mit.edu": "MIT OCW",
}

_WHY_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "this",
        "that",
        "from",
        "into",
        "about",
        "your",
        "you",
        "are",
        "is",
        "was",
        "were",
        "been",
        "being",
        "have",
        "has",
        "had",
        "will",
        "can",
        "may",
        "a",
        "an",
        "of",
        "to",
        "in",
        "on",
        "as",
        "by",
        "or",
        "at",
        "it",
        "its",
        "our",
        "their",
    }
)

# Glue / preference words allowed in a why-line even if absent from the snippet.
_WHY_ALLOWED = frozenset(
    {
        "visual",
        "structural",
        "step",
        "steps",
        "example",
        "examples",
        "conceptual",
        "overview",
        "introduction",
        "explains",
        "explanation",
        "covers",
        "tutorial",
        "diagram",
        "diagrams",
        "animation",
        "animated",
        "walkthrough",
        "learner",
        "learning",
        "preference",
        "clear",
        "solid",
        "worked",
        "article",
        "video",
        "resource",
        "topic",
        "matches",
        "listed",
        "search",
        "results",
    }
)

# Final Resources payload cache: topic|preference → (expires, resources dicts).
_PLAN_RESOURCE_CACHE: dict[str, tuple[float, list[dict[str, Any]]]] = {}
_PLAN_CACHE_TTL_DEFAULT = 1800

ThinkFn = Callable[[dict[str, Any]], dict[str, Any]]
RankFn = Callable[[dict[str, Any]], dict[str, Any]]


def clear_plan_resource_cache() -> None:
    _PLAN_RESOURCE_CACHE.clear()


def plan_cache_ttl_seconds() -> int:
    raw = os.getenv(
        "OFFICEHOURS_RESOURCES_CACHE_TTL_SECONDS",
        str(_PLAN_CACHE_TTL_DEFAULT),
    )
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return _PLAN_CACHE_TTL_DEFAULT


def build_revision_plan(
    db: Session,
    payload: RevisionPlanRequest,
    *,
    user_id: int | None = None,
    think_fn: ThinkFn | None = None,
    rank_fn: RankFn | None = None,
    search_fn: Callable[..., list[dict[str, Any]]] | None = None,
    link_check_fn: Callable[[str], bool] | None = None,
) -> RevisionPlanOut:
    preference = payload.preference if payload.preference in LEARNING_STYLES else "unknown"
    focus_rows = _rank_topics(payload.grades, payload.deadlines)
    focus_topics = [row["topic"] for row in focus_rows]
    notes: list[str] = []
    if not focus_topics:
        notes.append("No weak text topics yet - preference still shapes the plan.")
        focus_topics = []

    # Pedagogy Resources are live web only - never course KB / demo outlines.
    primary_topic = focus_topics[0] if focus_topics else "course revision"
    cache_key = f"{primary_topic.strip().lower()}|{preference}"
    cached_resources = _plan_cache_get(cache_key)

    search_impl = search_fn or resource_search
    check_impl = link_check_fn or link_ok

    allowed_urls: set[str] = set()
    candidates: list[dict[str, Any]] = []
    live_resources: list[ResourceOut] = []
    iterations: list[IterationTraceOut] = []
    search_count = 0
    checked_count = 0
    llm_calls = 0
    used_llm = False
    fallback_reason: str | None = None
    model_name: str | None = None
    last_raw_hits: list[dict[str, Any]] = []

    if cached_resources is not None:
        live_resources = [
            ResourceOut(**row) for row in cached_resources if row.get("url")
        ]
        allowed_urls = {r.url for r in live_resources if r.url}
        iterations.append(
            IterationTraceOut(
                iteration=1,
                action="stop",
                query=None,
                thinker="rules",
                note="Used cached resources for this topic and preference.",
            )
        )
    else:
        for iteration in range(1, MAX_ITERATIONS + 1):
            observation = _observe(
                focus_rows=focus_rows,
                preference=preference,
                kb_titles=[],
                live_count=len([r for r in live_resources if r.url]),
                search_count=search_count,
                checked_count=checked_count,
                last_hits=_public_hit_summaries(last_raw_hits),
                remaining_searches=MAX_SEARCHES - search_count,
                remaining_checks=MAX_CHECKED_LINKS - checked_count,
                iteration=iteration,
            )

            decision, thinker, think_note, llm_meta = _think(
                observation,
                user_id=user_id,
                course_id=payload.course_id,
                llm_calls=llm_calls,
                think_fn=think_fn,
                force_rules=fallback_reason is not None
                and thinker_locked_to_rules(fallback_reason),
            )
            if llm_meta.get("called"):
                llm_calls += 1
                used_llm = True
                model_name = llm_meta.get("model") or gemini_model()
            if llm_meta.get("fallback_reason") and fallback_reason is None:
                fallback_reason = llm_meta["fallback_reason"]
                # Keep operator reason in logs only - never surface gate/LLM codes.
                notes.append(
                    "Built from your scores and study preference while the full agent was unavailable."
                )

            action = decision["action"]
            query = decision.get("query")
            hit_count = 0
            checked_ok = 0
            act_note = think_note

            if action == "stop":
                iterations.append(
                    IterationTraceOut(
                        iteration=iteration,
                        action="stop",
                        query=None,
                        thinker=thinker,
                        note=act_note or "Stop - enough live links or no useful search left.",
                    )
                )
                break

            if action == "drop":
                dropped = _drop_weak_candidates(candidates, live_resources)
                act_note = act_note or f"Dropped {dropped} weak candidate link(s)."
                iterations.append(
                    IterationTraceOut(
                        iteration=iteration,
                        action="drop",
                        query=None,
                        thinker=thinker,
                        note=act_note,
                    )
                )
                if len([r for r in live_resources if r.url]) >= MIN_LIVE_LINKS_TO_STOP:
                    break
                continue

            # action == search
            if search_count >= MAX_SEARCHES:
                iterations.append(
                    IterationTraceOut(
                        iteration=iteration,
                        action="stop",
                        query=query,
                        thinker=thinker,
                        note="Search cap reached.",
                    )
                )
                break

            q = (query or "").strip()
            if not q:
                q = _rule_query(focus_rows, preference, search_count)
            # Never treat a bare URL as a search invent - require a text query.
            if q.startswith("http://") or q.startswith("https://"):
                act_note = "Rejected URL-shaped query; not searched."
                iterations.append(
                    IterationTraceOut(
                        iteration=iteration,
                        action="search",
                        query=q[:160],
                        thinker=thinker,
                        note=act_note,
                        search_hits=0,
                        checked_ok=0,
                    )
                )
                continue

            per_iter_budget = min(SEARCHES_PER_ITERATION, MAX_SEARCHES - search_count)
            raw_hits: list[dict[str, Any]] = []
            for _ in range(max(1, min(1, per_iter_budget))):
                if search_count >= MAX_SEARCHES:
                    break
                found = (
                    search_impl(
                        q,
                        max_results=6,
                        preference=preference,
                        topic=primary_topic,
                    )
                    or []
                )
                search_count += 1
                raw_hits.extend(found)
                # One logical search call per think; YouTube+articles inside resource_search.
                break
            last_raw_hits = raw_hits
            hit_count = len(raw_hits)

            for hit in raw_hits:
                url = str(hit.get("url") or "").strip()
                if not url.startswith("http"):
                    continue
                allowed_urls.add(url)
                candidates.append(hit)

            # Check new candidates that are not yet live.
            pending = [
                hit
                for hit in candidates
                if str(hit.get("url") or "") not in {r.url for r in live_resources if r.url}
            ]
            for hit in pending:
                if checked_count >= MAX_CHECKED_LINKS:
                    break
                if len([r for r in live_resources if r.url]) >= MAX_CHECKED_LINKS:
                    break
                url = str(hit.get("url") or "")
                if url not in allowed_urls:
                    continue
                checked_count += 1
                if not check_impl(url):
                    continue
                if not _hit_matches_topic(hit, focus_topics):
                    continue
                checked_ok += 1
                live_resources.append(
                    _resource_from_hit(hit, preference=preference)
                )

            iterations.append(
                IterationTraceOut(
                    iteration=iteration,
                    action="search",
                    query=q[:200],
                    thinker=thinker,
                    note=act_note,
                    search_hits=hit_count,
                    checked_ok=checked_ok,
                )
            )

            if len([r for r in live_resources if r.url]) >= MIN_LIVE_LINKS_TO_STOP:
                if iteration == MAX_ITERATIONS:
                    break
                continue

        # Rank / pick among search hits only (Gemini when armed; else rules).
        # Injected think_fn without rank_fn → rule rank (tests / offline).
        ranked, rank_meta = _rank_resources(
            candidates=candidates,
            live_urls={r.url for r in live_resources if r.url},
            preference=preference,
            topic=primary_topic,
            user_id=user_id,
            course_id=payload.course_id,
            llm_calls=llm_calls,
            rank_fn=rank_fn,
            force_rules=(
                (fallback_reason is not None and thinker_locked_to_rules(fallback_reason))
                or (think_fn is not None and rank_fn is None)
            ),
        )
        if rank_meta.get("called"):
            llm_calls += 1
            used_llm = True
            model_name = rank_meta.get("model") or model_name or gemini_model()
        # Rule-rank after a successful think must not flip the plan to fallback.
        if (
            rank_meta.get("fallback_reason")
            and fallback_reason is None
            and not used_llm
        ):
            fallback_reason = rank_meta["fallback_reason"]
            notes.append(
                "Built from your scores and study preference while the full agent was unavailable."
            )
        if ranked:
            live_resources = ranked

    # Strip any resource whose URL was not returned by search (no invented / KB URLs).
    # Cached rows already came from prior search-only picks.
    if cached_resources is None:
        by_url = {str(h.get("url") or ""): h for h in candidates}
        safe_resources: list[ResourceOut] = []
        for resource in live_resources:
            if not resource.url or resource.url not in allowed_urls:
                continue
            hit = by_url.get(resource.url) or {}
            if hit and not _hit_matches_topic(hit, focus_topics):
                continue
            safe_resources.append(resource)
        safe_resources = _diversify_resources(
            _dedupe_resources(safe_resources)
        )[:MAX_RESOURCES]
        if safe_resources:
            _plan_cache_set(
                cache_key,
                [r.model_dump() for r in safe_resources],
            )
    else:
        safe_resources = _dedupe_resources(
            [r for r in live_resources if r.url]
        )[:MAX_RESOURCES]

    web_live = [r for r in safe_resources if r.url]
    if not web_live:
        notes.append("We couldn't find resources right now. Try again later.")

    mode: str
    mode_label: str
    if used_llm and fallback_reason is None:
        mode = "agent"
        mode_label = "Plan built with the Pedagogy Agent"
    else:
        mode = "rule-based fallback"
        mode_label = "Plan built from your scores and preference"

    slots = _backwards_schedule(
        focus_rows=focus_rows,
        deadlines=payload.deadlines,
        available_minutes=payload.available_minutes_today,
        preference=preference,
    )
    ask_draft = _ask_draft(focus_topics, preference)

    # One Orchestrator log line per plan: mode + fallback reason only (no grades/names/scores/hits).
    policy._log(
        "answered" if mode == "agent" else "disabled",
        None,
        limit=f"{mode}:{fallback_reason or '-'}",
    )

    clean_iterations = [
        IterationTraceOut(
            iteration=step.iteration,
            action=step.action,
            query=step.query,
            thinker=step.thinker,
            note=_public_iteration_note(step.note),
        )
        for step in iterations
    ]

    return RevisionPlanOut(
        mode=mode,  # type: ignore[arg-type]
        mode_label=mode_label,
        focus_topics=focus_topics,
        preference=preference,  # type: ignore[arg-type]
        resources=safe_resources[:MAX_RESOURCES],
        time_slots=slots,
        ask_draft=ask_draft,
        iterations=clean_iterations,
        notes=notes,
        caps={
            "max_iterations": MAX_ITERATIONS,
            "max_llm_calls": MAX_LLM_CALLS,
            "max_searches": MAX_SEARCHES,
            "max_checked_links": MAX_CHECKED_LINKS,
            "llm_calls": llm_calls,
            "searches": search_count,
            "checked_links": checked_count,
        },
        model=model_name if mode == "agent" else None,
    )


def thinker_locked_to_rules(reason: str | None) -> bool:
    return bool(reason)


def _rank_topics(
    grades: list[GradeTopicIn],
    deadlines: list[DeadlineIn],
) -> list[dict[str, Any]]:
    due_map = {
        d.topic.strip().lower(): int(d.due_in_days)
        for d in deadlines
        if d.topic and d.topic.strip()
    }
    # Topics without an explicit deadline inherit the plan end (max due),
    # never a hardcoded day count.
    default_due = max(due_map.values()) if due_map else 14
    rows: list[dict[str, Any]] = []
    for grade in grades:
        if grade.assignment_kind != "text":
            continue
        topic = grade.topic.strip()
        rows.append(
            {
                "topic": topic,
                "weakness": grade.weakness,
                "due_in_days": due_map.get(topic.lower(), default_due),
            }
        )
    rows.sort(
        key=lambda row: (
            -WEAKNESS_RANK.get(str(row["weakness"]), 0),
            int(row["due_in_days"]),
            str(row["topic"]),
        )
    )
    return rows


def _observe(**kwargs: Any) -> dict[str, Any]:
    # Privacy: only topic labels, weakness, preference, public titles/snippets.
    return {
        "iteration": kwargs["iteration"],
        "preference": kwargs["preference"],
        "topics": [
            {"topic": row["topic"], "weakness": row["weakness"], "due_in_days": row["due_in_days"]}
            for row in kwargs["focus_rows"]
        ],
        "kb_titles": kwargs["kb_titles"][:5],
        "live_link_count": kwargs["live_count"],
        "search_count": kwargs["search_count"],
        "checked_count": kwargs["checked_count"],
        "remaining_searches": kwargs["remaining_searches"],
        "remaining_checks": kwargs["remaining_checks"],
        "recent_search_hits": kwargs["last_hits"][:6],
    }


def _public_hit_summaries(hits: list[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for hit in hits[:6]:
        out.append(
            {
                "title": str(hit.get("title") or "")[:160],
                "snippet": str(hit.get("snippet") or "")[:200],
            }
        )
    return out


def _think(
    observation: dict[str, Any],
    *,
    user_id: int | None,
    course_id: int,
    llm_calls: int,
    think_fn: ThinkFn | None,
    force_rules: bool,
) -> tuple[dict[str, Any], str, str | None, dict[str, Any]]:
    """Return (decision, thinker, note, llm_meta)."""
    if force_rules:
        return _rule_think(observation), "rules", "Forced rule thinker.", {"called": False}

    # Early stop without spending LLM when caps already met.
    if observation["live_link_count"] >= MIN_LIVE_LINKS_TO_STOP:
        return (
            {"action": "stop", "query": None},
            "rules",
            "Enough live links - stop without another model call.",
            {"called": False},
        )
    if observation["remaining_searches"] <= 0:
        return (
            {"action": "stop", "query": None},
            "rules",
            "Search budget exhausted.",
            {"called": False},
        )

    if think_fn is not None:
        raw = think_fn(observation)
        decision = _validate_think(raw)
        if decision is None:
            return (
                _rule_think(observation),
                "rules",
                "Invalid model output - rule-based fallback.",
                {"called": True, "fallback_reason": "invalid_output"},
            )
        return decision, "llm", None, {"called": True, "model": "mock"}

    gate = _llm_gate(user_id=user_id, course_id=course_id, llm_calls=llm_calls)
    if gate is not None:
        return (
            _rule_think(observation),
            "rules",
            f"LLM gate: {gate}",
            {"called": False, "fallback_reason": gate},
        )

    # Same spend as Study Agent: record user/course windows or fall back.
    spent = policy._WINDOWS.allow_all(policy._window_checks(user_id, course_id))
    if spent is not None:
        return (
            _rule_think(observation),
            "rules",
            f"LLM gate: budget:{spent}",
            {"called": False, "fallback_reason": f"budget:{spent}"},
        )

    try:
        user_payload = json.dumps(observation, ensure_ascii=False)
        completion = complete_gemini(
            REVISION_THINK_SYSTEM,
            user_payload,
            max_tokens=min(200, policy.max_output_tokens()),
            temperature=0,
            timeout=policy.timeout_seconds(),
            schema=REVISION_THINK_SCHEMA,
            api_key=_pedagogy_gemini_api_key(),
        )
        policy._note_spend(completion.input_tokens, completion.output_tokens)
        policy._note_success()
        decision = _validate_think_text(completion.text)
        if decision is None:
            return (
                _rule_think(observation),
                "rules",
                "Invalid model JSON - rule-based fallback.",
                {
                    "called": True,
                    "fallback_reason": "invalid_output",
                    "model": completion.model,
                },
            )
        return (
            decision,
            "llm",
            None,
            {"called": True, "model": completion.model},
        )
    except DailyQuotaError:
        policy._note_failure()
        return (
            _rule_think(observation),
            "rules",
            "Daily quota - rule-based fallback.",
            {"called": False, "fallback_reason": "daily_quota"},
        )
    except RateLimitExhausted:
        policy._note_failure()
        return (
            _rule_think(observation),
            "rules",
            "Rate limited - rule-based fallback.",
            {"called": False, "fallback_reason": "rate_limit"},
        )
    except Exception as exc:
        policy._note_failure()
        reason = "no_key" if "GEMINI_API_KEY" in str(exc) else "llm_error"
        logger.info("revision think fallback reason=%s type=%s", reason, type(exc).__name__)
        return (
            _rule_think(observation),
            "rules",
            f"LLM error ({type(exc).__name__}) - rule-based fallback.",
            {"called": False, "fallback_reason": reason},
        )


def _public_iteration_note(note: str | None) -> str | None:
    """Strip operator/gate codes so API traces never leak llm_off-style jargon."""
    text = (note or "").strip()
    if not text:
        return None
    if re.search(
        r"llm_|fallback|gate:|budget:|quota|rule-based|invalid model|api key|gemini|orchestrat",
        text,
        re.I,
    ):
        return "Used a simple planner from your scores and preference."
    return text


def _llm_gate(*, user_id: int | None, course_id: int, llm_calls: int) -> str | None:
    if not policy.llm_enabled():
        return "unavailable"
    if llm_calls >= MAX_LLM_CALLS:
        return "llm_cap"
    if not policy._model_calls_allowed():
        return "external_or_demo_off"
    provider = os.getenv("OFFICEHOURS_LLM_PROVIDER", "").strip().lower()
    if provider != "gemini":
        return "provider_off"
    if not policy._truthy("OFFICEHOURS_GEMINI_FREE_TIER_ACK"):
        return "free_tier_ack_off"
    if not _pedagogy_gemini_api_key():
        return "no_key"
    if policy.breaker_open():
        return "circuit_breaker"
    blocked = policy._budget_block() or policy._WINDOWS.blocking(
        policy._window_checks(user_id, course_id)
    )
    if blocked:
        return f"budget:{blocked}"
    return None


def _validate_think_text(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        # Strip optional fences.
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    return _validate_think(data)


def _validate_think(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    action = str(data.get("action") or "").strip().lower()
    if action not in {"search", "drop", "stop"}:
        return None
    query = data.get("query")
    if query is not None and not isinstance(query, str):
        return None
    if action == "search":
        q = (query or "").strip()
        if not q or len(q) > 200:
            return None
        return {"action": "search", "query": q}
    return {"action": action, "query": None}


def _rule_think(observation: dict[str, Any]) -> dict[str, Any]:
    if observation["live_link_count"] >= MIN_LIVE_LINKS_TO_STOP:
        return {"action": "stop", "query": None}
    if observation["remaining_searches"] <= 0:
        return {"action": "stop", "query": None}
    if observation["iteration"] >= MAX_ITERATIONS and observation["live_link_count"] > 0:
        return {"action": "stop", "query": None}
    recent = observation.get("recent_search_hits") or []
    if recent and observation["live_link_count"] == 0 and observation["iteration"] > 1:
        # Prior hits failed checks - try a tighter query rather than drop forever.
        pass
    preference = str(observation.get("preference") or "unknown")
    topics = observation.get("topics") or []
    topic = topics[0]["topic"] if topics else "course revision"
    hint = STYLE_QUERY_HINTS.get(preference, STYLE_QUERY_HINTS["unknown"])
    # Vary query slightly across iterations.
    suffix = "" if observation["search_count"] == 0 else " overview"
    return {"action": "search", "query": f"{topic} {hint}{suffix}".strip()[:200]}


def _rule_query(focus_rows: list[dict[str, Any]], preference: str, search_count: int) -> str:
    topic = focus_rows[0]["topic"] if focus_rows else "course revision"
    hint = STYLE_QUERY_HINTS.get(preference, STYLE_QUERY_HINTS["unknown"])
    suffix = "" if search_count == 0 else " overview"
    return f"{topic} {hint}{suffix}".strip()[:200]


def _drop_weak_candidates(
    candidates: list[dict[str, Any]],
    live_resources: list[ResourceOut],
) -> int:
    live_urls = {r.url for r in live_resources if r.url}
    before = len(candidates)
    candidates[:] = [hit for hit in candidates if str(hit.get("url") or "") in live_urls]
    return before - len(candidates)


def _token_in_blob(token: str, blob: str) -> bool:
    if token in blob:
        return True
    # light plural: trees ↔ tree
    if token.endswith("s") and len(token) > 4 and token[:-1] in blob:
        return True
    return False


def _hit_matches_topic(hit: dict[str, Any], topics: list[str]) -> bool:
    """Require real topic overlap - one short token is not enough when the topic has several."""
    if not topics:
        return True
    blob = f"{hit.get('title') or ''} {hit.get('snippet') or ''}".lower()
    for topic in topics:
        tokens = [
            part
            for part in re.split(r"[^a-z0-9]+", topic.lower())
            if len(part) > 2
        ]
        if not tokens:
            compact = re.sub(r"[^a-z0-9]+", " ", topic.lower()).strip()
            if compact and compact in blob:
                return True
            continue
        matches = sum(1 for part in tokens if _token_in_blob(part, blob))
        need = 2 if len(tokens) >= 2 else 1
        if matches >= need:
            return True
    return False


def _why(preference: str, topic: str) -> str:
    """Legacy preference-flavored why (tests / fallbacks without a hit)."""
    base = STYLE_WHY.get(preference) or STYLE_WHY["unknown"]
    return f"{base} Topic: {topic}."


def _host_from_url(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host


def _site_display_name(hit: dict[str, Any]) -> str:
    host = _host_from_url(str(hit.get("url") or ""))
    if host:
        for suffix, name in _KNOWN_SITE_NAMES.items():
            if host == suffix or host.endswith("." + suffix):
                return name
        return host
    channel = str(hit.get("channel") or "").strip()
    if channel:
        return channel
    provider = str(hit.get("provider") or "").strip()
    return provider or "Web"


def _source_label(hit: dict[str, Any]) -> str:
    """Display source: 'Video · YouTube' or 'Article · <site>'."""
    kind = str(hit.get("kind") or "article").lower()
    provider = str(hit.get("provider") or "").lower()
    if kind == "video" or provider == "youtube":
        return "Video · YouTube"
    return f"Article · {_site_display_name(hit)}"


def _channel_for_hit(hit: dict[str, Any]) -> str | None:
    """YouTube channel for secondary UI + mix; articles omit (mix uses host)."""
    kind = str(hit.get("kind") or "article").lower()
    provider = str(hit.get("provider") or "").lower()
    if kind == "video" or provider == "youtube":
        channel = str(hit.get("channel") or "").strip()
        return channel or None
    return None


def _significant_why_tokens(text: str) -> set[str]:
    return {
        part
        for part in re.split(r"[^a-z0-9]+", (text or "").lower())
        if len(part) > 2 and part not in _WHY_STOPWORDS
    }


def _why_is_grounded(why: str, title: str, snippet: str) -> bool:
    """Reject why-lines that invent facts beyond title/snippet (+ light glue)."""
    why_tokens = _significant_why_tokens(why)
    if not why_tokens:
        return False
    fact_tokens = _significant_why_tokens(f"{title} {snippet}") | _WHY_ALLOWED
    novel = why_tokens - fact_tokens
    if not novel:
        return True
    return (len(novel) / len(why_tokens)) <= 0.35


def _grounded_why(hit: dict[str, Any]) -> str:
    """Build a why-line only from title/snippet facts."""
    title = str(hit.get("title") or "").strip()
    snippet = str(hit.get("snippet") or "").strip()
    if snippet:
        sentence = re.split(r"(?<=[.!?])\s+", snippet)[0].strip()
        if sentence:
            return sentence[:200]
    if title:
        return f"Covers {title[:160]}."[:200]
    return "Listed in search results for this topic."


def _resource_from_hit(
    hit: dict[str, Any],
    *,
    preference: str = "",
    why: str | None = None,
) -> ResourceOut:
    title = str(hit.get("title") or "Resource")
    snippet = str(hit.get("snippet") or "")
    cleaned = (why or "").strip()
    if (
        not cleaned
        or "http://" in cleaned
        or "https://" in cleaned
        or not _why_is_grounded(cleaned, title, snippet)
    ):
        cleaned = _grounded_why(hit)
    return ResourceOut(
        title=title,
        url=str(hit.get("url") or "") or None,
        source=_source_label(hit),
        why=cleaned[:200],
        kind=str(hit.get("kind") or "article"),
        channel=_channel_for_hit(hit),
    )


def _publisher_key(resource: ResourceOut) -> str:
    """Mix key: YouTube channel or article site host."""
    if resource.channel and resource.channel.strip():
        return resource.channel.strip().lower()
    host = _host_from_url(resource.url or "")
    if host:
        for suffix in _KNOWN_SITE_NAMES:
            if host == suffix or host.endswith("." + suffix):
                return suffix
        return host
    return (resource.source or "web").lower()


def _plan_cache_get(key: str) -> list[dict[str, Any]] | None:
    ttl = plan_cache_ttl_seconds()
    if ttl <= 0:
        return None
    row = _PLAN_RESOURCE_CACHE.get(key)
    if not row:
        return None
    expires, resources = row
    if time.monotonic() > expires:
        _PLAN_RESOURCE_CACHE.pop(key, None)
        return None
    return [dict(r) for r in resources]


def _plan_cache_set(key: str, resources: list[dict[str, Any]]) -> None:
    ttl = plan_cache_ttl_seconds()
    if ttl <= 0 or not resources:
        return
    _PLAN_RESOURCE_CACHE[key] = (
        time.monotonic() + ttl,
        [dict(r) for r in resources],
    )


def _rank_resources(
    *,
    candidates: list[dict[str, Any]],
    live_urls: set[str],
    preference: str,
    topic: str,
    user_id: int | None,
    course_id: int,
    llm_calls: int,
    rank_fn: RankFn | None,
    force_rules: bool,
) -> tuple[list[ResourceOut], dict[str, Any]]:
    """Gemini (or rules) picks among search hits that already passed link checks."""
    pool = [
        hit
        for hit in candidates
        if str(hit.get("url") or "") in live_urls
    ]
    if not pool:
        return [], {"called": False}

    indexed = []
    for idx, hit in enumerate(pool, start=1):
        indexed.append({**hit, "_id": str(idx)})

    if force_rules:
        return _rule_rank(indexed, preference, topic), {"called": False}

    if rank_fn is not None:
        raw = rank_fn(
            {
                "preference": preference,
                "topic": topic,
                "candidates": [
                    {
                        "id": h["_id"],
                        "title": str(h.get("title") or "")[:160],
                        "source": _source_label(h),
                        "kind": str(h.get("kind") or "article"),
                        "snippet": str(h.get("snippet") or "")[:200],
                    }
                    for h in indexed
                ],
            }
        )
        picked = _apply_rank_picks(raw, indexed, preference, topic)
        if picked:
            return picked, {"called": True, "model": "mock"}
        return _rule_rank(indexed, preference, topic), {
            "called": True,
            "fallback_reason": "invalid_output",
        }

    gate = _llm_gate(user_id=user_id, course_id=course_id, llm_calls=llm_calls)
    if gate is not None:
        return _rule_rank(indexed, preference, topic), {
            "called": False,
            "fallback_reason": gate,
        }

    spent = policy._WINDOWS.allow_all(policy._window_checks(user_id, course_id))
    if spent is not None:
        return _rule_rank(indexed, preference, topic), {
            "called": False,
            "fallback_reason": f"budget:{spent}",
        }

    try:
        user_payload = json.dumps(
            {
                "preference": preference,
                "topic": topic,
                "candidates": [
                    {
                        "id": h["_id"],
                        "title": str(h.get("title") or "")[:160],
                        "source": _source_label(h),
                        "kind": str(h.get("kind") or "article"),
                        "snippet": str(h.get("snippet") or "")[:200],
                    }
                    for h in indexed
                ],
            },
            ensure_ascii=False,
        )
        # Privacy: payload is topic + preference + public titles/snippets only.
        completion = complete_gemini(
            REVISION_RANK_SYSTEM,
            user_payload,
            max_tokens=min(400, policy.max_output_tokens()),
            temperature=0,
            timeout=policy.timeout_seconds(),
            schema=REVISION_RANK_SCHEMA,
            api_key=_pedagogy_gemini_api_key(),
        )
        policy._note_spend(completion.input_tokens, completion.output_tokens)
        policy._note_success()
        picks = _validate_rank_text(completion.text)
        picked = _apply_rank_picks(picks, indexed, preference, topic) if picks else []
        if not picked:
            return _rule_rank(indexed, preference, topic), {
                "called": True,
                "fallback_reason": "invalid_output",
                "model": completion.model,
            }
        return picked, {"called": True, "model": completion.model}
    except DailyQuotaError:
        policy._note_failure()
        return _rule_rank(indexed, preference, topic), {
            "called": False,
            "fallback_reason": "daily_quota",
        }
    except RateLimitExhausted:
        policy._note_failure()
        return _rule_rank(indexed, preference, topic), {
            "called": False,
            "fallback_reason": "rate_limit",
        }
    except Exception as exc:
        policy._note_failure()
        reason = "no_key" if "GEMINI_API_KEY" in str(exc) else "llm_error"
        logger.info("revision rank fallback reason=%s type=%s", reason, type(exc).__name__)
        return _rule_rank(indexed, preference, topic), {
            "called": False,
            "fallback_reason": reason,
        }


def _validate_rank_text(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        if raw.startswith("```"):
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    picks = data.get("picks")
    if not isinstance(picks, list):
        return None
    cleaned = []
    for row in picks:
        if not isinstance(row, dict):
            continue
        pick_id = str(row.get("id") or "").strip()
        why = str(row.get("why") or "").strip()
        if not pick_id:
            continue
        cleaned.append({"id": pick_id, "why": why[:200] if why else ""})
    if not cleaned:
        return None
    return {"picks": cleaned}


def _apply_rank_picks(
    raw: dict[str, Any] | None,
    indexed: list[dict[str, Any]],
    preference: str,
    topic: str,
) -> list[ResourceOut]:
    if not raw:
        return []
    by_id = {str(h["_id"]): h for h in indexed}
    out: list[ResourceOut] = []
    seen: set[str] = set()
    for row in raw.get("picks") or []:
        hit = by_id.get(str(row.get("id") or ""))
        if not hit:
            continue
        url = str(hit.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(
            _resource_from_hit(
                hit,
                preference=preference,
                why=str(row.get("why") or "").strip() or None,
            )
        )
        # Collect extra picks so diversify can fill after channel/site caps.
        if len(out) >= MAX_RESOURCES * 2:
            break
    return _diversify_resources(out)


def _rule_rank(
    indexed: list[dict[str, Any]],
    preference: str,
    topic: str,
) -> list[ResourceOut]:
    hint = STYLE_QUERY_HINTS.get(preference, "")
    hint_tokens = [t for t in re.split(r"[^a-z0-9]+", hint.lower()) if len(t) > 2]

    def score(hit: dict[str, Any]) -> tuple[int, int, str]:
        blob = f"{hit.get('title') or ''} {hit.get('snippet') or ''} {hit.get('channel') or ''}".lower()
        pref_hits = sum(1 for t in hint_tokens if t in blob)
        edu = 1 if any(h in blob for h in EDU_CHANNEL_HINTS) else 0
        # Prefer videos for visual; articles still allowed.
        kind_bonus = 0
        kind = str(hit.get("kind") or "")
        if preference == "visual_structural" and kind == "video":
            kind_bonus = 2
        elif preference == "step_by_step" and ("tutorial" in blob or "step" in blob):
            kind_bonus = 2
        elif preference == "example_driven" and "example" in blob:
            kind_bonus = 2
        return (pref_hits + edu + kind_bonus, edu, str(hit.get("title") or ""))

    ordered = sorted(indexed, key=score, reverse=True)
    out: list[ResourceOut] = []
    for hit in ordered:
        url = str(hit.get("url") or "")
        if not url:
            continue
        out.append(_resource_from_hit(hit, preference=preference))
        if len(out) >= MAX_RESOURCES * 2:
            break
    return _diversify_resources(out)


def _is_article_or_tutorial(resource: ResourceOut) -> bool:
    if (resource.kind or "").lower() == "article":
        return True
    blob = f"{resource.title or ''} {resource.why or ''}".lower()
    return "tutorial" in blob


def _diversify_resources(resources: list[ResourceOut]) -> list[ResourceOut]:
    """Hard mix: ≤2 per channel/site; keep an article/tutorial when one exists."""
    if len(resources) <= 1:
        return resources

    selected: list[ResourceOut] = []
    counts: dict[str, int] = {}

    def try_add(resource: ResourceOut) -> bool:
        if len(selected) >= MAX_RESOURCES:
            return False
        url = (resource.url or "").strip()
        if url and any((s.url or "").strip() == url for s in selected):
            return False
        key = _publisher_key(resource)
        if counts.get(key, 0) >= 2:
            return False
        selected.append(resource)
        counts[key] = counts.get(key, 0) + 1
        return True

    for resource in resources:
        try_add(resource)
        if len(selected) >= MAX_RESOURCES:
            break

    pool_has_article = any(_is_article_or_tutorial(r) for r in resources)
    selected_has_article = any(_is_article_or_tutorial(r) for r in selected)
    if pool_has_article and not selected_has_article:
        for resource in resources:
            if not _is_article_or_tutorial(resource):
                continue
            key = _publisher_key(resource)
            url = (resource.url or "").strip()
            if url and any((s.url or "").strip() == url for s in selected):
                continue
            if counts.get(key, 0) >= 2:
                continue
            if len(selected) < MAX_RESOURCES:
                try_add(resource)
                break
            # Swap out the last non-article so mix still includes one.
            for idx in range(len(selected) - 1, -1, -1):
                if _is_article_or_tutorial(selected[idx]):
                    continue
                old_key = _publisher_key(selected[idx])
                counts[old_key] = max(0, counts.get(old_key, 1) - 1)
                selected[idx] = resource
                counts[key] = counts.get(key, 0) + 1
                break
            break

    return selected[:MAX_RESOURCES]


def _dedupe_resources(resources: list[ResourceOut]) -> list[ResourceOut]:
    out: list[ResourceOut] = []
    seen: set[str] = set()
    for resource in resources:
        key = (resource.url or resource.title).lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(resource)
    return out


def _backwards_schedule(
    *,
    focus_rows: list[dict[str, Any]],
    deadlines: list[DeadlineIn],
    available_minutes: int,
    preference: str,
) -> list[TimeSlotOut]:
    """Thin backwards packer from synthetic deadlines."""
    if not focus_rows:
        return [
            TimeSlotOut(
                day_offset=0,
                label="Today · foundations",
                minutes=min(45, available_minutes),
                topic="General review",
                focus="Open stamped course notes, then one practice pass.",
            )
        ]

    primary = focus_rows[0]
    due = int(primary.get("due_in_days") or 3)
    topic = str(primary["topic"])
    style = STYLE_LABELS.get(preference, "general")
    blocks = [
        (max(due - 2, 0), "Foundations", min(45, available_minutes), "Build the base for this topic."),
        (max(due - 1, 0), "Practice", min(60, max(30, available_minutes // 2)), f"Work problems for a {style} learner."),
        (due, "Self-check", min(30, available_minutes // 3 or 30), "Self-quiz the day before the deadline."),
    ]
    # Unique day offsets, keep order.
    slots: list[TimeSlotOut] = []
    seen_days: set[int] = set()
    for day_offset, label, minutes, focus in blocks:
        if day_offset in seen_days:
            day_offset = max(0, day_offset - 1)
        seen_days.add(day_offset)
        slots.append(
            TimeSlotOut(
                day_offset=day_offset,
                label=label,
                minutes=minutes,
                topic=topic,
                focus=focus,
            )
        )
    if len(focus_rows) > 1:
        secondary = focus_rows[1]
        secondary_due = int(secondary.get("due_in_days") or due)
        slots.append(
            TimeSlotOut(
                day_offset=secondary_due,
                label="Secondary topic",
                minutes=30,
                topic=str(secondary["topic"]),
                focus="Light pass after the primary deadline risk drops.",
            )
        )
    slots.sort(key=lambda s: s.day_offset)
    return slots


def _ask_draft(topics: list[str], preference: str) -> str | None:
    if not topics:
        return None
    topic = topics[0]
    label = STYLE_LABELS.get(preference, "general")
    return (
        f"Quiet ask: I'm revising {topic} and learn best in a {label} way. "
        f"Where should I focus before the deadline?"
    )
