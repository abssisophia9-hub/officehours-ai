"""
Student-facing knowledge-base agent.

Answers only from professor-approved KB entries using semantic retrieval.
Never exposes pending_review or rejected drafts to students.

When the course KB has no useful match, the agent stops guessing and steers
the student toward Quiet ask / TA / professor help — spinning on incomplete
materials wastes time.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.ai.claude_client import AnswerCheckClient
from app.models.knowledge import AgentAskResponse, KnowledgeSearchHit
# Bound on this module so the policy and the tests patch the same search.
from app.services.knowledge_service import search_approved_entries

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

# Used only after a check ran and did not confirm a quote. Distinct from the
# below-cutoff answer so the two paths can be told apart.
CHECK_MISS_ANSWER = "I couldn't confirm an answer in the approved course material."


def _cite_entry(entry) -> str:
    filename = (getattr(entry, "source_filename", None) or "").strip()
    page = getattr(entry, "page_number", None)
    chunk = getattr(entry, "chunk_index", None)
    if filename and page is not None and chunk is not None:
        return f"{filename}, p. {page}, chunk {chunk}"
    title = (getattr(entry, "question_text", None) or "").strip()
    if len(title) > 72:
        title = title[:69] + "…"
    source = (getattr(entry, "material_source", None) or "").strip()
    if title and source:
        return f"{title} ({source})"
    return title or source or "Approved FAQ"


def _retrieval_answer(sources: list[KnowledgeSearchHit], approved_only: bool) -> AgentAskResponse:
    best = sources[0]
    supporting = sources[1:]
    answer_parts = [
        f"Based on professor-approved course knowledge — {_cite_entry(best.entry)}:",
        best.entry.answer_draft.strip(),
    ]
    if supporting:
        related = "; ".join(
            f"{_cite_entry(hit.entry)} ({hit.similarity:.0%} match)"
            for hit in supporting
        )
        answer_parts.append(f"Related approved material: {related}.")

    confidence = min(0.98, max(hit.similarity for hit in sources))
    return AgentAskResponse(
        answer="\n\n".join(answer_parts),
        student_hint=best.entry.student_hint,
        confidence=round(confidence, 4),
        matched_count=len(sources),
        sources=sources,
        used_approved_kb_only=approved_only,
        should_seek_help=False,
    )


def _approved_source_line(entry) -> str:
    filename = (getattr(entry, "source_filename", None) or "").strip()
    page = getattr(entry, "page_number", None)
    if filename and page is not None:
        return f"based on {filename}, p.{page} approved by the professor"
    return f"based on {_cite_entry(entry)} approved by the professor"


def _checked_answer(
    sources: list[KnowledgeSearchHit],
    *,
    approved_only: bool,
    answer: str,
    quote: str,
    chunk_id: int,
) -> AgentAskResponse:
    # The quote was matched to the chunk before this reply is built. The student
    # sees the answer and the approved page, not the copied passage.
    del quote
    chosen = next(hit for hit in sources if hit.entry.id == chunk_id)
    text = f"{answer.strip()}\n{_approved_source_line(chosen.entry)}"
    return AgentAskResponse(
        answer=text,
        student_hint=chosen.entry.student_hint,
        confidence=round(min(0.98, chosen.similarity), 4),
        matched_count=1,
        sources=[chosen],
        used_approved_kb_only=approved_only,
        should_seek_help=False,
    )


def _file_answer(answer: str, filename: str, approved_only: bool) -> AgentAskResponse:
    """Explain the student's file. The line says they uploaded it, not the professor."""
    safe = " ".join((filename or "your file").split())
    text = f"{answer.strip()}\nbased on {safe} that you uploaded"
    return AgentAskResponse(
        answer=text,
        student_hint=None,
        confidence=0.7,
        matched_count=1,
        sources=[],
        used_approved_kb_only=approved_only,
        should_seek_help=False,
    )


def _check_miss(sources: list[KnowledgeSearchHit], approved_only: bool) -> AgentAskResponse:
    return AgentAskResponse(
        answer=CHECK_MISS_ANSWER,
        student_hint=NO_MATCH_HINT,
        confidence=round(sources[0].similarity, 4) if sources else 0.0,
        matched_count=0,
        sources=[],
        used_approved_kb_only=approved_only,
        should_seek_help=True,
    )


def _chunks_for_check(sources: list[KnowledgeSearchHit]) -> list[dict[str, Any]]:
    chunks = []
    for hit in sources[:3]:
        entry = hit.entry
        chunks.append(
            {
                "chunk_id": entry.id,
                "file": entry.source_filename or "",
                "page": entry.page_number,
                "text": entry.answer_draft or "",
            }
        )
    return chunks


def _blank_record(outcome: str) -> dict[str, Any]:
    return {
        "called": False,
        "latency_ms": 0.0,
        "input_tokens": 0,
        "output_tokens": 0,
        "model": None,
        "outcome": outcome,
        "error_type": None,
    }


def answer_from_knowledge_base(
    db: Session,
    question: str,
    *,
    top_k: int = 3,
    course_id: int | None = None,
    approved_only: bool = True,
    course_scoped: bool = True,
    answer_checker: AnswerCheckClient | None = None,
    check_records: list[dict[str, Any]] | None = None,
    user_id: int | None = None,
    student_file: dict[str, str] | None = None,
) -> AgentAskResponse:
    """Study-agent answer. The pipeline lives in ``agent_policy``.

    Retrieval, the 0.42 cutoff, and the filters are unchanged. Flags stay off
    the HTTP request model. ``answer_checker`` injects a fake client in tests.
    ``user_id`` is only a rate-limit key. It is not logged and not cached.
    """
    from app.ai.agent_policy import run_study_agent

    return run_study_agent(
        db,
        question,
        top_k=top_k,
        course_id=course_id,
        approved_only=approved_only,
        course_scoped=course_scoped,
        answer_checker=answer_checker,
        check_records=check_records,
        user_id=user_id,
        student_file=student_file,
    )
