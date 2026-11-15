"""
Ask Triage orchestration (renamed from the historical ``oracle_service``).

Runs Analyzer → Matcher → Synthesizer, keeps professor curation in the loop,
and records traces for metrics / lifetime confusion analytics.
Columns, API fields, and WebSocket events use the ``triage_*`` / ``triage.*``
prefix; ``oracle_*`` was the pre-rename spelling.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from sqlalchemy.orm import Session

from app.ai.analyzer_agent import CATEGORY_DISPLAY
from app.ai.claude_client import analyze_question, match_ta, synthesize_solution
from app.ai.clustering import cosine_similarity, embed_text
from app.models.knowledge import KnowledgeEntry
from app.models.request import Request
from app.models.ta_roster import DEFAULT_TA_ROSTER, TaRoster
from app.services.classification_service import classify_and_recommend
from app.services.course_ta_service import (
    assign_professor_when_no_ta,
    build_course_matcher_roster,
    course_ta_memberships,
)
from app.services.demo_mode import demo_mode
from app.services.knowledge_service import search_approved_entries


def ensure_default_roster(db: Session) -> list[TaRoster]:
    """Seed or refresh the demo TA roster so expertise tags stay current."""
    if not demo_mode():
        return db.query(TaRoster).order_by(TaRoster.id).all()
    by_name = {row.name: row for row in db.query(TaRoster).all()}
    changed = False
    for item in DEFAULT_TA_ROSTER:
        tags_json = json.dumps(item["expertise_tags"])
        existing = by_name.get(item["name"])
        if existing is None:
            db.add(
                TaRoster(
                    name=item["name"],
                    expertise_tags=tags_json,
                    queue_depth=int(item["queue_depth"]),
                    is_available=True,
                )
            )
            changed = True
            continue
        if existing.expertise_tags != tags_json:
            existing.expertise_tags = tags_json
            db.add(existing)
            changed = True
    if changed:
        db.commit()
    return db.query(TaRoster).order_by(TaRoster.id).all()


def run_ask_triage_pipeline(
    db: Session,
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
    course_id: int | None = None,
    learning_style: str | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    steps: list[dict[str, Any]] = []

    # Keep existing classifier for category compatibility with professor dashboard.
    # Prefer ML when available so Analyzer + dashboard taxonomy stay aligned.
    previous_backend = os.environ.get("OFFICEHOURS_CLASSIFIER_BACKEND")
    if previous_backend is None:
        os.environ["OFFICEHOURS_CLASSIFIER_BACKEND"] = "ml"
    try:
        classification = classify_and_recommend(question_text)
    finally:
        if previous_backend is None:
            os.environ.pop("OFFICEHOURS_CLASSIFIER_BACKEND", None)
        else:
            os.environ["OFFICEHOURS_CLASSIFIER_BACKEND"] = previous_backend
    style = learning_style or str(classification.get("learning_style") or "unknown")

    t0 = time.perf_counter()
    analyzer = analyze_question(
        question_text=question_text,
        code_snippet=code_snippet,
        course=course,
    )
    # Prefer trained taxonomy for dashboard routing; keep Analyzer display label.
    if analyzer.get("ml_category"):
        classification["category"] = analyzer["ml_category"]
    if analyzer.get("urgency"):
        classification["urgency"] = analyzer["urgency"]
    if analyzer.get("category") in {None, "", "General", "General CS"}:
        analyzer["category"] = str(
            CATEGORY_DISPLAY.get(
                str(classification.get("category")),
                classification.get("category") or analyzer["category"],
            )
        )
    steps.append(
        {
            "agent": "analyzer",
            "elapsed_ms": int((time.perf_counter() - t0) * 1000),
            "output": analyzer,
        }
    )

    ensure_default_roster(db)
    t1 = time.perf_counter()
    # A course with at least one TA keeps the expertise + queue matcher.
    # No TA membership at all: the professor (lowest user id) gets the ask.
    if course_id is not None and not course_ta_memberships(db, course_id):
        matcher = assign_professor_when_no_ta(
            db,
            course_id=course_id,
            analyzer=analyzer,
            course_code=course,
        )
    else:
        roster = build_course_matcher_roster(db, course_id=course_id)
        matcher = match_ta(analyzer, roster, question_text=question_text)
        if roster and all(row.get("course_scoped") for row in roster):
            matcher["rationale"] = (
                f"{matcher.get('rationale') or ''} "
                f"[course-scoped: {len(roster)} TA(s) on this course; "
                f"primary + backup with queue-depth load balance]."
            ).strip()
        if matcher.get("assigned_ta") and matcher.get("assigned_ta") != "Unassigned":
            matcher["assignee_role"] = "ta"
    steps.append(
        {
            "agent": "matcher",
            "elapsed_ms": int((time.perf_counter() - t1) * 1000),
            "output": matcher,
        }
    )

    similar = _similar_kb_hits(db, question_text, course_id=course_id)
    t2 = time.perf_counter()
    synthesizer = synthesize_solution(
        question_text=question_text,
        analyzer=analyzer,
        similar_questions=similar,
        learning_style=style,
        code_snippet=code_snippet,
        course=course,
    )
    steps.append(
        {
            "agent": "synthesizer",
            "elapsed_ms": int((time.perf_counter() - t2) * 1000),
            "output": synthesizer,
        }
    )

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return {
        "analyzer": analyzer,
        "matcher": matcher,
        "synthesizer": synthesizer,
        "classification": {
            "category": classification.get("category"),
            "urgency": classification.get("urgency"),
            "learning_style": style,
            "recommended_action": classification.get("recommended_action"),
            "matched_keywords": classification.get("matched_keywords") or [],
        },
        "steps": steps,
        "elapsed_ms": elapsed_ms,
    }


def apply_triage_to_request(
    db: Session,
    request: Request,
    triage: dict[str, Any],
) -> Request:
    analyzer = triage["analyzer"]
    matcher = triage["matcher"]
    synthesizer = triage["synthesizer"]
    classification = triage["classification"]

    request.category = str(
        classification.get("category") or analyzer.get("category") or request.category
    )
    request.urgency = str(
        classification.get("urgency") or analyzer.get("urgency") or request.urgency
    )
    request.learning_style = str(
        classification.get("learning_style") or request.learning_style or "unknown"
    )
    request.recommended_action = str(
        classification.get("recommended_action") or request.recommended_action
    )
    if bool(getattr(request, "sensitive", False)) or (
        request.category
        in {
            "emotional_stress",
            "accessibility_accommodation",
            "academic_integrity",
            "retake_request",
            "grading_dispute",
        }
    ):
        request.sensitive = True
        request.recommended_action = (
            "Private 1:1 / admin route - do not discuss in a public group review"
        )
    request.triage_category = str(analyzer.get("category") or "")
    request.triage_difficulty = str(analyzer.get("difficulty") or "MEDIUM")
    request.triage_estimated_minutes = int(analyzer.get("estimated_minutes") or 15)
    request.triage_tags = json.dumps(list(analyzer.get("tags") or []))
    request.assigned_ta = matcher.get("assigned_ta")
    request.alternative_ta = matcher.get("alternative_ta")
    request.assignee_role = matcher.get("assignee_role")
    request.assignee_user_id = matcher.pop("assignee_user_id", None)
    request.estimated_wait_minutes = int(matcher.get("estimated_wait_minutes") or 15)
    request.student_hint = synthesizer.get("student_hint")
    request.triage_trace_json = json.dumps(triage)

    # Bump assigned TA queue depth for demo realism.
    assigned = (
        db.query(TaRoster)
        .filter(TaRoster.name == matcher.get("assigned_ta"))
        .one_or_none()
    )
    # Global roster depth is demo-only. Course-scoped Matcher counts open
    # asks on this course so Alice's 2302 queue does not inflate another course.
    if assigned is not None and not request.course_id:
        assigned.queue_depth = int(assigned.queue_depth or 0) + 1
        db.add(assigned)

    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def build_triage_public_payload(triage: dict[str, Any]) -> dict[str, Any]:
    """Shape returned to student kiosk / dashboards."""
    return {
        "analyzer": {
            "category": triage["analyzer"].get("category"),
            "difficulty": triage["analyzer"].get("difficulty"),
            "estimated_minutes": triage["analyzer"].get("estimated_minutes"),
            "tags": triage["analyzer"].get("tags") or [],
            "urgency": triage["analyzer"].get("urgency"),
            "rationale": triage["analyzer"].get("rationale"),
        },
        "matcher": {
            "assigned_ta": triage["matcher"].get("assigned_ta"),
            "alternative_ta": triage["matcher"].get("alternative_ta"),
            "estimated_wait_minutes": triage["matcher"].get("estimated_wait_minutes"),
            "rationale": triage["matcher"].get("rationale"),
            "assignee_role": triage["matcher"].get("assignee_role"),
        },
        "synthesizer": {
            "student_hint": triage["synthesizer"].get("student_hint"),
            "teaching_approach": triage["synthesizer"].get("teaching_approach"),
            "similar_count": triage["synthesizer"].get("similar_count"),
            "similar_questions": triage["synthesizer"].get("similar_questions") or [],
            "kb_insight": triage["synthesizer"].get("kb_insight"),
        },
        "steps": [
            {
                "agent": step["agent"],
                "elapsed_ms": step["elapsed_ms"],
            }
            for step in triage.get("steps") or []
        ],
        "elapsed_ms": triage.get("elapsed_ms"),
    }


def lifetime_confusion_topics(
    db: Session, *, limit: int = 8, course_ids: list[int] | None = None
) -> list[dict[str, Any]]:
    """
    Lifetime agent foundation: aggregate approved KB categories/tags that
    confuse students most across the semester.
    """
    query = db.query(KnowledgeEntry).filter(KnowledgeEntry.status == "approved")
    if course_ids is not None:
        query = query.filter(KnowledgeEntry.course_id.in_(course_ids or [-1]))
    entries = query.order_by(KnowledgeEntry.id.desc()).all()
    counts: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = (entry.category or "uncategorized").strip() or "uncategorized"
        bucket = counts.setdefault(
            key,
            {"topic": key, "approved_count": 0, "tags": {}, "sample_question": entry.question_text},
        )
        bucket["approved_count"] += 1
        for tag in json.loads(entry.tags or "[]"):
            bucket["tags"][tag] = bucket["tags"].get(tag, 0) + 1

    ranked = sorted(counts.values(), key=lambda item: item["approved_count"], reverse=True)
    result = []
    for item in ranked[:limit]:
        top_tags = sorted(item["tags"].items(), key=lambda pair: pair[1], reverse=True)
        result.append(
            {
                "topic": item["topic"],
                "approved_count": item["approved_count"],
                "top_tags": [tag for tag, _ in top_tags[:5]],
                "sample_question": item["sample_question"],
                "agent_advice": (
                    f"Semester confusion hotspot: {item['topic']}. "
                    "Prioritize FAQ cards and group review for this topic."
                ),
            }
        )
    return result


def _similar_kb_hits(
    db: Session, question_text: str, *, course_id: int | None = None
) -> list[dict[str, Any]]:
    try:
        matches = search_approved_entries(
            db, question_text, top_k=3, course_id=course_id
        )
    except Exception:
        return []

    hits = []
    for entry, score in matches:
        hits.append(
            {
                "id": entry.id,
                "question_text": entry.question_text,
                "category": entry.category,
                "score": round(float(score), 3),
            }
        )
    if hits:
        return hits

    # Fallback lexical-ish: embed against approved texts if search returns empty.
    approved_q = db.query(KnowledgeEntry).filter(KnowledgeEntry.status == "approved")
    if course_id is not None:
        approved_q = approved_q.filter(KnowledgeEntry.course_id == course_id)
    approved = approved_q.order_by(KnowledgeEntry.id.desc()).limit(20).all()
    if not approved:
        return []
    query_vec = embed_text(question_text)
    scored = []
    for entry in approved:
        score = cosine_similarity(query_vec, embed_text(entry.question_text))
        scored.append((score, entry))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [
        {
            "id": entry.id,
            "question_text": entry.question_text,
            "category": entry.category,
            "score": round(float(score), 3),
        }
        for score, entry in scored[:3]
        if score >= 0.2
    ]
