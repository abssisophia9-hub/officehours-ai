"""
ORM and Pydantic models for student requests.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    student_id: Mapped[str | None] = mapped_column(String, nullable=True)
    student_name: Mapped[str | None] = mapped_column(String, nullable=True)
    course: Mapped[str | None] = mapped_column(String, nullable=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    code_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    urgency: Mapped[str | None] = mapped_column(String, nullable=True)
    learning_style: Mapped[str | None] = mapped_column(String, nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    oracle_category: Mapped[str | None] = mapped_column(String, nullable=True)
    oracle_difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    oracle_estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oracle_tags: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    alternative_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    estimated_wait_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    student_hint: Mapped[str | None] = mapped_column(Text, nullable=True)
    oracle_trace_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # How the student wants to be helped: async message, face-to-face, or online call.
    help_mode: Mapped[str] = mapped_column(String, nullable=False, default="message")
    # TA staffing loop: open → claimed → in_progress → helped.
    work_status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    claimed_by: Mapped[str | None] = mapped_column(String, nullable=True)
    claimed_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Submitter (even Quiet ask). Used for "my asks"; never exposed as identity.
    created_by_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    helped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Direct async reply from a TA (message mode) — visible on student status.
    ta_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    ta_replied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


HELP_MODES = ("message", "face_to_face", "online_meeting")
WORK_STATUSES = ("open", "claimed", "in_progress", "helped")


class RequestCreate(BaseModel):
    text: str = Field(min_length=1, max_length=8000)
    anonymous: bool = True
    student_id: str | None = Field(default=None, max_length=64)
    student_name: str | None = Field(default=None, max_length=200)
    course: str | None = Field(default=None, max_length=64)
    course_id: int | None = Field(default=None, ge=1)
    code_snippet: str | None = Field(default=None, max_length=20000)
    category: str | None = Field(default=None, max_length=80)
    urgency: str | None = Field(default=None, max_length=40)
    learning_style: str | None = Field(default=None, max_length=40)
    cluster_id: int | None = None
    recommended_action: str | None = Field(default=None, max_length=500)
    sensitive: bool | None = None
    help_mode: str = Field(default="message", max_length=32)


class OracleAnalyzerOut(BaseModel):
    category: str | None = None
    difficulty: str | None = None
    estimated_minutes: int | None = None
    tags: list[str] = Field(default_factory=list)
    urgency: str | None = None
    rationale: str | None = None


class OracleMatcherOut(BaseModel):
    assigned_ta: str | None = None
    alternative_ta: str | None = None
    estimated_wait_minutes: int | None = None
    rationale: str | None = None


class OracleSynthesizerOut(BaseModel):
    student_hint: str | None = None
    teaching_approach: str | None = None
    similar_count: int = 0
    similar_questions: list[dict[str, Any]] = Field(default_factory=list)
    kb_insight: str | None = None


class OracleStepOut(BaseModel):
    agent: str
    elapsed_ms: int


class OracleResultOut(BaseModel):
    analyzer: OracleAnalyzerOut
    matcher: OracleMatcherOut
    synthesizer: OracleSynthesizerOut
    steps: list[OracleStepOut] = Field(default_factory=list)
    elapsed_ms: int | None = None


class RequestOut(RequestCreate):
    id: int
    created_at: datetime
    sensitive: bool = False
    help_mode: str = "message"
    work_status: str = "open"
    claimed_by: str | None = None
    claimed_by_user_id: int | None = None
    claimed_at: datetime | None = None
    helped_at: datetime | None = None
    ta_reply: str | None = None
    ta_replied_at: datetime | None = None
    oracle_category: str | None = None
    oracle_difficulty: str | None = None
    oracle_estimated_minutes: int | None = None
    oracle_tags: list[str] = Field(default_factory=list)
    assigned_ta: str | None = None
    alternative_ta: str | None = None
    estimated_wait_minutes: int | None = None
    student_hint: str | None = None
    oracle: OracleResultOut | None = None
    # Anonymous solidarity (non-sensitive only in messaging).
    similar_asks_this_week: int = 0
    solidarity_message: str | None = None
    study_buddy_eligible: bool = False

    model_config = ConfigDict(from_attributes=True)


class RequestStatusOut(BaseModel):
    request_code: int
    status: str
    headline: str
    message: str
    category: str | None = None
    submitted_at: datetime
    anonymous_submission: bool
    help_mode: str | None = None
    work_status: str | None = None
    claimed_by: str | None = None
    claimed_by_user_id: int | None = None
    ta_reply: str | None = None
    recommended_next_step: str | None = None
    agenda_hint: str | None = None
    student_hint: str | None = None
    assigned_ta: str | None = None
    estimated_wait_minutes: int | None = None
    # Shared cluster group meeting (same for every request_id on the decision).
    meeting_title: str | None = None
    meeting_when: str | None = None
    meeting_place: str | None = None
    group_meeting: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True)
