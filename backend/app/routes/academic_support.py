"""Direct frontend interface for persisted academic-support chat turns."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.agent_metrics import KbAskEvent
from app.models.auth import User
from app.models.study_conversation import StudyConversation, StudyMessage
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role
from app.services.kb_agent_service import answer_from_knowledge_base

router = APIRouter(prefix="/academic-support", tags=["academic-support"])

NOT_FOUND = "No professor-approved material answers this."
TITLE_LIMIT = 80


class ChatTurnCreate(BaseModel):
    question: str = Field(min_length=1, max_length=8000)


def _owned_conversation(
    db: Session, user: User, conversation_id: int
) -> StudyConversation:
    conversation = db.get(StudyConversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )
    require_course_role(
        db,
        user,
        conversation.course_id,
        roles={"student"},
    )
    return conversation


def _history(db: Session, conversation_id: int) -> list[dict[str, str]]:
    rows = (
        db.query(StudyMessage)
        .filter(StudyMessage.conversation_id == conversation_id)
        .order_by(StudyMessage.id.desc())
        .limit(20)
        .all()
    )
    return [
        {"role": row.role, "text": row.text}
        for row in reversed(rows)
    ]


@router.post(
    "/conversations/{conversation_id}/turns",
    status_code=status.HTTP_201_CREATED,
)
def create_chat_turn(
    conversation_id: int,
    payload: ChatTurnCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Run one bounded Study Agent turn and persist both messages atomically."""
    conversation = _owned_conversation(db, user, conversation_id)
    question = payload.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message is empty.",
        )

    history = _history(db, conversation.id)
    response = answer_from_knowledge_base(
        db,
        question,
        course_id=conversation.course_id,
        user_id=user.id,
        session_history=history,
    )
    not_found = bool(response.should_seek_help or response.matched_count == 0)
    sources = [] if not_found else [
        source.model_dump(mode="json") for source in response.sources
    ]
    now = datetime.now(timezone.utc)
    if conversation.title == "New chat":
        conversation.title = (
            question
            if len(question) <= TITLE_LIMIT
            else f"{question[: TITLE_LIMIT - 1]}…"
        )
    conversation.updated_at = now

    student_message = StudyMessage(
        conversation_id=conversation.id,
        role="student",
        text=question,
        created_at=now,
    )
    agent_message = StudyMessage(
        conversation_id=conversation.id,
        role="agent",
        text=NOT_FOUND if not_found else response.answer,
        sources_json=json.dumps(sources) if sources else None,
        not_found=not_found,
        is_error=False,
        created_at=now,
    )
    event = KbAskEvent(
        course_id=conversation.course_id,
        question=question[:4000],
        hit=not not_found,
        should_seek_help=bool(response.should_seek_help),
        confidence=float(response.confidence or 0.0),
        matched_count=int(response.matched_count or 0),
    )
    db.add_all([student_message, agent_message, event])
    db.commit()
    db.refresh(agent_message)
    db.refresh(conversation)
    return {
        "message": {
            "id": agent_message.id,
            "role": agent_message.role,
            "text": agent_message.text,
            "sources": sources,
            "not_found": agent_message.not_found,
            "error": agent_message.is_error,
            "created_at": agent_message.created_at,
        },
        "title": conversation.title,
        "updated_at": conversation.updated_at,
    }
