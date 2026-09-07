"""Peer study notes — storage, feed, likes, comments."""

from __future__ import annotations

import mimetypes
import re
import uuid
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.peer_notes import (
    MAX_PEER_NOTE_BYTES,
    PEER_NOTE_EXTENSIONS,
    PeerNote,
    PeerNoteComment,
    PeerNoteCommentOut,
    PeerNoteLike,
    PeerNoteOut,
)

STORAGE_ROOT = Path(__file__).resolve().parents[2] / "data" / "peer_notes"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def ensure_storage_dir(course_id: int) -> Path:
    path = STORAGE_ROOT / str(course_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extension(filename: str) -> str:
    name = (filename or "").lower().strip()
    return name[name.rfind(".") :] if "." in name else ""


def _safe_filename(original: str) -> str:
    base = Path(original or "notes").name
    cleaned = re.sub(r"[^\w.\-]+", "_", base).strip("._") or "notes"
    return cleaned[:120]


def create_peer_note(
    db: Session,
    *,
    course_id: int,
    author: User,
    title: str,
    about: str,
    caption: str | None,
    anonymous: bool,
    filename: str,
    content_type: str | None,
    data: bytes,
) -> PeerNote:
    title_clean = (title or "").strip()
    about_clean = (about or "").strip()
    if not title_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Title is required.",
        )
    if not about_clean:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Describe what your notes are about before uploading.",
        )
    if len(data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file.",
        )
    from app.services.upload_security import assert_upload_allowed, safe_filename

    ext = assert_upload_allowed(
        filename=filename,
        data=data,
        allowed_extensions=PEER_NOTE_EXTENSIONS,
        max_bytes=MAX_PEER_NOTE_BYTES,
    )

    folder = ensure_storage_dir(course_id)
    stored = f"{uuid.uuid4().hex}_{safe_filename(filename)}"
    dest = folder / stored
    dest.write_bytes(data)

    guessed = content_type or mimetypes.guess_type(filename)[0]
    note = PeerNote(
        course_id=course_id,
        author_user_id=author.id,
        title=title_clean[:200],
        about=about_clean[:2000],
        caption=(caption or "").strip()[:2000] or None,
        anonymous=bool(anonymous),
        original_filename=safe_filename(filename),
        stored_filename=stored,
        content_type=guessed,
        byte_size=len(data),
        is_image=ext in IMAGE_EXTENSIONS,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_peer_notes(db: Session, *, course_id: int, viewer: User) -> list[PeerNoteOut]:
    notes = (
        db.query(PeerNote)
        .filter(PeerNote.course_id == course_id)
        .order_by(PeerNote.created_at.desc(), PeerNote.id.desc())
        .limit(100)
        .all()
    )
    return [serialize_note(db, note, viewer) for note in notes]


def get_peer_note(db: Session, note_id: int) -> PeerNote:
    note = db.get(PeerNote, note_id)
    if note is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Note not found.",
        )
    return note


def note_file_path(note: PeerNote) -> Path:
    path = STORAGE_ROOT / str(note.course_id) / note.stored_filename
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File missing from storage.",
        )
    return path


def serialize_note(db: Session, note: PeerNote, viewer: User) -> PeerNoteOut:
    like_count = (
        db.query(PeerNoteLike).filter(PeerNoteLike.note_id == note.id).count()
    )
    comment_count = (
        db.query(PeerNoteComment)
        .filter(PeerNoteComment.note_id == note.id)
        .count()
    )
    liked_by_me = (
        db.query(PeerNoteLike)
        .filter(
            PeerNoteLike.note_id == note.id,
            PeerNoteLike.user_id == viewer.id,
        )
        .first()
        is not None
    )
    author = db.get(User, note.author_user_id)
    if note.anonymous and note.author_user_id != viewer.id:
        author_display = "Classmate"
    else:
        author_display = (
            (author.display_name if author else None)
            or (author.email if author else None)
            or "Classmate"
        )

    return PeerNoteOut(
        id=note.id,
        course_id=note.course_id,
        title=note.title,
        about=note.about,
        caption=note.caption,
        anonymous=note.anonymous,
        author_display=author_display,
        original_filename=note.original_filename,
        content_type=note.content_type,
        byte_size=note.byte_size,
        is_image=note.is_image,
        like_count=like_count,
        comment_count=comment_count,
        liked_by_me=liked_by_me,
        is_mine=note.author_user_id == viewer.id,
        created_at=note.created_at,
        preview_url=f"/peer-notes/{note.id}/preview" if note.is_image else None,
        download_url=f"/peer-notes/{note.id}/download",
    )


def toggle_like(db: Session, *, note: PeerNote, user: User) -> tuple[bool, int]:
    existing = (
        db.query(PeerNoteLike)
        .filter(
            PeerNoteLike.note_id == note.id,
            PeerNoteLike.user_id == user.id,
        )
        .one_or_none()
    )
    if existing:
        db.delete(existing)
        db.commit()
        liked = False
    else:
        db.add(PeerNoteLike(note_id=note.id, user_id=user.id))
        db.commit()
        liked = True
    count = db.query(PeerNoteLike).filter(PeerNoteLike.note_id == note.id).count()
    return liked, count


def add_comment(
    db: Session,
    *,
    note: PeerNote,
    author: User,
    body: str,
    anonymous: bool,
) -> PeerNoteComment:
    text = (body or "").strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Comment cannot be empty.",
        )
    comment = PeerNoteComment(
        note_id=note.id,
        author_user_id=author.id,
        body=text[:2000],
        anonymous=bool(anonymous),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def list_comments(
    db: Session, *, note: PeerNote, viewer: User
) -> list[PeerNoteCommentOut]:
    rows = (
        db.query(PeerNoteComment)
        .filter(PeerNoteComment.note_id == note.id)
        .order_by(PeerNoteComment.created_at.asc(), PeerNoteComment.id.asc())
        .limit(200)
        .all()
    )
    out: list[PeerNoteCommentOut] = []
    for row in rows:
        author = db.get(User, row.author_user_id)
        if row.anonymous and row.author_user_id != viewer.id:
            display = "Classmate"
        else:
            display = (
                (author.display_name if author else None)
                or (author.email if author else None)
                or "Classmate"
            )
        out.append(
            PeerNoteCommentOut(
                id=row.id,
                note_id=row.note_id,
                body=row.body,
                anonymous=row.anonymous,
                author_display=display,
                created_at=row.created_at,
                is_mine=row.author_user_id == viewer.id,
            )
        )
    return out


def delete_own_note(db: Session, *, note: PeerNote, user: User) -> None:
    if note.author_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own notes.",
        )
    path = STORAGE_ROOT / str(note.course_id) / note.stored_filename
    db.query(PeerNoteLike).filter(PeerNoteLike.note_id == note.id).delete()
    db.query(PeerNoteComment).filter(PeerNoteComment.note_id == note.id).delete()
    db.delete(note)
    db.commit()
    if path.is_file():
        path.unlink()
