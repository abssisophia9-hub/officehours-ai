"""
Knowledge-base drafting, curation helpers, and semantic retrieval.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.clustering import cosine_similarity, embed_text
from app.ai.summarizer import extract_keywords, summarize_request_cluster
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
        course_id=getattr(request, "course_id", None),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_faq_from_cluster(
    db: Session,
    *,
    cluster_id: int,
    course: str | None = None,
    course_id: int | None = None,
) -> KnowledgeEntry | None:
    query = db.query(Request).filter(Request.cluster_id == cluster_id)
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    elif course:
        query = query.filter(Request.course == course)
    members = query.order_by(Request.id).all()
    if not members:
        return None

    summary = summarize_request_cluster([item.text for item in members])
    title = str(summary["title"])
    question_text = f"FAQ: {title}"
    joined = "\n".join(f"- {item.text.strip()}" for item in members[:8])
    draft = draft_kb_with_model(
        question_text=question_text,
        category=members[0].category,
        tags=list(summary.get("keywords") or []),
        learning_style="unknown",
        urgency="medium",
        code_snippet=None,
    )
    answer = (
        f"Repeated question cluster ({len(members)} students).\n\n"
        f"Representative asks:\n{joined}\n\n"
        f"Draft FAQ answer:\n{draft['answer_draft']}"
    )
    entry = KnowledgeEntry(
        question_text=question_text,
        answer_draft=answer,
        student_hint=str(draft["student_hint"]),
        category=members[0].category or "faq",
        tags=_serialize_tags(["faq", "cluster", *list(summary.get("keywords") or [])]),
        urgency="medium",
        difficulty="medium",
        learning_style="unknown",
        drafter_backend=str(draft.get("drafter_backend") or "cluster_faq"),
        status="pending_review",
        source_request_id=members[0].id,
        cluster_id=cluster_id,
        course_id=course_id or getattr(members[0], "course_id", None),
        professor_note=f"Auto-drafted FAQ from cluster {cluster_id}",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def create_faq_from_insight(
    db: Session,
    *,
    course_id: int,
    topic_key: str,
) -> KnowledgeEntry | None:
    """Pending FAQ from a review-insight topic so the next cohort gets a better explanation."""
    from app.services.analytics_service import build_review_insights

    insights = build_review_insights(db, course_id=course_id)
    topic = next((item for item in insights.topics if item.topic_key == topic_key), None)
    if topic is None or not topic.questions:
        return None
    if topic.cluster_id is not None:
        clustered = create_faq_from_cluster(
            db,
            cluster_id=topic.cluster_id,
            course_id=course_id,
            course=insights.course_code,
        )
        if clustered is not None:
            clustered.professor_note = (
                f"Drafted from review insight “{topic.label}” for the next cohort / related chapter."
            )
            db.commit()
            db.refresh(clustered)
            return clustered

    texts = [item.text for item in topic.questions if item.text]
    summary = summarize_request_cluster(texts)
    title = str(summary.get("title") or topic.label)
    question_text = f"FAQ: {title} ({topic.label})"
    joined = "\n".join(f"- {text.strip()}" for text in texts[:8])
    draft = draft_kb_with_model(
        question_text=question_text,
        category=topic.label,
        tags=list(summary.get("keywords") or []),
        learning_style="unknown",
        urgency="medium",
        code_snippet=None,
    )
    source_request_id = next(
        (item.request_id for item in topic.questions if item.request_id),
        None,
    )
    entry = KnowledgeEntry(
        question_text=question_text,
        answer_draft=(
            f"Review-insight topic ({topic.total_signal} signals).\n\n"
            f"Representative asks:\n{joined}\n\n"
            f"Draft FAQ answer:\n{draft['answer_draft']}"
        ),
        student_hint=str(draft["student_hint"]),
        category="faq",
        tags=_serialize_tags(["faq", "review-insight", *list(summary.get("keywords") or [])]),
        urgency="medium",
        difficulty="medium",
        learning_style="unknown",
        drafter_backend=str(draft.get("drafter_backend") or "review_insight_faq"),
        status="pending_review",
        source_request_id=source_request_id,
        cluster_id=topic.cluster_id,
        course_id=course_id,
        professor_note=(
            f"Auto-drafted from review insight “{topic.label}” — tighten this "
            "explanation for coming students / related chapters."
        ),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def ingest_course_material(
    db: Session,
    *,
    title: str,
    content: str,
    source: str = "slides",
    course_id: int | None = None,
    course: str | None = None,
    auto_approve: bool = True,
    external_id: str | None = None,
) -> list[KnowledgeEntry]:
    chunks = _chunk_material(content)
    if not chunks:
        return []
    entries: list[KnowledgeEntry] = []
    status = "approved" if auto_approve else "pending_review"
    now = datetime.now(timezone.utc)
    note_bits = [f"{course or ''} material ingest: {title}".strip()]
    if external_id:
        note_bits.append(f"canvas:{external_id}")
    professor_note = " | ".join(bit for bit in note_bits if bit)
    for index, chunk in enumerate(chunks, start=1):
        question = f"{title} — part {index}"
        entry = KnowledgeEntry(
            question_text=question,
            answer_draft=chunk,
            student_hint=(
                f"This answer comes from course materials ({source}): {title}."
            ),
            category="course_material",
            tags=_serialize_tags(["course_material", source, title.lower()[:40]]),
            urgency="low",
            difficulty="medium",
            learning_style="unknown",
            drafter_backend=(
                "canvas_sync" if source == "canvas" else "course_material_ingest"
            ),
            status=status,
            source_request_id=None,
            cluster_id=None,
            course_id=course_id,
            material_source=source,
            professor_note=professor_note,
            reviewed_at=now if auto_approve else None,
        )
        db.add(entry)
        entries.append(entry)
    db.commit()
    for entry in entries:
        db.refresh(entry)
    return entries


def list_entries(
    db: Session,
    *,
    status_filter: str | None = None,
    course_id: int | None = None,
) -> list[KnowledgeEntry]:
    query = db.query(KnowledgeEntry)
    if status_filter:
        query = query.filter(KnowledgeEntry.status == status_filter)
    if course_id is not None:
        # Strict course scope — do not leak other courses' materials.
        query = query.filter(KnowledgeEntry.course_id == course_id)
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
    course_id: int | None = None,
) -> list[tuple[KnowledgeEntry, float]]:
    query = db.query(KnowledgeEntry).filter(KnowledgeEntry.status == "approved")
    if course_id is not None:
        # Strict course scope so CSC 3323 slides never answer CSC 2302 students.
        query = query.filter(KnowledgeEntry.course_id == course_id)
    approved = query.order_by(KnowledgeEntry.id).all()
    if not approved:
        return []

    query_embedding = embed_text(question)
    scored: list[tuple[KnowledgeEntry, float]] = []
    for entry in approved:
        # Prefer matching material content as well as the title/question.
        haystack = f"{entry.question_text}\n{entry.answer_draft}"
        similarity = cosine_similarity(query_embedding, embed_text(haystack))
        # Long slides dilute symmetric overlap, so fall back to containment:
        # what fraction of the question's content words appear in the doc.
        if similarity < similarity_threshold:
            similarity = max(
                similarity,
                _question_containment(question, haystack),
            )
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
        course_id=getattr(entry, "course_id", None),
        material_source=getattr(entry, "material_source", None),
        ta_resolution=getattr(entry, "ta_resolution", None),
        professor_note=entry.professor_note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        reviewed_at=entry.reviewed_at,
    )


def _chunk_material(content: str, *, max_chars: int = 900) -> list[str]:
    cleaned = content.replace("\r\n", "\n").strip()
    if not cleaned:
        return []
    paragraphs = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    if not paragraphs:
        paragraphs = [cleaned]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(paragraph) <= max_chars:
            current = paragraph
        else:
            for start in range(0, len(paragraph), max_chars):
                chunks.append(paragraph[start : start + max_chars].strip())
            current = ""
    if current:
        chunks.append(current)
    return chunks


_CONTAINMENT_STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "how", "i", "in",
    "is", "it", "my", "of", "on", "or", "the", "to", "what", "when", "where",
    "which", "why", "with", "you",
}


def _question_containment(question: str, haystack: str) -> float:
    from app.ai.clustering import _tokenize

    question_tokens = _tokenize(question) - _CONTAINMENT_STOPWORDS
    if not question_tokens:
        return 0.0
    doc_tokens = _tokenize(haystack)
    return len(question_tokens & doc_tokens) / len(question_tokens)


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
