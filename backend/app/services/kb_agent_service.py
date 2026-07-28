"""
Student-facing knowledge-base agent.

Answers only from professor-approved KB entries using semantic retrieval.
Never exposes pending_review or rejected drafts to students.

When the course KB has no useful match, the agent stops guessing and steers
the student toward Quiet ask / TA / professor help — spinning on incomplete
materials wastes time.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.knowledge import AgentAskResponse, KnowledgeSearchHit
from app.services.knowledge_service import search_approved_entries, to_out

# Below this similarity we treat a hit as too weak to answer from.
WEAK_MATCH_CONFIDENCE = 0.42

NO_MATCH_ANSWER = (
    "I don't have professor-approved course material that answers this yet — "
    "guessing would waste your time.\n\n"
    "Don't keep rephrasing into this agent. Use Quiet ask (anonymous) or reach "
    "out to your TA / professor in office hours. Once they help and the "
    "professor approves the FAQ, the next student gets the answer instantly."
)

NO_MATCH_HINT = (
    "Submit a Quiet ask with the smallest example that shows where you're stuck. "
    "Staff will help — you do not need to wait on incomplete course materials."
)


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

    if not sources or sources[0].similarity < WEAK_MATCH_CONFIDENCE:
        return AgentAskResponse(
            answer=NO_MATCH_ANSWER,
            student_hint=NO_MATCH_HINT,
            confidence=round(sources[0].similarity, 4) if sources else 0.0,
            matched_count=0,
            sources=[],
            used_approved_kb_only=True,
            should_seek_help=True,
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
        should_seek_help=False,
    )
