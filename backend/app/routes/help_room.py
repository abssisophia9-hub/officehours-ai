"""Stuck Room API — AUI classmate rooms (not Quiet ask, not classmate files)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.help_room import (
    HelpCommunityOut,
    HelpFileOut,
    HelpInterestCreate,
    HelpInterestOut,
    HelpfulMarkOut,
    HelpPostCreate,
    HelpPostOut,
    HelpPostVoteOut,
    HelpProfileOut,
    HelpRankOut,
    HelpReachOutCreate,
    HelpReachOutOut,
    HelpReplyCreate,
    HelpReplyOut,
    HelpVoteRequest,
)
from app.routes.auth import get_current_user
from app.services.access_control import get_membership, require_course_role
from app.services.help_room_service import (
    accept_reply,
    add_reply,
    attach_file,
    create_post,
    create_reach_out,
    delete_own_post,
    express_interest,
    file_path,
    get_community,
    get_file_row,
    get_post,
    get_profile,
    get_reply,
    list_posts,
    list_ranks,
    list_reach_outs,
    serialize_post,
    serialize_reach_out,
    serialize_reply,
    set_vote,
    toggle_follow,
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
    room_type: str | None = Query(default=None),
    chapter: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Students see the social room. Staff use review insights instead."""
    _require_student(db, user, course_id)
    return list_posts(
        db,
        course_id=course_id,
        viewer=user,
        sort=sort,
        flair=flair,
        room_type=room_type,
        chapter=chapter,
        status_filter=status_filter,
    )


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
        room_type=payload.room_type,
        tags=payload.tags,
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
    """Hilbert-weighted leaderboard. Course members may view; posting stays student-only."""
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


@router.get("/files/{file_id}")
def download_room_file(
    file_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = get_file_row(db, file_id)
    post = get_post(db, row.post_id)
    _require_student(db, user, post.course_id)
    path = file_path(row, post.course_id)
    return FileResponse(
        path,
        filename=row.original_filename,
        media_type=row.content_type or "application/octet-stream",
    )


@router.get("/profile/{user_id}", response_model=HelpProfileOut)
def profile(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_student(db, user, course_id)
    return get_profile(db, course_id=course_id, user_id=user_id, viewer=user)


@router.post("/profile/{user_id}/follow", response_model=HelpProfileOut)
def follow_classmate(
    user_id: int,
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_student(db, user, course_id)
    return toggle_follow(db, course_id=course_id, followee_id=user_id, viewer=user)


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


@router.post("/{post_id}/vote", response_model=HelpPostVoteOut)
def vote_room(
    post_id: int,
    payload: HelpVoteRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    return set_vote(db, post=post, user=user, value=payload.value)


@router.post("/{post_id}/interest", response_model=HelpInterestOut, status_code=status.HTTP_201_CREATED)
def interest(
    post_id: int,
    payload: HelpInterestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    return express_interest(db, post=post, user=user, note=payload.note)


@router.post("/{post_id}/files", response_model=HelpFileOut, status_code=status.HTTP_201_CREATED)
async def upload_room_file(
    post_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    post = get_post(db, post_id)
    _require_student(db, user, post.course_id)
    data = await file.read()
    return attach_file(
        db,
        post=post,
        user=user,
        filename=file.filename or "file.bin",
        content_type=file.content_type,
        data=data,
    )


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


@router.post("/replies/{reply_id}/accept", response_model=HelpPostOut)
def accept_solution(
    reply_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    reply = get_reply(db, reply_id)
    post = get_post(db, reply.post_id)
    _require_student(db, user, post.course_id)
    return accept_reply(db, reply=reply, post=post, user=user)


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
