"""Stuck Room API — student peer community (not Quiet ask, not classmate files)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.help_room import (
    HelpCommunityOut,
    HelpfulMarkOut,
    HelpPostCreate,
    HelpPostOut,
    HelpPostVoteOut,
    HelpRankOut,
    HelpReachOutCreate,
    HelpReachOutOut,
    HelpReplyCreate,
    HelpReplyOut,
)
from app.routes.auth import get_current_user
from app.services.access_control import get_membership, require_course_role
from app.services.help_room_service import (
    add_reply,
    create_post,
    create_reach_out,
    delete_own_post,
    get_community,
    get_post,
    get_reply,
    list_posts,
    list_ranks,
    list_reach_outs,
    serialize_post,
    serialize_reach_out,
    serialize_reply,
    toggle_helpful,
    toggle_same_here,
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
    sort: str = Query(default="hot"),
    flair: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Students see the social room. Staff use review insights instead."""
    _require_student(db, user, course_id)
    return list_posts(db, course_id=course_id, viewer=user, sort=sort, flair=flair)


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
        flair=payload.flair,
    )
    return serialize_post(db, post, user, include_replies=True)


@router.get("/community/", response_model=HelpCommunityOut)
def community(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_student(db, user, course_id)
    return get_community(db, course_id=course_id)


@router.get("/ranks/", response_model=list[HelpRankOut])
def ranks(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Helpful-mark leaderboard. Course members may view; posting stays student-only."""
    _require_member(db, user, course_id)
    return list_ranks(db, course_id=course_id)


@router.get("/reach-outs/", response_model=list[HelpReachOutOut])
def reach_outs(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_student(db, user, course_id)
    return list_reach_outs(db, course_id=course_id, viewer=user)


@router.get("/{post_id}", response_model=HelpPostOut)
def thread(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    return serialize_post(db, post, user, include_replies=True)


@router.post("/{post_id}/same-here", response_model=HelpPostVoteOut)
def same_here(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    return toggle_same_here(db, post=post, user=user)


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
        parent_reply_id=payload.parent_reply_id,
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


@router.post(
    "/replies/{reply_id}/reach-out",
    response_model=HelpReachOutOut,
    status_code=status.HTTP_201_CREATED,
)
def reach_out(
    reply_id: int,
    payload: HelpReachOutCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reply = get_reply(db, reply_id)
    post = get_post(db, reply.post_id)
    _require_student(db, user, post.course_id)
    row = create_reach_out(
        db,
        reply=reply,
        post=post,
        user=user,
        note=payload.note,
    )
    return serialize_reach_out(db, row, user)


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
