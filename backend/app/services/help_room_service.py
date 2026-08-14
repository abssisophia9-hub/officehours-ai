"""Stuck Room — course-scoped peer help threads with helpful-mark ranking."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.help_room import (
    HelpfulMark,
    HelpfulMarkOut,
    HelpPost,
    HelpPostOut,
    HelpRankOut,
    HelpReachOut,
    HelpReachOutOut,
    HelpReply,
    HelpReplyOut,
)

# Quiet ask already covers private/staff topics. Stuck Room is for course concepts.
_SENSITIVE_PATTERNS = (
    r"\b(suicid|kill myself|self[- ]harm|want to die)\b",
    r"\b(grading dispute|change my grade|unfair grade|grade appeal)\b",
    r"\b(plagiar|i cheated|academic integrity|honor code violation)\b",
    r"\b(disability accommodation|accommodation letter)\b",
    r"\b(retake (the )?(exam|midterm|final)|make[- ]up exam)\b",
    r"\b(depression|panic attack|mental health crisis)\b",
)
_SENSITIVE_RE = re.compile("|".join(_SENSITIVE_PATTERNS), re.IGNORECASE)


def normalize_chapter(value: str | None) -> str | None:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    if not cleaned:
        return None
    return cleaned[:80]


def _reject_sensitive(text: str) -> None:
    if _SENSITIVE_RE.search(text or ""):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "Stuck Room is for course concepts, not grades, integrity, or "
                "personal crises. Use Quiet ask so staff can follow up privately."
            ),
        )


def _author_display(db: Session, user_id: int, anonymous: bool, viewer: User) -> str:
    if anonymous and user_id != viewer.id:
        return "Classmate"
    author = db.get(User, user_id)
    return (
        (author.display_name if author else None)
        or (author.email if author else None)
        or "Classmate"
    )


def create_post(
    db: Session,
    *,
    course_id: int,
    author: User,
    title: str,
    body: str,
    chapter: str | None,
    anonymous: bool,
) -> HelpPost:
    title_clean = (title or "").strip()
    body_clean = (body or "").strip()
    if not title_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Say what you are stuck on (a short title).",
        )
    if not body_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Describe the stuck point — not the homework answer.",
        )
    _reject_sensitive(f"{title_clean}\n{body_clean}")
    post = HelpPost(
        course_id=course_id,
        author_user_id=author.id,
        title=title_clean[:200],
        body=body_clean[:4000],
        chapter=normalize_chapter(chapter),
        anonymous=bool(anonymous),
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_post(db: Session, post_id: int) -> HelpPost:
    post = db.get(HelpPost, post_id)
    if post is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stuck Room post not found.",
        )
    return post


def list_posts(db: Session, *, course_id: int, viewer: User) -> list[HelpPostOut]:
    rows = (
        db.query(HelpPost)
        .filter(HelpPost.course_id == course_id)
        .order_by(HelpPost.created_at.desc(), HelpPost.id.desc())
        .limit(80)
        .all()
    )
    return [serialize_post(db, post, viewer, include_replies=True) for post in rows]


def serialize_reply(db: Session, reply: HelpReply, viewer: User) -> HelpReplyOut:
    helpful_count = (
        db.query(HelpfulMark).filter(HelpfulMark.reply_id == reply.id).count()
    )
    marked = (
        db.query(HelpfulMark)
        .filter(
            HelpfulMark.reply_id == reply.id,
            HelpfulMark.rater_user_id == viewer.id,
        )
        .first()
        is not None
    )
    reached = (
        db.query(HelpReachOut)
        .filter(
            HelpReachOut.reply_id == reply.id,
            HelpReachOut.from_user_id == viewer.id,
        )
        .first()
        is not None
    )
    reachable = (
        (not reply.anonymous)
        and reply.author_user_id != viewer.id
        and marked
    )
    return HelpReplyOut(
        id=reply.id,
        post_id=reply.post_id,
        body=reply.body,
        anonymous=reply.anonymous,
        author_display=_author_display(db, reply.author_user_id, reply.anonymous, viewer),
        created_at=reply.created_at,
        is_mine=reply.author_user_id == viewer.id,
        helpful_count=helpful_count,
        marked_helpful_by_me=marked,
        reachable=reachable,
        reached_out_by_me=reached,
    )


def serialize_post(
    db: Session,
    post: HelpPost,
    viewer: User,
    *,
    include_replies: bool = False,
) -> HelpPostOut:
    replies_query = (
        db.query(HelpReply)
        .filter(HelpReply.post_id == post.id)
        .order_by(HelpReply.created_at.asc(), HelpReply.id.asc())
    )
    reply_count = replies_query.count()
    replies: list[HelpReplyOut] = []
    if include_replies:
        replies = [serialize_reply(db, row, viewer) for row in replies_query.limit(100).all()]
    similar = 0
    if post.chapter:
        similar = (
            db.query(HelpPost)
            .filter(
                HelpPost.course_id == post.course_id,
                HelpPost.chapter == post.chapter,
                HelpPost.id != post.id,
            )
            .count()
        )
    return HelpPostOut(
        id=post.id,
        course_id=post.course_id,
        title=post.title,
        body=post.body,
        chapter=post.chapter,
        anonymous=post.anonymous,
        author_display=_author_display(db, post.author_user_id, post.anonymous, viewer),
        created_at=post.created_at,
        is_mine=post.author_user_id == viewer.id,
        reply_count=reply_count,
        similar_chapter_count=similar,
        replies=replies,
    )


def add_reply(
    db: Session,
    *,
    post: HelpPost,
    author: User,
    body: str,
    anonymous: bool,
) -> HelpReply:
    text = (body or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Share a perspective or approach — empty replies are not allowed.",
        )
    _reject_sensitive(text)
    reply = HelpReply(
        post_id=post.id,
        author_user_id=author.id,
        body=text[:4000],
        anonymous=bool(anonymous),
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


def toggle_helpful(db: Session, *, reply: HelpReply, user: User) -> HelpfulMarkOut:
    if reply.author_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot mark your own reply as helpful.",
        )
    existing = (
        db.query(HelpfulMark)
        .filter(
            HelpfulMark.reply_id == reply.id,
            HelpfulMark.rater_user_id == user.id,
        )
        .one_or_none()
    )
    if existing:
        db.delete(existing)
        db.commit()
        marked = False
    else:
        db.add(HelpfulMark(reply_id=reply.id, rater_user_id=user.id))
        db.commit()
        marked = True
    count = db.query(HelpfulMark).filter(HelpfulMark.reply_id == reply.id).count()
    reached = (
        db.query(HelpReachOut)
        .filter(
            HelpReachOut.reply_id == reply.id,
            HelpReachOut.from_user_id == user.id,
        )
        .first()
        is not None
    )
    return HelpfulMarkOut(
        reply_id=reply.id,
        marked=marked,
        helpful_count=count,
        reachable=(not reply.anonymous) and marked,
        reached_out_by_me=reached,
    )


def get_reply(db: Session, reply_id: int) -> HelpReply:
    reply = db.get(HelpReply, reply_id)
    if reply is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reply not found.",
        )
    return reply


def list_ranks(db: Session, *, course_id: int, limit: int = 15) -> list[HelpRankOut]:
    """Points = unique classmates who marked your replies helpful in this course."""
    rows = (
        db.query(
            HelpReply.author_user_id,
            func.count(HelpfulMark.id).label("points"),
            func.count(func.distinct(HelpReply.id)).label("replies"),
        )
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .join(HelpfulMark, HelpfulMark.reply_id == HelpReply.id)
        .filter(HelpPost.course_id == course_id)
        .group_by(HelpReply.author_user_id)
        .order_by(func.count(HelpfulMark.id).desc(), HelpReply.author_user_id.asc())
        .limit(limit)
        .all()
    )
    out: list[HelpRankOut] = []
    for index, row in enumerate(rows, start=1):
        user = db.get(User, row.author_user_id)
        out.append(
            HelpRankOut(
                rank=index,
                user_id=row.author_user_id,
                display_name=(
                    (user.display_name if user else None)
                    or (user.email if user else None)
                    or "Classmate"
                ),
                helpful_points=int(row.points),
                reply_count=int(row.replies),
            )
        )
    return out


def create_reach_out(
    db: Session,
    *,
    reply: HelpReply,
    post: HelpPost,
    user: User,
    note: str,
) -> HelpReachOut:
    if reply.author_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot reach out to your own reply.",
        )
    if reply.anonymous:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This classmate posted quietly. You can still mark the aha, "
                "but they stay unnamed."
            ),
        )
    marked = (
        db.query(HelpfulMark)
        .filter(
            HelpfulMark.reply_id == reply.id,
            HelpfulMark.rater_user_id == user.id,
        )
        .first()
    )
    if marked is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mark “this unlocked it” first — reach-out is for a real aha, not cold DMs.",
        )
    existing = (
        db.query(HelpReachOut)
        .filter(
            HelpReachOut.reply_id == reply.id,
            HelpReachOut.from_user_id == user.id,
        )
        .one_or_none()
    )
    text = (note or "").strip()[:500]
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add a short thanks / compare-notes note.",
        )
    if existing:
        existing.note = text
        db.commit()
        db.refresh(existing)
        return existing
    row = HelpReachOut(
        course_id=post.course_id,
        reply_id=reply.id,
        from_user_id=user.id,
        to_user_id=reply.author_user_id,
        note=text,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def serialize_reach_out(
    db: Session, row: HelpReachOut, viewer: User
) -> HelpReachOutOut:
    post_title = "Stuck Room"
    reply = db.get(HelpReply, row.reply_id)
    if reply is not None:
        post = db.get(HelpPost, reply.post_id)
        if post is not None:
            post_title = post.title
    from_user = db.get(User, row.from_user_id)
    to_user = db.get(User, row.to_user_id)
    return HelpReachOutOut(
        id=row.id,
        course_id=row.course_id,
        reply_id=row.reply_id,
        post_title=post_title,
        note=row.note,
        from_display=(
            (from_user.display_name if from_user else None)
            or (from_user.email if from_user else None)
            or "Classmate"
        ),
        to_display=(
            (to_user.display_name if to_user else None)
            or (to_user.email if to_user else None)
            or "Classmate"
        ),
        is_incoming=row.to_user_id == viewer.id,
        created_at=row.created_at,
    )


def list_reach_outs(
    db: Session, *, course_id: int, viewer: User
) -> list[HelpReachOutOut]:
    rows = (
        db.query(HelpReachOut)
        .filter(
            HelpReachOut.course_id == course_id,
            or_(
                HelpReachOut.to_user_id == viewer.id,
                HelpReachOut.from_user_id == viewer.id,
            ),
        )
        .order_by(HelpReachOut.created_at.desc(), HelpReachOut.id.desc())
        .limit(40)
        .all()
    )
    return [serialize_reach_out(db, row, viewer) for row in rows]


def delete_own_post(db: Session, *, post: HelpPost, user: User) -> None:
    if post.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own Stuck Room post.",
        )
    reply_ids = [
        row.id
        for row in db.query(HelpReply.id).filter(HelpReply.post_id == post.id).all()
    ]
    if reply_ids:
        db.query(HelpReachOut).filter(HelpReachOut.reply_id.in_(reply_ids)).delete(
            synchronize_session=False
        )
        db.query(HelpfulMark).filter(HelpfulMark.reply_id.in_(reply_ids)).delete(
            synchronize_session=False
        )
    db.query(HelpReply).filter(HelpReply.post_id == post.id).delete()
    db.delete(post)
    db.commit()
