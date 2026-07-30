"""Peer study notes API — share, like, comment, download (course members only)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.peer_notes import (
    PeerNoteCommentCreate,
    PeerNoteCommentOut,
    PeerNoteLikeOut,
    PeerNoteOut,
)
from app.routes.auth import get_current_user
from app.services.access_control import get_membership, require_course_role
from app.services.peer_notes_service import (
    add_comment,
    create_peer_note,
    delete_own_note,
    get_peer_note,
    list_comments,
    list_peer_notes,
    note_file_path,
    serialize_note,
    toggle_like,
)

router = APIRouter(prefix="/peer-notes", tags=["peer-notes"])


def _require_course_member(db: Session, user: User, course_id: int):
    course, membership = require_course_role(
        db,
        user,
        course_id,
        roles={"student", "ta", "professor"},
    )
    return course, membership


@router.get("/", response_model=list[PeerNoteOut])
def feed(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_course_member(db, user, course_id)
    return list_peer_notes(db, course_id=course_id, viewer=user)


@router.post("/", response_model=PeerNoteOut, status_code=status.HTTP_201_CREATED)
async def upload_note(
    course_id: int = Form(...),
    title: str = Form(...),
    about: str = Form(...),
    caption: str | None = Form(default=None),
    anonymous: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Students share notes with classmates. Title + about are required before file."""
    _require_course_member(db, user, course_id)
    # Only students (and dual-role TAs acting as classmates) post peer notes —
    # professors/TAs may also share if they are members; keep open to all members.
    data = await file.read()
    note = create_peer_note(
        db,
        course_id=course_id,
        author=user,
        title=title,
        about=about,
        caption=caption,
        anonymous=anonymous,
        filename=file.filename or "notes.bin",
        content_type=file.content_type,
        data=data,
    )
    return serialize_note(db, note, user)


@router.post("/{note_id}/like", response_model=PeerNoteLikeOut)
def like_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    liked, count = toggle_like(db, note=note, user=user)
    return PeerNoteLikeOut(note_id=note.id, liked=liked, like_count=count)


@router.get("/{note_id}/comments", response_model=list[PeerNoteCommentOut])
def get_comments(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    return list_comments(db, note=note, viewer=user)


@router.post(
    "/{note_id}/comments",
    response_model=PeerNoteCommentOut,
    status_code=status.HTTP_201_CREATED,
)
def post_comment(
    note_id: int,
    payload: PeerNoteCommentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    comment = add_comment(
        db,
        note=note,
        author=user,
        body=payload.body,
        anonymous=payload.anonymous,
    )
    return list_comments(db, note=note, viewer=user)[-1]


@router.get("/{note_id}/download")
def download_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    path = note_file_path(note)
    return FileResponse(
        path,
        media_type=note.content_type or "application/octet-stream",
        filename=note.original_filename,
    )


@router.get("/{note_id}/preview")
def preview_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    if not note.is_image:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Preview is only available for image notes.",
        )
    path = note_file_path(note)
    return FileResponse(
        path,
        media_type=note.content_type or "image/jpeg",
        filename=note.original_filename,
    )


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    note = get_peer_note(db, note_id)
    get_membership(db, user, note.course_id)
    delete_own_note(db, note=note, user=user)
    return None
