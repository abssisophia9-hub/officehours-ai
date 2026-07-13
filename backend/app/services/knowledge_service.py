"""
Knowledge-base drafting, curation helpers, and semantic retrieval.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.clustering import cosine_similarity, embed_text
from app.ai.summarizer import extract_keywords
from app.ai.synthesizer_model import draft_kb_with_model
from app.models.knowledge import KnowledgeEntry, KnowledgeEntryOut, KnowledgeEntryUpdate
from app.models.request import Request

DEFAULT_SEARCH_THRESHOLD = 0.35
DIFFICULTY_BY_URGENCY = {
    "urgent": "hard",
    "high": "hard",
    "medium": "medium",
    "low": "easy",
}


def create_pending_entry_from_request(
    db: Session,
    request: Request,
    *,
    urgency: str | None = None,
    matched_keywords: list[str] | None = None,
    learning_style: str | None = None,
) -> KnowledgeEntry:
    tags = matched_keywords or extract_keywords([request.text], max_keywords=4)
    style = learning_style or getattr(request, "learning_style", None) or "unknown"
    difficulty = DIFFICULTY_BY_URGENCY.get((urgency or "").lower(), "medium")
    draft = draft_kb_with_model(
        question_text=request.text,
        category=request.category,
        tags=tags,
        learning_style=style,
        urgency=urgency or getattr(request, "urgency", None),
        code_snippet=getattr(request, "code_snippet", None),
    )
    entry = KnowledgeEntry(
        question_text=request.text,
        answer_draft=str(draft["answer_draft"]),
        student_hint=str(draft["student_hint"]),
        category=request.category,
        tags=_serialize_tags(tags),
        urgency=urgency or getattr(request, "urgency", None),
        difficulty=difficulty,
        learning_style=style,
        drafter_backend=str(draft.get("drafter_backend") or "custom_synthesizer"),
        status="pending_review",
        source_request_id=request.id,
        cluster_id=request.cluster_id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_entries(
    db: Session,
    *,
    status_filter: str | None = None,
) -> list[KnowledgeEntry]:
    query = db.query(KnowledgeEntry)
    if status_filter:
        query = query.filter(KnowledgeEntry.status == status_filter)
    return query.order_by(KnowledgeEntry.id.desc()).all()


def update_entry(
    db: Session,
    entry: KnowledgeEntry,
    payload: KnowledgeEntryUpdate,
) -> KnowledgeEntry:
    if payload.answer_draft is not None:
        entry.answer_draft = payload.answer_draft.strip()
    if payload.student_hint is not None:
        entry.student_hint = payload.student_hint.strip()
    if payload.professor_note is not None:
        entry.professor_note = payload.professor_note.strip() or None
    if payload.tags is not None:
        entry.tags = _serialize_tags(payload.tags)
    if payload.difficulty is not None:
        entry.difficulty = payload.difficulty.strip() or None
    if payload.status is not None:
        entry.status = payload.status
        if payload.status in {"approved", "rejected"}:
            entry.reviewed_at = datetime.now(timezone.utc)

    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def search_approved_entries(
    db: Session,
    question: str,
    *,
    top_k: int = 3,
    similarity_threshold: float = DEFAULT_SEARCH_THRESHOLD,
) -> list[tuple[KnowledgeEntry, float]]:
    approved = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.status == "approved")
        .order_by(KnowledgeEntry.id)
        .all()
    )
    if not approved:
        return []

    query_embedding = embed_text(question)
    scored: list[tuple[KnowledgeEntry, float]] = []
    for entry in approved:
        similarity = cosine_similarity(query_embedding, embed_text(entry.question_text))
        if similarity >= similarity_threshold:
            scored.append((entry, similarity))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]


def to_out(entry: KnowledgeEntry) -> KnowledgeEntryOut:
    return KnowledgeEntryOut(
        id=entry.id,
        question_text=entry.question_text,
        answer_draft=entry.answer_draft,
        student_hint=entry.student_hint,
        category=entry.category,
        tags=_deserialize_tags(entry.tags),
        urgency=entry.urgency,
        difficulty=entry.difficulty,
        learning_style=entry.learning_style,
        drafter_backend=entry.drafter_backend,
        status=entry.status,  # type: ignore[arg-type]
        source_request_id=entry.source_request_id,
        cluster_id=entry.cluster_id,
        professor_note=entry.professor_note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        reviewed_at=entry.reviewed_at,
    )


def _serialize_tags(tags: list[str]) -> str:
    cleaned = [tag.strip() for tag in tags if tag and tag.strip()]
    return json.dumps(cleaned)


def _deserialize_tags(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []
