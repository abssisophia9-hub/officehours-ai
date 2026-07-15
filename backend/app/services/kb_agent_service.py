"""
Student-facing knowledge-base agent.

Answers only from professor-approved KB entries using semantic retrieval.
Never exposes pending_review or rejected drafts to students.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import AgentAskResponse, KnowledgeSearchHit
from app.services.knowledge_service import search_approved_entries, to_out


def answer_from_knowledge_base(
    db: Session,
    question: str,
    *,
    top_k: int = 3,
    course_id: int | None = None,
) -> AgentAskResponse:
    matches = search_approved_entries(db, question, top_k=top_k, course_id=course_id)
    sources = [
        KnowledgeSearchHit(entry=to_out(entry), similarity=round(similarity, 4))
        for entry, similarity in matches
    ]

    if not sources:
        return AgentAskResponse(
            answer=(
                "I do not have a professor-approved answer for that yet. "
                "Submit a help request so a TA or the professor can review it, "
                "and it may be added to the course knowledge base after approval."
            ),
            student_hint=(
                "Write the smallest example that shows where you get stuck — "
                "that makes office-hours help much faster."
            ),
            confidence=0.0,
            matched_count=0,
            sources=[],
            used_approved_kb_only=True,
        )

    best = sources[0]
    supporting = sources[1:]
    answer_parts = [
        "Based on professor-approved course knowledge:",
        best.entry.answer_draft.strip(),
    ]
    if supporting:
        related = "; ".join(
            f"#{hit.entry.id} ({hit.similarity:.0%} match)" for hit in supporting
        )
        answer_parts.append(f"Related approved entries: {related}.")

    confidence = min(0.98, max(hit.similarity for hit in sources))
    return AgentAskResponse(
        answer="\n\n".join(answer_parts),
        student_hint=best.entry.student_hint,
        confidence=round(confidence, 4),
        matched_count=len(sources),
        sources=sources,
        used_approved_kb_only=True,
    )
