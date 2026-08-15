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
    flair: Mapped[str] = mapped_column(
        String, nullable=False, default="stuck", server_default="stuck"
    )
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class HelpReply(Base):
    __tablename__ = "help_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    parent_reply_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
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


class HelpPostVote(Base):
    """Same-here upvote on a stuck post (Reddit-style score, not helper karma)."""

    __tablename__ = "help_post_votes"
    __table_args__ = (
        UniqueConstraint("post_id", "user_id", name="uq_help_post_vote"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    post_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


POST_FLAIRS = ("stuck", "aha", "vent", "find_peer")


class HelpReachOut(Base):
    """Identified handshake after an aha — not a chat, not staff-visible."""

    __tablename__ = "help_reach_outs"
    __table_args__ = (
        UniqueConstraint("reply_id", "from_user_id", name="uq_help_reach_out"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    reply_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    from_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    to_user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class ReviewTopicNote(Base):
    """Professor annotation on a review-insight topic (covered / next cohort)."""

    __tablename__ = "review_topic_notes"
    __table_args__ = (
        UniqueConstraint("course_id", "topic_key", name="uq_review_topic_note"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    topic_key: Mapped[str] = mapped_column(String, nullable=False)
    review_status: Mapped[str] = mapped_column(String, nullable=False, default="watch")
    next_cohort_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class HelpPostCreate(BaseModel):
    course_id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=4000)
    chapter: str | None = Field(default=None, max_length=80)
    flair: str = Field(default="stuck", max_length=20)
    anonymous: bool = False


class HelpReplyCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    anonymous: bool = False
    parent_reply_id: int | None = None


class HelpReplyOut(BaseModel):
    id: int
    post_id: int
    parent_reply_id: int | None = None
    body: str
    anonymous: bool
    author_display: str
    author_karma: int = 0
    created_at: datetime
    is_mine: bool = False
    helpful_count: int = 0
    marked_helpful_by_me: bool = False
    reachable: bool = False
    reached_out_by_me: bool = False
    children: list["HelpReplyOut"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class HelpPostOut(BaseModel):
    id: int
    course_id: int
    title: str
    body: str
    chapter: str | None = None
    flair: str = "stuck"
    anonymous: bool
    author_display: str
    author_karma: int = 0
    created_at: datetime
    is_mine: bool = False
    reply_count: int = 0
    same_here_count: int = 0
    same_here_by_me: bool = False
    unlocked_count: int = 0
    similar_chapter_count: int = 0
    replies: list[HelpReplyOut] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


HelpReplyOut.model_rebuild()


class HelpPostVoteOut(BaseModel):
    post_id: int
    marked: bool
    same_here_count: int


class HelpCommunityOut(BaseModel):
    course_id: int
    course_code: str | None = None
    course_title: str | None = None
    community_name: str
    classmate_count: int = 0
    post_count: int = 0
    comment_count: int = 0
    helper_count: int = 0


class HelpfulMarkOut(BaseModel):
    reply_id: int
    marked: bool
    helpful_count: int
    reachable: bool = False
    reached_out_by_me: bool = False


class HelpReachOutCreate(BaseModel):
    note: str = Field(
        default="Your perspective unlocked it for me — thanks. If you're open to it, I'd like to compare notes.",
        min_length=1,
        max_length=500,
    )


class HelpReachOutOut(BaseModel):
    id: int
    course_id: int
    reply_id: int
    post_title: str
    note: str
    from_display: str
    to_display: str
    is_incoming: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HelpRankOut(BaseModel):
    rank: int
    user_id: int
    display_name: str
    helpful_points: int
    reply_count: int


class ReviewInsightQuestionOut(BaseModel):
    source: str
    text: str
    request_id: int | None = None
    cluster_id: int | None = None
    stuck_post_id: int | None = None


class ReviewInsightTopicOut(BaseModel):
    topic_key: str
    label: str
    bucket: str
    office_hours_count: int = 0
    stuck_post_count: int = 0
    total_signal: int = 0
    sample_questions: list[str] = Field(default_factory=list)
    questions: list[ReviewInsightQuestionOut] = Field(default_factory=list)
    request_ids: list[int] = Field(default_factory=list)
    cluster_id: int | None = None
    review_hint: str
    emphasize: bool = False
    review_status: str = "watch"
    next_cohort_note: str | None = None


class ReviewInsightsOut(BaseModel):
    course_id: int
    course_code: str | None = None
    topics: list[ReviewInsightTopicOut] = Field(default_factory=list)
    office_hours_total: int = 0
    stuck_post_total: int = 0
    message: str


class ReviewTopicNoteUpdate(BaseModel):
    course_id: int = Field(ge=1)
    topic_key: str = Field(min_length=1, max_length=200)
    review_status: str = Field(default="watch", max_length=20)
    next_cohort_note: str | None = Field(default=None, max_length=2000)


class InsightFaqRequest(BaseModel):
    course_id: int = Field(ge=1)
    topic_key: str = Field(min_length=1, max_length=200)
