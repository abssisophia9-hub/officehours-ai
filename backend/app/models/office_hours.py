"""
ORM and Pydantic models for professor office-hour availability windows.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

VALID_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


class OfficeHoursWindow(Base):
    __tablename__ = "office_hours_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    day: Mapped[str] = mapped_column(String, nullable=False)
    start: Mapped[str] = mapped_column(String, nullable=False)
    end: Mapped[str] = mapped_column(String, nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False, default="TBD")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class OfficeHoursWindowCreate(BaseModel):
    day: str = Field(pattern=r"^(Monday|Tuesday|Wednesday|Thursday|Friday)$")
    start: str = Field(min_length=4, max_length=5)
    end: str = Field(min_length=4, max_length=5)
    location: str = Field(default="TBD", max_length=200)


class OfficeHoursWindowOut(BaseModel):
    id: int
    day: str
    start: str
    end: str
    location: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
