"""
ORM and Pydantic models for student requests.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class Request(Base):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    student_id: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class RequestCreate(BaseModel):
    text: str
    anonymous: bool = True
    student_id: str | None = None
    category: str | None = None
    cluster_id: int | None = None
    recommended_action: str | None = None


class RequestOut(RequestCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
