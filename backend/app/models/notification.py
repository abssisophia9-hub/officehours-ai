"""In-app inbox rows. Email is sent alongside when SMTP is configured."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    email_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class NotificationOut(BaseModel):
    id: int
    kind: str
    title: str
    body: str
    request_id: int | None = None
    course_id: int | None = None
    email_sent: bool = False
    read_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
