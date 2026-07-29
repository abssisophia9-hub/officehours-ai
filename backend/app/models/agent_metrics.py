"""Telemetry for KB agent asks and human gold labels for agent evaluation."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KbAskEvent(Base):
    """One student /agent/ask attempt — used for per-course hit-rate metrics."""

    __tablename__ = "kb_ask_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    should_seek_help: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    matched_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )


class AgentGoldLabel(Base):
    """Human judgment used to evaluate Analyzer / Matcher (and hint usefulness)."""

    __tablename__ = "agent_gold_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    label_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    gold_category: Mapped[str] = mapped_column(String, nullable=False, index=True)
    gold_assigned_ta: Mapped[str | None] = mapped_column(String, nullable=True)
    gold_hint_useful: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    course_code: Mapped[str | None] = mapped_column(String, nullable=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    labeled_by: Mapped[str | None] = mapped_column(String, nullable=True)
    label_source: Mapped[str] = mapped_column(
        String, nullable=False, default="human_gold"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class GoldLabelCreate(BaseModel):
    text: str = Field(min_length=3, max_length=4000)
    gold_category: str = Field(min_length=2, max_length=120)
    gold_assigned_ta: str | None = Field(default=None, max_length=120)
    gold_hint_useful: int | None = Field(default=None, ge=0, le=1)
    department: str | None = Field(default=None, max_length=32)
    course_code: str | None = Field(default=None, max_length=64)
    course_id: int | None = None
    labeled_by: str | None = Field(default=None, max_length=200)
    label_id: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)


class GoldLabelOut(BaseModel):
    id: int
    label_id: str | None = None
    text: str
    gold_category: str
    gold_assigned_ta: str | None = None
    gold_hint_useful: int | None = None
    department: str | None = None
    course_code: str | None = None
    course_id: int | None = None
    labeled_by: str | None = None
    label_source: str
    notes: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CourseKbHitRate(BaseModel):
    course_id: int | None
    course_code: str | None = None
    course_title: str | None = None
    asks: int
    hits: int
    misses: int
    hit_rate: float
    avg_confidence_on_hits: float | None = None


class KbHitRateReport(BaseModel):
    total_asks: int
    total_hits: int
    total_misses: int
    overall_hit_rate: float
    by_course: list[CourseKbHitRate]
