"""Peer study notes — classmates share downloadable notes (not professor KB)."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

PEER_NOTE_EXTENSIONS = {
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".gif",
    ".txt",
    ".md",
    ".docx",
}
MAX_PEER_NOTE_BYTES = 20_000_000


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PeerNote(Base):
    __tablename__ = "peer_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    # What the notes are about (topic / week / lecture) — required before upload.
    about: Mapped[str] = mapped_column(Text, nullable=False)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    original_filename: Mapped[str] = mapped_column(String, nullable=False)
    stored_filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_image: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class PeerNoteLike(Base):
    __tablename__ = "peer_note_likes"
    __table_args__ = (
        UniqueConstraint("note_id", "user_id", name="uq_peer_note_like"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class PeerNoteComment(Base):
    __tablename__ = "peer_note_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    note_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class PeerNoteCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    anonymous: bool = False


class PeerNoteCommentOut(BaseModel):
    id: int
    note_id: int
    body: str
    anonymous: bool
    author_display: str
    created_at: datetime
    is_mine: bool = False

    model_config = ConfigDict(from_attributes=True)


class PeerNoteOut(BaseModel):
    id: int
    course_id: int
    title: str
    about: str
    caption: str | None = None
    anonymous: bool
    author_display: str
    original_filename: str
    content_type: str | None = None
    byte_size: int
    is_image: bool
    like_count: int = 0
    comment_count: int = 0
    liked_by_me: bool = False
    is_mine: bool = False
    created_at: datetime
    preview_url: str | None = None
    download_url: str

    model_config = ConfigDict(from_attributes=True)


class PeerNoteLikeOut(BaseModel):
    note_id: int
    liked: bool
    like_count: int
