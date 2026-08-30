"""Stuck Room — course-scoped peer community with ranks, not likes."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.models.help_room import (
    FLAIR_TO_ROOM_TYPE,
    POST_FLAIRS,
    ROOM_TYPE_TO_FLAIR,
    ROOM_TYPES,
    HelpChapterOut,
    HelpCommunityOut,
    HelpFileOut,
    HelpFollow,
    HelpfulMark,
    HelpfulMarkOut,
    HelpInterest,
    HelpInterestOut,
    HelpPost,
    HelpPostFile,
    HelpPostOut,
    HelpPostVote,
    HelpPostVoteOut,
    HelpProfileOut,
    HelpRankOut,
    HelpReachOut,
    HelpReachOutOut,
    HelpReply,
    HelpReplyOut,
)
from app.services.canvas_service import list_canvas_module_names
from app.services.room_chapters import (
    chapters_for_course,
    merge_course_chapters,
    resolve_chapter_source,
)
from app.services.room_reputation import compute_reputation

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
_SORTS = ("hot", "new", "top", "rising")
_FILE_EXTENSIONS = {
    ".csv",
    ".pdf",
    ".m",
    ".step",
    ".stp",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".zip",
    ".txt",
    ".md",
    ".docx",
}
_MAX_FILE_BYTES = 10_000_000
_STORAGE_ROOT = Path(__file__).resolve().parents[2] / "data" / "help_room_files"


def normalize_chapter(value: str | None) -> str | None:
    cleaned = re.sub(r"\s+", " ", (value or "").strip())
    if not cleaned:
        return None
    return cleaned[:80]


def normalize_flair(value: str | None) -> str:
    key = (value or "stuck").strip().lower().replace(" ", "_")
    aliases = {
        "im_stuck": "stuck",
        "i'm_stuck": "stuck",
        "stress": "vent",
        "peer": "find_peer",
        "find-peer": "find_peer",
        "problem": "stuck",
        "discussion": "vent",
        "article": "aha",
    }
    key = aliases.get(key, key)
    if key not in POST_FLAIRS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pick a flair: stuck, aha, vent, or find_peer.",
        )
    return key


def normalize_room_type(room_type: str | None, flair: str | None = None) -> str:
    raw = (room_type or "").strip().lower()
    if not raw and flair:
        raw = FLAIR_TO_ROOM_TYPE.get(normalize_flair(flair), "problem")
    if raw in FLAIR_TO_ROOM_TYPE:
        raw = FLAIR_TO_ROOM_TYPE[raw]
    if raw not in ROOM_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Room type must be Problem, Discussion, or Article.",
        )
    return raw


def normalize_tags(tags: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in tags or []:
        token = re.sub(r"[^A-Za-z0-9_]+", "", (item or "").strip().lstrip("#"))
        if not token:
            continue
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(token[:40])
        if len(out) >= 8:
            break
    return out


def _tags_from_post(post: HelpPost) -> list[str]:
    raw = getattr(post, "tags_json", None) or ""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item) for item in parsed][:8]


def _handle_for(user: User | None) -> str:
    if user is None:
        return "classmate"
    if user.handle:
        return user.handle.lstrip("@")
    local = (user.email or "classmate").split("@", 1)[0]
    return re.sub(r"[^a-z0-9.]+", "", local.lower()) or "classmate"


def community_name(code: str | None) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "", code or "course") or "course"
    return f"r/{slug}"


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
    # Rooms are named on purpose: helpers must be visible on the leaderboard.
    # Quiet ask is the anonymous path to staff.
    _ = (anonymous, viewer)
    author = db.get(User, user_id)
    return (
        (author.display_name if author else None)
        or (author.email if author else None)
        or "Classmate"
    )


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _course_karma(db: Session, user_id: int, course_id: int) -> int:
    return int(
        db.query(func.count(HelpfulMark.id))
        .join(HelpReply, HelpReply.id == HelpfulMark.reply_id)
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .filter(
            HelpPost.course_id == course_id,
            HelpReply.author_user_id == user_id,
        )
        .scalar()
        or 0
    )


def _vote_stats(db: Session, post_id: int, viewer_id: int) -> tuple[int, int, int, int]:
    rows = db.query(HelpPostVote).filter(HelpPostVote.post_id == post_id).all()
    up = 0
    down = 0
    mine = 0
    for row in rows:
        value = int(getattr(row, "value", 1) or 1)
        if value >= 1:
            up += 1
        elif value <= -1:
            down += 1
        if row.user_id == viewer_id:
            mine = 1 if value >= 1 else (-1 if value <= -1 else 0)
    return up - down, up, down, mine


def _same_here_count(db: Session, post_id: int) -> int:
    return (
        db.query(HelpPostVote)
        .filter(HelpPostVote.post_id == post_id, HelpPostVote.value >= 1)
        .count()
    )


def _same_here_by_me(db: Session, post_id: int, viewer_id: int) -> bool:
    row = (
        db.query(HelpPostVote)
        .filter(HelpPostVote.post_id == post_id, HelpPostVote.user_id == viewer_id)
        .first()
    )
    return row is not None and int(getattr(row, "value", 1) or 1) >= 1


def _unlocked_count(db: Session, post_id: int) -> int:
    return (
        db.query(func.count(HelpfulMark.id))
        .join(HelpReply, HelpReply.id == HelpfulMark.reply_id)
        .filter(HelpReply.post_id == post_id)
        .scalar()
        or 0
    )


def _hot_score(
    post: HelpPost, same_here: int, reply_count: int, unlocked: int
) -> float:
    age_hours = max(
        0.25,
        (datetime.now(timezone.utc) - _aware(post.created_at)).total_seconds() / 3600,
    )
    gravity = same_here + reply_count + (3 * unlocked)
    return gravity / ((age_hours + 2) ** 1.4)


def create_post(
    db: Session,
    *,
    course_id: int,
    author: User,
    title: str,
    body: str,
    chapter: str | None,
    anonymous: bool,
    flair: str | None = "stuck",
    room_type: str | None = None,
    tags: list[str] | None = None,
) -> HelpPost:
    # Rooms stay named so helpers can appear on the leaderboard.
    _ = anonymous
    title_clean = (title or "").strip()
    body_clean = (body or "").strip()
    if not title_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Give the room a title.",
        )
    if not body_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Describe the room — markdown is fine, homework answers are not.",
        )
    _reject_sensitive(f"{title_clean}\n{body_clean}")
    resolved_type = normalize_room_type(room_type, flair)
    resolved_flair = ROOM_TYPE_TO_FLAIR[resolved_type]
    if flair:
        resolved_flair = normalize_flair(flair)
        resolved_type = FLAIR_TO_ROOM_TYPE.get(resolved_flair, resolved_type)
    tag_list = normalize_tags(tags)
    post = HelpPost(
        course_id=course_id,
        author_user_id=author.id,
        title=title_clean[:200],
        body=body_clean[:8000],
        chapter=normalize_chapter(chapter),
        flair=resolved_flair,
        room_type=resolved_type,
        status="open",
        tags_json=json.dumps(tag_list) if tag_list else None,
        anonymous=False,
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


def get_community(db: Session, *, course_id: int) -> HelpCommunityOut:
    course = db.get(Course, course_id)
    classmate_count = (
        db.query(func.count(CourseMembership.id))
        .filter(
            CourseMembership.course_id == course_id,
            CourseMembership.role == "student",
        )
        .scalar()
        or 0
    )
    post_count = db.query(HelpPost).filter(HelpPost.course_id == course_id).count()
    comment_count = (
        db.query(func.count(HelpReply.id))
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .filter(HelpPost.course_id == course_id)
        .scalar()
        or 0
    )
    helper_count = len(list_ranks(db, course_id=course_id, limit=50))
    open_count = (
        db.query(HelpPost)
        .filter(HelpPost.course_id == course_id, HelpPost.status == "open")
        .count()
    )
    solved_count = (
        db.query(HelpPost)
        .filter(HelpPost.course_id == course_id, HelpPost.status == "solved")
        .count()
    )
    code = course.code if course else None
    syllabus = chapters_for_course(code)
    canvas_modules = list_canvas_module_names(course)
    catalog = merge_course_chapters(syllabus, canvas_modules)
    catalog_labels = {label for label, _source in catalog}
    chapter_rows = (
        db.query(HelpPost.chapter, func.count(HelpPost.id))
        .filter(HelpPost.course_id == course_id, HelpPost.chapter.isnot(None))
        .group_by(HelpPost.chapter)
        .all()
    )
    counts = {label: int(n) for label, n in chapter_rows if label}
    chapter_out = [
        HelpChapterOut(label=label, post_count=counts.get(label, 0), source=source)
        for label, source in catalog
    ]
    for label, n in counts.items():
        if label not in catalog_labels:
            chapter_out.append(HelpChapterOut(label=label, post_count=n, source="posted"))
    resolution = round(solved_count / post_count, 3) if post_count else 0.0
    return HelpCommunityOut(
        course_id=course_id,
        course_code=code,
        course_title=course.title if course else None,
        community_name=community_name(code),
        classmate_count=int(classmate_count),
        post_count=int(post_count),
        comment_count=int(comment_count),
        helper_count=int(helper_count),
        open_count=int(open_count),
        solved_count=int(solved_count),
        resolution_rate=resolution,
        chapter_source=resolve_chapter_source(
            syllabus=syllabus,
            canvas_modules=canvas_modules,
            posted=bool(counts),
        ),
        chapters=chapter_out,
    )


def list_posts(
    db: Session,
    *,
    course_id: int,
    viewer: User,
    sort: str = "hot",
    flair: str | None = None,
    room_type: str | None = None,
    chapter: str | None = None,
    status_filter: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[HelpPostOut] | dict:
    key = (sort or "hot").strip().lower()
    if key not in _SORTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Sort must be hot, new, top, or rising.",
        )
    query = db.query(HelpPost).filter(HelpPost.course_id == course_id)
    if flair:
        query = query.filter(HelpPost.flair == normalize_flair(flair))
    if room_type:
        query = query.filter(HelpPost.room_type == normalize_room_type(room_type))
    if chapter:
        query = query.filter(HelpPost.chapter == normalize_chapter(chapter))
    if status_filter in ("open", "solved"):
        query = query.filter(HelpPost.status == status_filter)
    fetch_cap = 500 if limit is None else max(offset + (limit or 0), 80)
    rows = query.order_by(HelpPost.created_at.desc(), HelpPost.id.desc()).limit(fetch_cap).all()
    serialized = [
        serialize_post(db, post, viewer, include_replies=False) for post in rows
    ]
    if key == "new":
        ordered = serialized
    elif key == "top":
        ordered = sorted(
            serialized,
            key=lambda item: (
                item.score,
                item.unlocked_count,
                item.reply_count,
                item.id,
            ),
            reverse=True,
        )
    elif key == "rising":
        cutoff = datetime.now(timezone.utc).timestamp() - (36 * 3600)
        recent = [
            item
            for post, item in zip(rows, serialized)
            if _aware(post.created_at).timestamp() >= cutoff
        ]
        pool = recent or serialized
        ordered = sorted(
            pool,
            key=lambda item: (item.same_here_count + item.reply_count, item.id),
            reverse=True,
        )
    else:
        ordered = sorted(
            serialized,
            key=lambda item: (
                _hot_score(
                    next(post for post in rows if post.id == item.id),
                    item.same_here_count,
                    item.reply_count,
                    item.unlocked_count,
                ),
                item.id,
            ),
            reverse=True,
        )
    from app.services.pagination import clamp_page, page_or_list

    limit, offset = clamp_page(limit, offset)
    return page_or_list(ordered, limit=limit, offset=offset)


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
    reachable = reply.author_user_id != viewer.id and marked
    show_karma = True
    post = db.get(HelpPost, reply.post_id)
    karma = (
        _course_karma(db, reply.author_user_id, post.course_id)
        if show_karma and post is not None
        else 0
    )
    return HelpReplyOut(
        id=reply.id,
        post_id=reply.post_id,
        parent_reply_id=reply.parent_reply_id,
        body=reply.body,
        anonymous=False,
        author_display=_author_display(
            db, reply.author_user_id, reply.anonymous, viewer
        ),
        author_user_id=reply.author_user_id,
        author_karma=karma,
        created_at=reply.created_at,
        is_mine=reply.author_user_id == viewer.id,
        helpful_count=helpful_count,
        marked_helpful_by_me=marked,
        accepted=bool(getattr(reply, "accepted", False)),
        reachable=reachable,
        reached_out_by_me=reached,
        children=[],
    )


def _reply_tree(
    db: Session, replies: list[HelpReply], viewer: User
) -> list[HelpReplyOut]:
    serialized = {row.id: serialize_reply(db, row, viewer) for row in replies}
    roots: list[HelpReplyOut] = []
    for row in replies:
        node = serialized[row.id]
        parent_id = row.parent_reply_id
        if parent_id and parent_id in serialized:
            serialized[parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


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
    all_replies = replies_query.limit(200).all()
    reply_count = len(all_replies)
    replies: list[HelpReplyOut] = []
    if include_replies:
        replies = _reply_tree(db, all_replies, viewer)
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
    show_karma = True
    score, up_count, down_count, my_vote = _vote_stats(db, post.id, viewer.id)
    author = db.get(User, post.author_user_id)
    hide_author = False
    interest_count = db.query(HelpInterest).filter(HelpInterest.post_id == post.id).count()
    interested = (
        db.query(HelpInterest)
        .filter(HelpInterest.post_id == post.id, HelpInterest.from_user_id == viewer.id)
        .first()
        is not None
    )
    files = [
        HelpFileOut(
            id=row.id,
            original_filename=row.original_filename,
            byte_size=row.byte_size,
            content_type=row.content_type,
            download_url=f"/help-room/files/{row.id}",
        )
        for row in db.query(HelpPostFile)
        .filter(HelpPostFile.post_id == post.id)
        .order_by(HelpPostFile.id.asc())
        .all()
    ]
    room_type = getattr(post, "room_type", None) or FLAIR_TO_ROOM_TYPE.get(
        post.flair or "stuck", "problem"
    )
    return HelpPostOut(
        id=post.id,
        course_id=post.course_id,
        title=post.title,
        body=post.body,
        chapter=post.chapter,
        flair=post.flair or "stuck",
        room_type=room_type,
        status=getattr(post, "status", None) or "open",
        tags=_tags_from_post(post),
        anonymous=False,
        author_display=_author_display(
            db, post.author_user_id, post.anonymous, viewer
        ),
        author_handle=None if hide_author else _handle_for(author),
        author_user_id=None if hide_author else post.author_user_id,
        author_karma=(
            _course_karma(db, post.author_user_id, post.course_id) if show_karma else 0
        ),
        created_at=post.created_at,
        is_mine=post.author_user_id == viewer.id,
        reply_count=reply_count,
        same_here_count=up_count,
        same_here_by_me=my_vote == 1,
        score=score,
        up_count=up_count,
        down_count=down_count,
        my_vote=my_vote,
        unlocked_count=int(_unlocked_count(db, post.id)),
        similar_chapter_count=similar,
        interest_count=int(interest_count),
        interested_by_me=interested,
        files=files,
        replies=replies,
    )


def add_reply(
    db: Session,
    *,
    post: HelpPost,
    author: User,
    body: str,
    anonymous: bool,
    parent_reply_id: int | None = None,
) -> HelpReply:
    _ = anonymous
    text = (body or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Share a perspective or approach — empty replies are not allowed.",
        )
    _reject_sensitive(text)
    parent_id = parent_reply_id
    if parent_id is not None:
        parent = db.get(HelpReply, parent_id)
        if parent is None or parent.post_id != post.id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="That comment is not on this thread.",
            )
    reply = HelpReply(
        post_id=post.id,
        parent_reply_id=parent_id,
        author_user_id=author.id,
        body=text[:4000],
        anonymous=False,
    )
    db.add(reply)
    db.commit()
    db.refresh(reply)
    return reply


def set_vote(db: Session, *, post: HelpPost, user: User, value: int) -> HelpPostVoteOut:
    if post.author_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot vote on your own room.",
        )
    if value not in (-1, 0, 1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Vote must be up, down, or clear.",
        )
    existing = (
        db.query(HelpPostVote)
        .filter(HelpPostVote.post_id == post.id, HelpPostVote.user_id == user.id)
        .one_or_none()
    )
    if value == 0 or (existing is not None and int(getattr(existing, "value", 1) or 1) == value):
        if existing:
            db.delete(existing)
            db.commit()
        marked = False
        mine = 0
    elif existing:
        existing.value = value
        db.commit()
        marked = value == 1
        mine = value
    else:
        db.add(HelpPostVote(post_id=post.id, user_id=user.id, value=value))
        db.commit()
        marked = value == 1
        mine = value
    score, up_count, down_count, _mine = _vote_stats(db, post.id, user.id)
    return HelpPostVoteOut(
        post_id=post.id,
        marked=marked,
        same_here_count=up_count,
        score=score,
        up_count=up_count,
        down_count=down_count,
        my_vote=mine if value != 0 else 0,
    )


def toggle_same_here(db: Session, *, post: HelpPost, user: User) -> HelpPostVoteOut:
    existing = (
        db.query(HelpPostVote)
        .filter(HelpPostVote.post_id == post.id, HelpPostVote.user_id == user.id)
        .one_or_none()
    )
    current = int(getattr(existing, "value", 0) or 0) if existing else 0
    return set_vote(db, post=post, user=user, value=0 if current == 1 else 1)


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
        reachable=marked,
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


def _user_activity(db: Session, *, course_id: int, user_id: int) -> dict[str, int]:
    rooms = db.query(HelpPost).filter(
        HelpPost.course_id == course_id, HelpPost.author_user_id == user_id
    ).count()
    solutions = (
        db.query(func.count(HelpReply.id))
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .filter(HelpPost.course_id == course_id, HelpReply.author_user_id == user_id)
        .scalar()
        or 0
    )
    accepted = (
        db.query(func.count(HelpReply.id))
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .filter(
            HelpPost.course_id == course_id,
            HelpReply.author_user_id == user_id,
            HelpReply.accepted.is_(True),
        )
        .scalar()
        or 0
    )
    helpful = _course_karma(db, user_id, course_id)
    return {
        "rooms": int(rooms),
        "solutions": int(solutions),
        "accepted": int(accepted),
        "helpful_votes": int(helpful),
    }


def list_ranks(db: Session, *, course_id: int, limit: int = 15) -> list[HelpRankOut]:
    """Leaderboard from Hilbert-weighted reputation, not raw likes."""
    author_ids = {
        row[0]
        for row in db.query(HelpPost.author_user_id)
        .filter(HelpPost.course_id == course_id)
        .distinct()
        .all()
    }
    author_ids.update(
        row[0]
        for row in db.query(HelpReply.author_user_id)
        .join(HelpPost, HelpPost.id == HelpReply.post_id)
        .filter(HelpPost.course_id == course_id)
        .distinct()
        .all()
    )
    ranked: list[HelpRankOut] = []
    for user_id in author_ids:
        user = db.get(User, user_id)
        activity = _user_activity(db, course_id=course_id, user_id=user_id)
        rep = compute_reputation(**activity)
        ranked.append(
            HelpRankOut(
                rank=0,
                user_id=user_id,
                display_name=(
                    (user.display_name if user else None)
                    or (user.email if user else None)
                    or "Classmate"
                ),
                handle=_handle_for(user),
                helpful_points=activity["helpful_votes"],
                reply_count=activity["solutions"],
                node_points=rep.node_points,
                hilbert_weight=rep.hilbert_weight,
                rooms_score=rep.rooms_score,
                tier=rep.tier,
                stars=rep.stars,
            )
        )
    ranked.sort(
        key=lambda item: (item.hilbert_weight, item.node_points, item.helpful_points),
        reverse=True,
    )
    return [
        item.model_copy(update={"rank": index})
        for index, item in enumerate(ranked[:limit], start=1)
    ]


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
    db.query(HelpPostVote).filter(HelpPostVote.post_id == post.id).delete()
    db.query(HelpInterest).filter(HelpInterest.post_id == post.id).delete()
    db.query(HelpPostFile).filter(HelpPostFile.post_id == post.id).delete()
    db.delete(post)
    db.commit()


def express_interest(
    db: Session, *, post: HelpPost, user: User, note: str
) -> HelpInterestOut:
    if post.author_user_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You already own this room.",
        )
    text = (note or "").strip()[:400]
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add a short offer to help.",
        )
    existing = (
        db.query(HelpInterest)
        .filter(HelpInterest.post_id == post.id, HelpInterest.from_user_id == user.id)
        .one_or_none()
    )
    if existing:
        existing.note = text
        db.commit()
        db.refresh(existing)
        row = existing
    else:
        row = HelpInterest(post_id=post.id, from_user_id=user.id, note=text)
        db.add(row)
        db.commit()
        db.refresh(row)
    return HelpInterestOut(
        id=row.id,
        post_id=row.post_id,
        from_display=user.display_name or user.email,
        from_user_id=user.id,
        note=row.note,
        created_at=row.created_at,
        is_mine=True,
    )


def accept_reply(db: Session, *, reply: HelpReply, post: HelpPost, user: User) -> HelpPostOut:
    if post.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the room author can accept a solution.",
        )
    if reply.post_id != post.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That solution is not on this room.",
        )
    db.query(HelpReply).filter(HelpReply.post_id == post.id).update({"accepted": False})
    reply.accepted = True
    post.status = "solved"
    db.commit()
    db.refresh(post)
    return serialize_post(db, post, user, include_replies=True)


def attach_file(
    db: Session,
    *,
    post: HelpPost,
    user: User,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> HelpFileOut:
    if post.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the room author can attach files.",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file.")
    if len(data) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (10 MB max).",
        )
    name = (filename or "file.bin").lower()
    ext = name[name.rfind(".") :] if "." in name else ""
    if ext not in _FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Supported: CSV, PDF, MATLAB, STEP, PNG, ZIP, TXT, MD, DOCX.",
        )
    folder = _STORAGE_ROOT / str(post.course_id)
    folder.mkdir(parents=True, exist_ok=True)
    stored = f"{uuid.uuid4().hex}{ext}"
    (folder / stored).write_bytes(data)
    row = HelpPostFile(
        post_id=post.id,
        original_filename=Path(filename or stored).name[:120],
        stored_filename=stored,
        content_type=content_type,
        byte_size=len(data),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return HelpFileOut(
        id=row.id,
        original_filename=row.original_filename,
        byte_size=row.byte_size,
        content_type=row.content_type,
        download_url=f"/help-room/files/{row.id}",
    )


def get_file_row(db: Session, file_id: int) -> HelpPostFile:
    row = db.get(HelpPostFile, file_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    return row


def file_path(row: HelpPostFile, course_id: int) -> Path:
    return _STORAGE_ROOT / str(course_id) / row.stored_filename


def _parse_skills(raw: str | None) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return [part.strip() for part in raw.split(",") if part.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed][:12]
    return []


def get_profile(
    db: Session, *, course_id: int, user_id: int, viewer: User
) -> HelpProfileOut:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    membership = (
        db.query(CourseMembership)
        .filter(CourseMembership.course_id == course_id, CourseMembership.user_id == user_id)
        .one_or_none()
    )
    if membership is None or membership.role != "student":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No classmate profile in this course.",
        )
    if viewer.id != user_id:
        user.profile_views = int(getattr(user, "profile_views", 0) or 0) + 1
        db.commit()
    activity = _user_activity(db, course_id=course_id, user_id=user_id)
    rep = compute_reputation(**activity)
    followers = (
        db.query(HelpFollow)
        .filter(HelpFollow.course_id == course_id, HelpFollow.followee_id == user_id)
        .count()
    )
    following = (
        db.query(HelpFollow)
        .filter(HelpFollow.course_id == course_id, HelpFollow.follower_id == user_id)
        .count()
    )
    followed = (
        db.query(HelpFollow)
        .filter(
            HelpFollow.course_id == course_id,
            HelpFollow.follower_id == viewer.id,
            HelpFollow.followee_id == user_id,
        )
        .first()
        is not None
    )
    role = "Student"
    if (user.country or "").strip():
        role = f"{user.country.strip()} · Student"
    return HelpProfileOut(
        user_id=user.id,
        display_name=user.display_name,
        handle=_handle_for(user),
        bio=user.bio,
        country=user.country or "Morocco",
        role_label=role,
        skills=_parse_skills(user.skills_json),
        rooms=activity["rooms"],
        solutions=activity["solutions"],
        accepted=activity["accepted"],
        helpful_votes=activity["helpful_votes"],
        followers=int(followers),
        following=int(following),
        profile_views=int(getattr(user, "profile_views", 0) or 0),
        node_points=rep.node_points,
        hilbert_weight=rep.hilbert_weight,
        rooms_score=rep.rooms_score,
        tier=rep.tier,
        stars=rep.stars,
        followed_by_me=followed,
        is_me=viewer.id == user_id,
    )


def toggle_follow(
    db: Session, *, course_id: int, followee_id: int, viewer: User
) -> HelpProfileOut:
    if followee_id == viewer.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="You cannot follow yourself.",
        )
    existing = (
        db.query(HelpFollow)
        .filter(
            HelpFollow.course_id == course_id,
            HelpFollow.follower_id == viewer.id,
            HelpFollow.followee_id == followee_id,
        )
        .one_or_none()
    )
    if existing:
        db.delete(existing)
    else:
        db.add(
            HelpFollow(
                course_id=course_id,
                follower_id=viewer.id,
                followee_id=followee_id,
            )
        )
    db.commit()
    return get_profile(db, course_id=course_id, user_id=followee_id, viewer=viewer)
