"""Follow-up messages on an existing office-hours request."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class RequestFollowUp(Base):
    __tablename__ = "request_followups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("requests.id"), nullable=False, index=True
    )
    author_role: Mapped[str] = mapped_column(String, nullable=False)
    # student | ta | professor
    author_name: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class FollowUpCreate(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    author_role: str = Field(default="student", min_length=2, max_length=32)
    author_name: str = Field(min_length=1, max_length=120)


class FollowUpOut(BaseModel):
    id: int
    request_id: int
    author_role: str
    author_name: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
