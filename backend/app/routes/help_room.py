"""Stuck Room API — student peer-help threads (not Quiet ask, not classmate files)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.help_room import (
    HelpfulMarkOut,
    HelpPostCreate,
    HelpPostOut,
    HelpRankOut,
    HelpReplyCreate,
    HelpReplyOut,
)
from app.routes.auth import get_current_user
from app.services.access_control import get_membership, require_course_role
from app.services.help_room_service import (
    add_reply,
    create_post,
    delete_own_post,
    get_post,
    get_reply,
    list_posts,
    list_ranks,
    serialize_post,
    serialize_reply,
    toggle_helpful,
)

router = APIRouter(prefix="/help-room", tags=["help-room"])


def _require_student(db: Session, user: User, course_id: int):
    return require_course_role(db, user, course_id, roles={"student"})


def _require_member(db: Session, user: User, course_id: int):
    return require_course_role(
        db,
        user,
        course_id,
        roles={"student", "ta", "professor"},
    )


@router.get("/", response_model=list[HelpPostOut])
def feed(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Students see the social room. Staff use review insights instead."""
    _require_student(db, user, course_id)
    return list_posts(db, course_id=course_id, viewer=user)


@router.post("/", response_model=HelpPostOut, status_code=status.HTTP_201_CREATED)
def create_stuck_post(
    payload: HelpPostCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_student(db, user, payload.course_id)
    post = create_post(
        db,
        course_id=payload.course_id,
        author=user,
        title=payload.title,
        body=payload.body,
        chapter=payload.chapter,
        anonymous=payload.anonymous,
    )
    return serialize_post(db, post, user, include_replies=True)


@router.get("/ranks/", response_model=list[HelpRankOut])
def ranks(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Helpful-mark leaderboard. Course members may view; posting stays student-only."""
    _require_member(db, user, course_id)
    return list_ranks(db, course_id=course_id)


@router.post(
    "/{post_id}/replies",
    response_model=HelpReplyOut,
    status_code=status.HTTP_201_CREATED,
)
def create_reply(
    post_id: int,
    payload: HelpReplyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    reply = add_reply(
        db,
        post=post,
        author=user,
        body=payload.body,
        anonymous=payload.anonymous,
    )
    return serialize_reply(db, reply, user)


@router.post("/replies/{reply_id}/helpful", response_model=HelpfulMarkOut)
def mark_helpful(
    reply_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reply = get_reply(db, reply_id)
    post = get_post(db, reply.post_id)
    _require_student(db, user, post.course_id)
    return toggle_helpful(db, reply=reply, user=user)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    get_membership(db, user, post.course_id)
    delete_own_post(db, post=post, user=user)
    return None
