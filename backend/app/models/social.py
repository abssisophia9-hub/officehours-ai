"""Social / peer features: study-buddy opt-in ORM."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StudyBuddyOptIn(Base):
    """Opt-in for conceptual group review — never used for sensitive categories."""

    __tablename__ = "study_buddy_opt_ins"
    __table_args__ = (UniqueConstraint("request_id", name="uq_study_buddy_request"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    display_label: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
