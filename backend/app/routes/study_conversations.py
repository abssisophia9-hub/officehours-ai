"""Saved Study Agent conversations. One list per student per course."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.study_conversation import StudyConversation, StudyMessage
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role

router = APIRouter(prefix="/study-conversations", tags=["study-conversations"])

NEW_CHAT = "New chat"
TITLE_LIMIT = 80


class ConversationCreate(BaseModel):
    course_id: int


class MessageCreate(BaseModel):
    role: str
    text: str = Field(min_length=1, max_length=8000)
    sources: list | None = None
    not_found: bool = False
    error: bool = False


def _student_course(db: Session, user: User, course_id: int):
    return require_course_role(db, user, course_id, roles={"student"})


def _owned(db: Session, user: User, conversation_id: int) -> StudyConversation:
    row = db.get(StudyConversation, conversation_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    _student_course(db, user, row.course_id)
    return row


def _summary(row: StudyConversation) -> dict:
    return {
        "id": row.id,
        "course_id": row.course_id,
        "title": row.title,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _message_out(row: StudyMessage) -> dict:
    sources = None
    if row.sources_json:
        try:
            parsed = json.loads(row.sources_json)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            sources = parsed
    return {
        "id": row.id,
        "role": row.role,
        "text": row.text,
        "sources": sources or [],
        "not_found": row.not_found,
        "error": row.is_error,
        "created_at": row.created_at,
    }


def _touch(row: StudyConversation) -> None:
    row.updated_at = datetime.now(timezone.utc)


@router.get("")
def list_conversations(
    course_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _student_course(db, user, course_id)
    rows = (
        db.query(StudyConversation)
        .filter(
            StudyConversation.user_id == user.id,
            StudyConversation.course_id == course_id,
        )
        .order_by(StudyConversation.updated_at.desc(), StudyConversation.id.desc())
        .all()
    )
    return [_summary(row) for row in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _student_course(db, user, payload.course_id)
    existing = (
        db.query(StudyConversation)
        .filter(
            StudyConversation.user_id == user.id,
            StudyConversation.course_id == payload.course_id,
            StudyConversation.title == NEW_CHAT,
        )
        .order_by(StudyConversation.id.desc())
        .all()
    )
    for row in existing:
        has_message = (
            db.query(StudyMessage.id)
            .filter(StudyMessage.conversation_id == row.id)
            .first()
        )
        if has_message is None:
            return _summary(row)
    now = datetime.now(timezone.utc)
    row = StudyConversation(
        user_id=user.id,
        course_id=payload.course_id,
        title=NEW_CHAT,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _summary(row)


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = _owned(db, user, conversation_id)
    messages = (
        db.query(StudyMessage)
        .filter(StudyMessage.conversation_id == row.id)
        .order_by(StudyMessage.id.asc())
        .all()
    )
    return {**_summary(row), "messages": [_message_out(message) for message in messages]}


@router.post("/{conversation_id}/messages", status_code=status.HTTP_201_CREATED)
def append_message(
    conversation_id: int,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.role not in {"student", "agent"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown message role.")
    row = _owned(db, user, conversation_id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message is empty.")
    if payload.role == "student" and row.title == NEW_CHAT:
        # The first line is the question. A later "Attached:" line stays in the message.
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), text)
        row.title = first_line if len(first_line) <= TITLE_LIMIT else f"{first_line[: TITLE_LIMIT - 1]}…"
    sources_json = None
    if payload.sources:
        sources_json = json.dumps(payload.sources)
    message = StudyMessage(
        conversation_id=row.id,
        role=payload.role,
        text=text,
        sources_json=sources_json,
        not_found=payload.not_found,
        is_error=payload.error,
    )
    _touch(row)
    db.add(message)
    db.commit()
    db.refresh(message)
    db.refresh(row)
    return {"message": _message_out(message), "title": row.title, "updated_at": row.updated_at}
