"""
Office Hours Oracle orchestration.

Runs Analyzer → Matcher → Synthesizer, keeps professor curation in the loop,
and records traces for metrics / lifetime confusion analytics.
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
from app.services.knowledge_service import search_approved_entries


def ensure_default_roster(db: Session) -> list[TaRoster]:
    existing = db.query(TaRoster).order_by(TaRoster.id).all()
    if existing:
        return existing

    for item in DEFAULT_TA_ROSTER:
        db.add(
            TaRoster(
                name=item["name"],
                expertise_tags=json.dumps(item["expertise_tags"]),
                queue_depth=int(item["queue_depth"]),
                is_available=True,
            )
        )
    db.commit()
    return db.query(TaRoster).order_by(TaRoster.id).all()


def run_oracle_pipeline(
    db: Session,
    *,
    question_text: str,
    code_snippet: str | None = None,
    course: str | None = None,
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

    roster_rows = ensure_default_roster(db)
    roster = [
        {
            "id": row.id,
            "name": row.name,
            "expertise_tags": json.loads(row.expertise_tags or "[]"),
            "queue_depth": row.queue_depth,
        }
        for row in roster_rows
        if row.is_available
    ]

    t1 = time.perf_counter()
    matcher = match_ta(analyzer, roster)
    steps.append(
        {
            "agent": "matcher",
            "elapsed_ms": int((time.perf_counter() - t1) * 1000),
            "output": matcher,
        }
    )

    similar = _similar_kb_hits(db, question_text)
    t2 = time.perf_counter()
    synthesizer = synthesize_solution(
        question_text=question_text,
        analyzer=analyzer,
        similar_questions=similar,
        learning_style=style,
        code_snippet=code_snippet,
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


def apply_oracle_to_request(
    db: Session,
    request: Request,
    oracle: dict[str, Any],
) -> Request:
    analyzer = oracle["analyzer"]
    matcher = oracle["matcher"]
    synthesizer = oracle["synthesizer"]
    classification = oracle["classification"]

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
    request.oracle_category = str(analyzer.get("category") or "")
    request.oracle_difficulty = str(analyzer.get("difficulty") or "MEDIUM")
    request.oracle_estimated_minutes = int(analyzer.get("estimated_minutes") or 15)
    request.oracle_tags = json.dumps(list(analyzer.get("tags") or []))
    request.assigned_ta = matcher.get("assigned_ta")
    request.alternative_ta = matcher.get("alternative_ta")
    request.estimated_wait_minutes = int(matcher.get("estimated_wait_minutes") or 15)
    request.student_hint = synthesizer.get("student_hint")
    request.oracle_trace_json = json.dumps(oracle)

    # Bump assigned TA queue depth for demo realism.
    assigned = (
        db.query(TaRoster)
        .filter(TaRoster.name == matcher.get("assigned_ta"))
        .one_or_none()
    )
    if assigned is not None:
        assigned.queue_depth = int(assigned.queue_depth or 0) + 1
        db.add(assigned)

    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def build_oracle_public_payload(oracle: dict[str, Any]) -> dict[str, Any]:
    """Shape returned to student kiosk / dashboards."""
    return {
        "analyzer": {
            "category": oracle["analyzer"].get("category"),
            "difficulty": oracle["analyzer"].get("difficulty"),
            "estimated_minutes": oracle["analyzer"].get("estimated_minutes"),
            "tags": oracle["analyzer"].get("tags") or [],
            "urgency": oracle["analyzer"].get("urgency"),
            "rationale": oracle["analyzer"].get("rationale"),
        },
        "matcher": {
            "assigned_ta": oracle["matcher"].get("assigned_ta"),
            "alternative_ta": oracle["matcher"].get("alternative_ta"),
            "estimated_wait_minutes": oracle["matcher"].get("estimated_wait_minutes"),
            "rationale": oracle["matcher"].get("rationale"),
        },
        "synthesizer": {
            "student_hint": oracle["synthesizer"].get("student_hint"),
            "teaching_approach": oracle["synthesizer"].get("teaching_approach"),
            "similar_count": oracle["synthesizer"].get("similar_count"),
            "similar_questions": oracle["synthesizer"].get("similar_questions") or [],
            "kb_insight": oracle["synthesizer"].get("kb_insight"),
        },
        "steps": [
            {
                "agent": step["agent"],
                "elapsed_ms": step["elapsed_ms"],
            }
            for step in oracle.get("steps") or []
        ],
        "elapsed_ms": oracle.get("elapsed_ms"),
    }


def lifetime_confusion_topics(db: Session, *, limit: int = 8) -> list[dict[str, Any]]:
    """
    Lifetime agent foundation: aggregate approved KB categories/tags that
    confuse students most across the semester.
    """
    entries = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.status == "approved")
        .order_by(KnowledgeEntry.id.desc())
        .all()
    )
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


def _similar_kb_hits(db: Session, question_text: str) -> list[dict[str, Any]]:
    try:
        matches = search_approved_entries(db, question_text, top_k=3)
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
    approved = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.status == "approved")
        .order_by(KnowledgeEntry.id.desc())
        .limit(20)
        .all()
    )
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
