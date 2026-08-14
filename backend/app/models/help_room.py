"""Stuck Room — classmates share what they are stuck on; helpful marks, not likes."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class HelpPost(Base):
    __tablename__ = "help_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    chapter: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class HelpReply(Base):
    __tablename__ = "help_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    author_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class HelpfulMark(Base):
    """One classmate saying a reply actually unlocked the stuck point."""

    __tablename__ = "help_helpful_marks"
    __table_args__ = (
        UniqueConstraint("reply_id", "rater_user_id", name="uq_help_helpful_mark"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reply_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rater_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class HelpPostCreate(BaseModel):
    course_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    chapter: str | None = Field(default=None, max_length=80)
    anonymous: bool = False


class HelpReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    anonymous: bool = False


class HelpReplyOut(BaseModel):
    id: int
    post_id: int
    body: str
    anonymous: bool
    author_display: str
    created_at: datetime
    is_mine: bool = False
    helpful_count: int = 0
    marked_helpful_by_me: bool = False

    model_config = ConfigDict(from_attributes=True)


class HelpPostOut(BaseModel):
    id: int
    course_id: int
    title: str
    body: str
    chapter: str | None = None
    anonymous: bool
    author_display: str
    created_at: datetime
    is_mine: bool = False
    reply_count: int = 0
    replies: list[HelpReplyOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class HelpfulMarkOut(BaseModel):
    reply_id: int
    marked: bool
    helpful_count: int


class HelpRankOut(BaseModel):
    rank: int
    user_id: int
    display_name: str
    helpful_points: int
    reply_count: int


class ReviewInsightTopicOut(BaseModel):
    label: str
    bucket: str
    office_hours_count: int = 0
    stuck_post_count: int = 0
    total_signal: int = 0
    sample_questions: list[str] = Field(default_factory=list)
    review_hint: str
    emphasize: bool = False


class ReviewInsightsOut(BaseModel):
    course_id: int
    course_code: str | None = None
    topics: list[ReviewInsightTopicOut] = Field(default_factory=list)
    office_hours_total: int = 0
    stuck_post_total: int = 0
    message: str
