"""
ORM and Pydantic models for professor recommendation decisions.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class RecommendationDecision(Base):
    __tablename__ = "recommendation_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_kind: Mapped[str] = mapped_column(String, nullable=False, index=True)
    action_title: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="approved")
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    professor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_ids: Mapped[str] = mapped_column(Text, nullable=False)
    action_plan: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RecommendationDecisionCreate(BaseModel):
    card_id: str
    action_kind: str
    action_title: str
    status: str = Field(pattern="^(approved|editing|dismissed)$")
    cluster_id: int | None = None
    professor_note: str | None = None
    request_ids: list[int]


class RecommendationDecisionOut(BaseModel):
    id: int
    card_id: str
    action_kind: str
    action_title: str
    status: str
    cluster_id: int | None = None
    professor_note: str | None = None
    request_ids: list[int]
    action_plan: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
