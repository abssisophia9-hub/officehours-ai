"""
Office Hours Oracle — multi-agent Claude client.

Three specialized agents with structured JSON outputs:
  1. Analyzer  — categorize, difficulty, tags, estimated help time
  2. Matcher   — assign TA by expertise + queue depth
  3. Synthesizer — student hint, teaching approach, similar KB hits

USE_MOCK_CLAUDE=true (default) keeps demos deterministic without API keys.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from app.ai.claude_drafter import STYLE_TEACHING_GUIDANCE, draft_with_claude

ANALYZER_SYSTEM = """You are the Analyzer agent for Office Hours Oracle.
Extract structured triage metadata from a student question.
Return ONLY JSON with keys:
category (short label), difficulty (EASY|MEDIUM|HARD),
estimated_minutes (int), tags (string array), urgency (low|medium|high|urgent),
rationale (one sentence)."""

MATCHER_SYSTEM = """You are the Matcher agent for Office Hours Oracle.
Given analyzer tags and a TA roster with expertise and queue depths,
pick the best primary TA and one alternative.
Return ONLY JSON with keys:
assigned_ta, alternative_ta, estimated_wait_minutes (int),
rationale (one sentence). Prefer expertise overlap, then shortest queue."""

SYNTHESIZER_SYSTEM = """You are the Synthesizer agent for Office Hours Oracle.
Given the student question, analyzer tags, and optional similar KB excerpts,
produce a non-spoiler student_hint and a numbered teaching_approach for the TA.
Return ONLY JSON with keys: student_hint, teaching_approach, kb_insight."""


def analyze_question(
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    """
    Analyzer entrypoint.

    Default: fine-tuned small classifier (``OFFICEHOURS_ANALYZER_BACKEND=ml``).
    Set backend to ``claude`` for LLM extraction or ``rules`` for keywords only.
    """
    from app.ai.analyzer_agent import analyze_with_classifier

    return analyze_with_classifier(
        question_text=question_text,
        code_snippet=code_snippet,
        course=course,
    )


def analyze_question_llm(
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
) -> dict[str, Any]:
    """Optional LLM Analyzer path (not the default)."""
    if _use_mock():
        return _mock_analyze(question_text, code_snippet=code_snippet, course=course)

    user = _compose_question_block(question_text, code_snippet, course)
    try:
        raw = _call_claude(ANALYZER_SYSTEM, user)
        data = _parse_json(raw)
        return {
            "category": str(data.get("category") or "General"),
            "difficulty": str(data.get("difficulty") or "MEDIUM").upper(),
            "estimated_minutes": int(data.get("estimated_minutes") or 15),
            "tags": list(data.get("tags") or []),
            "urgency": str(data.get("urgency") or "medium").lower(),
            "rationale": str(data.get("rationale") or ""),
            "backend": "claude",
        }
    except Exception:
        mock = _mock_analyze(question_text, code_snippet=code_snippet, course=course)
        mock["backend"] = "mock_claude_fallback"
        return mock


def match_ta(
    analyzer: dict[str, Any],
    roster: list[dict[str, Any]],
) -> dict[str, Any]:
    if not roster:
        return {
            "assigned_ta": "Unassigned",
            "alternative_ta": None,
            "estimated_wait_minutes": int(analyzer.get("estimated_minutes") or 15),
            "rationale": "No TA roster configured.",
            "backend": "heuristic",
        }

    if _use_mock():
        return _mock_match(analyzer, roster)

    user = json.dumps(
        {"analyzer": analyzer, "roster": roster},
        ensure_ascii=True,
    )
    try:
        raw = _call_claude(MATCHER_SYSTEM, user)
        data = _parse_json(raw)
        return {
            "assigned_ta": str(data.get("assigned_ta") or roster[0]["name"]),
            "alternative_ta": data.get("alternative_ta"),
            "estimated_wait_minutes": int(
                data.get("estimated_wait_minutes")
                or _wait_from_queue(roster[0], analyzer)
            ),
            "rationale": str(data.get("rationale") or ""),
            "backend": "claude",
        }
    except Exception:
        result = _mock_match(analyzer, roster)
        result["backend"] = "mock_claude_fallback"
        return result


def synthesize_solution(
    *,
    question_text: str,
    analyzer: dict[str, Any],
    similar_questions: list[dict[str, Any]],
    learning_style: str | None = None,
    code_snippet: str | None = None,
) -> dict[str, Any]:
    """
    Synthesizer agent: RAG over approved KB + LLM teaching draft.

    Intentionally not fine-tuned — knowledge compounds through professor-approved
    retrieval, while Claude/mock drafts the teaching approach and student hint.
    """
    # Reuse the existing style-aware drafter as the reliable synthesizer core.
    draft = draft_with_claude(
        question_text=question_text,
        category=str(analyzer.get("category")),
        tags=list(analyzer.get("tags") or []),
        learning_style=learning_style or "unknown",
        urgency=str(analyzer.get("urgency") or "medium"),
    )

    if _use_mock() or draft.get("drafter_backend", "").startswith("mock"):
        kb_insight = _kb_insight(similar_questions)
        teaching = str(draft["answer_draft"])
        if code_snippet:
            teaching = (
                f"{teaching}\n\nCode focus: walk the failing branch in the snippet "
                "and verify pointer/recolor updates after each rotation."
            )
        return {
            "student_hint": str(draft["student_hint"]),
            "teaching_approach": teaching,
            "similar_count": len(similar_questions),
            "similar_questions": similar_questions[:3],
            "kb_insight": kb_insight,
            "backend": str(draft.get("drafter_backend") or "mock_claude"),
        }

    user = json.dumps(
        {
            "question": question_text,
            "code_snippet": code_snippet,
            "analyzer": analyzer,
            "learning_style": learning_style,
            "similar_questions": similar_questions[:3],
            "style_guidance": STYLE_TEACHING_GUIDANCE.get(
                learning_style or "unknown", STYLE_TEACHING_GUIDANCE["unknown"]
            ),
        },
        ensure_ascii=True,
    )
    try:
        raw = _call_claude(SYNTHESIZER_SYSTEM, user)
        data = _parse_json(raw)
        return {
            "student_hint": str(data.get("student_hint") or draft["student_hint"]),
            "teaching_approach": str(
                data.get("teaching_approach") or draft["answer_draft"]
            ),
            "similar_count": len(similar_questions),
            "similar_questions": similar_questions[:3],
            "kb_insight": str(data.get("kb_insight") or _kb_insight(similar_questions)),
            "backend": "claude",
        }
    except Exception:
        return {
            "student_hint": str(draft["student_hint"]),
            "teaching_approach": str(draft["answer_draft"]),
            "similar_count": len(similar_questions),
            "similar_questions": similar_questions[:3],
            "kb_insight": _kb_insight(similar_questions),
            "backend": "mock_claude_fallback",
        }


def _mock_analyze(
    question_text: str,
    *,
    code_snippet: str | None,
    course: str | None,
) -> dict[str, Any]:
    text = f"{question_text}\n{code_snippet or ''}".lower()
    tags: list[str] = []
    category = "General CS"
    difficulty = "MEDIUM"
    estimated = 15
    urgency = "medium"

    topic_rules = [
        (
            ("red-black", "red black", "rb tree", "rotation", "delete_fixup"),
            "Red-Black Tree Deletion",
            ["trees", "red-black", "deletion", "rotations"],
            15,
        ),
        (
            ("recursion", "base case", "stack overflow"),
            "Recursion",
            ["recursion", "base-case", "call-stack"],
            12,
        ),
        (
            ("binary search", "sorted array", "mid"),
            "Binary Search",
            ["search", "arrays", "invariants"],
            10,
        ),
        (
            ("hash", "collision", "bucket"),
            "Hashing",
            ["hashing", "collisions"],
            12,
        ),
        (
            ("dynamic programming", "dp", "memo"),
            "Dynamic Programming",
            ["dp", "memoization", "subproblems"],
            20,
        ),
        (
            ("pointer", "segfault", "null"),
            "Pointers / Memory",
            ["pointers", "memory"],
            15,
        ),
    ]

    for needles, label, topic_tags, minutes in topic_rules:
        if any(needle in text for needle in needles):
            category = label
            tags = list(topic_tags)
            estimated = minutes
            break

    if not tags:
        words = re.findall(r"[a-zA-Z][a-zA-Z\\-]{3,}", question_text.lower())
        stop = {"this", "that", "with", "from", "have", "about", "into", "when"}
        tags = [w for w in words if w not in stop][:4] or ["general"]

    if any(w in text for w in ("infinite", "urgent", "stuck", "broken", "crash")):
        urgency = "high"
        difficulty = "MEDIUM" if "infinite" in text else "HARD"
        estimated = max(estimated, 15)

    if course:
        tags = list(dict.fromkeys([*tags, course.lower().replace(" ", "-")]))

    return {
        "category": category,
        "difficulty": difficulty,
        "estimated_minutes": estimated,
        "tags": tags,
        "urgency": urgency,
        "rationale": f"Matched question cues to {category}.",
        "backend": "mock_claude",
    }


def _mock_match(
    analyzer: dict[str, Any],
    roster: list[dict[str, Any]],
) -> dict[str, Any]:
    tags = {str(tag).lower() for tag in analyzer.get("tags") or []}
    category = str(analyzer.get("category") or "").lower()

    scored: list[tuple[int, dict[str, Any]]] = []
    for ta in roster:
        expertise = {str(tag).lower() for tag in ta.get("expertise_tags") or []}
        overlap = len(tags & expertise)
        if any(token in category for token in expertise):
            overlap += 2
        # Prefer expertise, then shorter queue.
        score = overlap * 10 - int(ta.get("queue_depth") or 0)
        scored.append((score, ta))

    scored.sort(key=lambda item: (-item[0], int(item[1].get("queue_depth") or 0)))
    primary = scored[0][1]
    alternative = scored[1][1] if len(scored) > 1 else None
    wait = _wait_from_queue(primary, analyzer)

    rationale = (
        f"{primary['name']} matched on expertise "
        f"({', '.join(primary.get('expertise_tags') or [])}) "
        f"with queue depth {primary.get('queue_depth', 0)}."
    )
    return {
        "assigned_ta": primary["name"],
        "alternative_ta": alternative["name"] if alternative else None,
        "estimated_wait_minutes": wait,
        "rationale": rationale,
        "backend": "mock_claude",
    }


def _wait_from_queue(ta: dict[str, Any], analyzer: dict[str, Any]) -> int:
    per_ticket = int(analyzer.get("estimated_minutes") or 15)
    depth = int(ta.get("queue_depth") or 0)
    return max(per_ticket, per_ticket * max(depth, 1))


def _kb_insight(similar_questions: list[dict[str, Any]]) -> str:
    if not similar_questions:
        return "No closely matching approved KB entries yet — professor curation will grow this."
    count = len(similar_questions)
    return (
        f"Found {count} similar past question{'s' if count != 1 else ''} "
        "in the curated knowledge base for the TA teaching roadmap."
    )


def _compose_question_block(
    question_text: str,
    code_snippet: str | None,
    course: str | None,
) -> str:
    parts = [f"Course: {course or 'unspecified'}", f"Question: {question_text}"]
    if code_snippet:
        parts.append(f"Code:\n{code_snippet}")
    return "\n\n".join(parts)


def _use_mock() -> bool:
    flag = os.getenv("USE_MOCK_CLAUDE", "true").strip().lower()
    if flag in {"0", "false", "no"}:
        return not bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
    return True


def _call_claude(system: str, user: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY missing")

    payload = {
        "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        "max_tokens": 800,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.loads(response.read().decode("utf-8"))
    parts = body.get("content") or []
    texts = [part.get("text", "") for part in parts if part.get("type") == "text"]
    return "\n".join(texts).strip()


def _parse_json(raw: str) -> dict[str, Any]:
    cleaned = raw.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)
