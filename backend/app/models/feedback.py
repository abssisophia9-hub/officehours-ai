"""Bug / issue reports from the account menu."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BugReport(Base):
    __tablename__ = "bug_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    course_code: Mapped[str | None] = mapped_column(String, nullable=True)
    page_path: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class BugReportCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)
    course_id: int | None = None
    course_code: str | None = None
    role: str | None = None
    page_path: str | None = None


class BugReportOut(BaseModel):
    id: int
    title: str
    body: str
    role: str | None = None
    course_code: str | None = None
    page_path: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
