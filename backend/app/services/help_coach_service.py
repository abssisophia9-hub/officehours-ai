"""
Help Coach — TA-facing AI co-pilot while helping a student.

Ask Triage / Oracle (Analyzer → Matcher → Synthesizer) runs once at intake.
Help Coach runs *during* the TA staffing loop: similar open asks, approved KB
neighbors, teaching script, Socratic steps, and draft student replies.

Uses the same local RAG stack as the Synthesizer / Study Agent (no external LLM).
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.ai.synthesizer_model import synthesize_with_model
from app.models.knowledge import KnowledgeEntry
from app.models.request import Request
from app.services.knowledge_service import search_approved_entries

AssistMode = Literal["draft_reply", "socratic", "refresh_teaching", "rewrite_reply"]

OPEN_WORK = {"open", "claimed", "in_progress"}


def build_help_coach(
    db: Session,
    request: Request,
    *,
    knowledge_entry: KnowledgeEntry | None = None,
) -> dict[str, Any]:
    """Snapshot Help Coach payload for one queue item / selected ask."""
    teaching = _teaching_approach(request, knowledge_entry)
    hint = _student_hint(request, knowledge_entry)
    kb_insight = _kb_insight(request)
    similar_kb = _similar_kb(db, request)
    similar_open = _similar_open_asks(db, request)
    steps = _socratic_steps(
        teaching_approach=teaching,
        difficulty=request.oracle_difficulty,
        category=request.oracle_category or request.category,
        learning_style=request.learning_style,
    )
    return {
        "teaching_approach": teaching,
        "student_hint": hint,
        "kb_insight": kb_insight,
        "difficulty": request.oracle_difficulty,
        "estimated_minutes": request.oracle_estimated_minutes,
        "learning_style": request.learning_style,
        "category": request.oracle_category or request.category,
        "similar_open_count": len(similar_open),
        "similar_open": similar_open,
        "similar_kb": similar_kb,
        "socratic_steps": steps,
        "group_help_suggested": len(similar_open) >= 2,
        "coach_summary": _coach_summary(
            similar_open_count=len(similar_open),
            similar_kb_count=len(similar_kb),
            difficulty=request.oracle_difficulty,
            estimated_minutes=request.oracle_estimated_minutes,
        ),
    }


def run_help_coach_assist(
    db: Session,
    request: Request,
    *,
    mode: AssistMode,
    knowledge_entry: KnowledgeEntry | None = None,
    current_reply: str | None = None,
    focus: str | None = None,
) -> dict[str, Any]:
    """Generate a Help Coach action for the TA."""
    coach = build_help_coach(db, request, knowledge_entry=knowledge_entry)

    if mode == "refresh_teaching":
        refreshed = _refresh_teaching(db, request)
        teaching = refreshed["teaching_approach"]
        hint = refreshed["student_hint"]
        kb_insight = refreshed["kb_insight"]
        steps = _socratic_steps(
            teaching_approach=teaching,
            difficulty=request.oracle_difficulty,
            category=request.oracle_category or request.category,
            learning_style=request.learning_style,
        )
        coach.update(
            {
                "teaching_approach": teaching,
                "student_hint": hint,
                "kb_insight": kb_insight,
                "socratic_steps": steps,
                "similar_kb": refreshed.get("similar_kb") or coach["similar_kb"],
            }
        )
        return {
            "mode": mode,
            "message": "Refreshed teaching script from approved KB / teaching bank.",
            "draft_reply": None,
            "teaching_approach": teaching,
            "student_hint": hint,
            "socratic_steps": steps,
            "help_coach": coach,
            "backend": refreshed.get("backend") or "help_coach_refresh",
        }

    if mode == "socratic":
        steps = list(coach["socratic_steps"])
        if focus and focus.strip():
            steps = [f"Focus on: {focus.strip()}", *steps]
        return {
            "mode": mode,
            "message": "Socratic teaching steps ready — ask these while helping.",
            "draft_reply": None,
            "teaching_approach": coach["teaching_approach"],
            "student_hint": coach["student_hint"],
            "socratic_steps": steps,
            "help_coach": coach,
            "backend": "help_coach_socratic",
        }

    if mode == "rewrite_reply":
        source = (current_reply or request.ta_reply or coach["student_hint"] or "").strip()
        if len(source) < 3:
            source = _compose_draft_reply(request, coach, focus=focus)
        draft = _rewrite_reply(source, request, coach)
        return {
            "mode": mode,
            "message": "Rewrote reply for clarity (student-facing).",
            "draft_reply": draft,
            "teaching_approach": coach["teaching_approach"],
            "student_hint": coach["student_hint"],
            "socratic_steps": coach["socratic_steps"],
            "help_coach": coach,
            "backend": "help_coach_rewrite",
        }

    draft = _compose_draft_reply(request, coach, focus=focus)
    return {
        "mode": "draft_reply",
        "message": "Drafted a student reply from the teaching script + KB.",
        "draft_reply": draft,
        "teaching_approach": coach["teaching_approach"],
        "student_hint": coach["student_hint"],
        "socratic_steps": coach["socratic_steps"],
        "help_coach": coach,
        "backend": "help_coach_draft",
    }


def _teaching_approach(
    request: Request, knowledge_entry: KnowledgeEntry | None
) -> str:
    if knowledge_entry and (knowledge_entry.answer_draft or "").strip():
        return knowledge_entry.answer_draft.strip()
    synth = _synthesizer_blob(request)
    if synth.get("teaching_approach"):
        return str(synth["teaching_approach"]).strip()
    return (
        "1. Restate the stuck point in one sentence.\n"
        "2. Work the smallest example that isolates the bug.\n"
        "3. Check the invariant / assumption that broke.\n"
        "4. Ask the student to restate the fix in their own words."
    )


def _student_hint(request: Request, knowledge_entry: KnowledgeEntry | None) -> str:
    if knowledge_entry and (knowledge_entry.student_hint or "").strip():
        return knowledge_entry.student_hint.strip()
    if (request.student_hint or "").strip():
        return request.student_hint.strip()
    synth = _synthesizer_blob(request)
    return str(synth.get("student_hint") or "").strip()


def _kb_insight(request: Request) -> str | None:
    synth = _synthesizer_blob(request)
    insight = synth.get("kb_insight")
    return str(insight).strip() if insight else None


def _synthesizer_blob(request: Request) -> dict[str, Any]:
    if not request.oracle_trace_json:
        return {}
    try:
        trace = json.loads(request.oracle_trace_json)
    except Exception:
        return {}
    return dict(trace.get("synthesizer") or {})


def _similar_kb(db: Session, request: Request) -> list[dict[str, Any]]:
    """Approved KB neighbors — live re-search so coach stays current."""
    matches = search_approved_entries(
        db,
        request.text,
        top_k=3,
        course_id=request.course_id,
    )
    out: list[dict[str, Any]] = []
    for entry, score in matches:
        out.append(
            {
                "id": entry.id,
                "question_text": entry.question_text,
                "category": entry.category,
                "similarity": round(float(score), 4),
                "student_hint": entry.student_hint,
                "answer_preview": (entry.answer_draft or "")[:280],
            }
        )
    if out:
        return out

    synth = _synthesizer_blob(request)
    for item in list(synth.get("similar_questions") or [])[:3]:
        out.append(
            {
                "id": item.get("id"),
                "question_text": item.get("question_text") or item.get("text"),
                "category": item.get("category"),
                "similarity": item.get("score") or item.get("similarity"),
                "student_hint": item.get("student_hint"),
                "answer_preview": (item.get("answer_draft") or "")[:280],
            }
        )
    return out


def _similar_open_asks(db: Session, request: Request) -> list[dict[str, Any]]:
    """Other open asks in the same course cluster / category (group-help cue)."""
    q = db.query(Request).filter(Request.id != request.id)
    if request.course_id is not None:
        q = q.filter(Request.course_id == request.course_id)
    elif request.course:
        q = q.filter(Request.course == request.course)

    rows = q.order_by(Request.created_at.desc()).all()
    cluster_id = request.cluster_id
    category = (request.oracle_category or request.category or "").strip().lower()

    matches: list[dict[str, Any]] = []
    for row in rows:
        work = str(getattr(row, "work_status", None) or "open")
        if work not in OPEN_WORK:
            continue
        same_cluster = (
            cluster_id is not None
            and row.cluster_id is not None
            and row.cluster_id == cluster_id
        )
        row_cat = (row.oracle_category or row.category or "").strip().lower()
        same_category = bool(category and row_cat and row_cat == category)
        if not (same_cluster or same_category):
            continue
        matches.append(
            {
                "id": row.id,
                "text": row.text,
                "work_status": work,
                "assigned_ta": row.assigned_ta,
                "cluster_id": row.cluster_id,
                "category": row.oracle_category or row.category,
                "match_reason": "cluster" if same_cluster else "category",
            }
        )
        if len(matches) >= 5:
            break
    return matches


def _socratic_steps(
    *,
    teaching_approach: str,
    difficulty: str | None,
    category: str | None,
    learning_style: str | None,
) -> list[str]:
    """Turn the teaching script into ask-the-student prompts."""
    numbered = re.findall(
        r"(?:^|\n)\s*\d+[.)]\s*(.+)",
        teaching_approach or "",
    )
    steps: list[str] = []
    for line in numbered[:5]:
        cleaned = line.strip().rstrip(".")
        if not cleaned:
            continue
        lower = cleaned.lower()
        if lower.startswith(("ask ", "what ", "why ", "how ", "where ", "can ")):
            steps.append(cleaned if cleaned.endswith("?") else f"{cleaned}?")
        else:
            steps.append(f"Can you show me: {cleaned}?")

    topic = (category or "this concept").replace("_", " ")
    style = (learning_style or "unknown").replace("_", " ")
    diff = (difficulty or "MEDIUM").upper()

    if not steps:
        steps = [
            f"In one sentence, what about {topic} is breaking for you?",
            "Walk me through the smallest example where it still works.",
            "Where does that example first go wrong?",
            "What would you try next, before I hint?",
        ]

    if diff == "HARD":
        steps.append(
            "Before coding the fix: which invariant must stay true after each step?"
        )
    elif diff == "EASY":
        steps.append(f"Can you restate the rule for {topic} in your own words?")

    if style and style != "unknown":
        steps.append(f"Prefer a {style} explanation — sketch or example first?")

    seen: set[str] = set()
    unique: list[str] = []
    for step in steps:
        key = step.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(step)
    return unique[:6]


def _compose_draft_reply(
    request: Request,
    coach: dict[str, Any],
    *,
    focus: str | None = None,
) -> str:
    del request  # reserved for future personalization
    topic = (coach.get("category") or "your question").replace("_", " ")
    hint = (coach.get("student_hint") or "").strip()
    teaching = (coach.get("teaching_approach") or "").strip()
    kb = list(coach.get("similar_kb") or [])
    steps = list(coach.get("socratic_steps") or [])

    bullets: list[str] = []
    numbered = re.findall(r"(?:^|\n)\s*\d+[.)]\s*(.+)", teaching)
    for line in numbered[:3]:
        bullets.append(f"- {line.strip()}")
    if not bullets and steps:
        for step in steps[:3]:
            bullets.append(f"- {step}")

    parts = [
        f"Thanks for the ask about {topic}.",
        "",
        "Here's a focused path to unblock you:",
    ]
    if bullets:
        parts.extend(bullets)
    else:
        parts.append("- Restate the stuck point, then try the smallest failing example.")

    if kb:
        best = kb[0]
        preview = (best.get("answer_preview") or "").strip()
        if preview:
            parts.extend(
                [
                    "",
                    "Related approved course note (use as a map, not a copy-paste):",
                    preview[:220] + ("…" if len(preview) > 220 else ""),
                ]
            )

    if hint:
        parts.extend(["", f"Try this check next: {hint}"])

    if focus and focus.strip():
        parts.extend(["", f"Focusing on what you flagged: {focus.strip()}"])

    parts.extend(
        [
            "",
            "Reply with what you tried and where it still fails — happy to continue.",
        ]
    )
    return "\n".join(parts).strip()


def _rewrite_reply(source: str, request: Request, coach: dict[str, Any]) -> str:
    text = " ".join(source.split()).strip()
    topic = (coach.get("category") or request.oracle_category or "this").replace(
        "_", " "
    )
    hint = (coach.get("student_hint") or "").strip()
    body = text
    if not body.endswith((".", "!", "?")):
        body = body + "."
    lines = [
        f"Quick follow-up on {topic}:",
        "",
        body,
    ]
    if hint and hint.lower() not in body.lower():
        lines.extend(["", f"Next check: {hint}"])
    lines.extend(["", "Tell me what changes after you try that."])
    return "\n".join(lines).strip()


def _refresh_teaching(db: Session, request: Request) -> dict[str, Any]:
    similar = []
    for entry, score in search_approved_entries(
        db, request.text, top_k=3, course_id=request.course_id
    ):
        similar.append(
            {
                "id": entry.id,
                "question_text": entry.question_text,
                "category": entry.category,
                "score": round(float(score), 4),
                "answer_draft": entry.answer_draft,
                "student_hint": entry.student_hint,
            }
        )
    analyzer = {
        "category": request.oracle_category or request.category or "General",
        "ml_category": request.category or "uncategorized",
        "tags": _tags(request),
        "urgency": request.urgency or "medium",
        "difficulty": request.oracle_difficulty or "MEDIUM",
    }
    result = synthesize_with_model(
        question_text=request.text,
        analyzer=analyzer,
        similar_questions=similar,
        learning_style=request.learning_style,
        code_snippet=request.code_snippet,
    )
    similar_kb = [
        {
            "id": item.get("id"),
            "question_text": item.get("question_text"),
            "category": item.get("category"),
            "similarity": item.get("score") or item.get("similarity"),
            "student_hint": item.get("student_hint"),
            "answer_preview": (item.get("answer_draft") or "")[:280],
        }
        for item in (result.get("similar_questions") or similar)[:3]
    ]
    return {
        "teaching_approach": str(result.get("teaching_approach") or ""),
        "student_hint": str(result.get("student_hint") or ""),
        "kb_insight": str(result.get("kb_insight") or ""),
        "backend": result.get("backend"),
        "similar_kb": similar_kb,
    }


def _tags(request: Request) -> list[str]:
    if not request.oracle_tags:
        return []
    try:
        parsed = json.loads(request.oracle_tags)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    return []


def _coach_summary(
    *,
    similar_open_count: int,
    similar_kb_count: int,
    difficulty: str | None,
    estimated_minutes: int | None,
) -> str:
    bits = []
    if difficulty:
        bits.append(str(difficulty))
    if estimated_minutes is not None:
        bits.append(f"~{estimated_minutes} min")
    if similar_open_count:
        bits.append(f"{similar_open_count} similar open")
    if similar_kb_count:
        bits.append(f"{similar_kb_count} approved KB")
    return " · ".join(bits) if bits else "Help Coach ready"
