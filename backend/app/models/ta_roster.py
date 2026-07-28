"""Default TA roster for Oracle Matcher — keep in sync with data/ta_roster_seed.csv.

Category tags (conceptual_question, exam_logistics, …) matter: Matcher silver
labels and runtime expertise-overlap both rely on them.
"""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

DEFAULT_TA_ROSTER = [
    {
        "name": "Alice Chen",
        "expertise_tags": [
            "trees",
            "red-black",
            "deletion",
            "rotations",
            "bst",
            "conceptual_question",
        ],
        "queue_depth": 1,
    },
    {
        "name": "Bob Martinez",
        "expertise_tags": [
            "recursion",
            "dp",
            "memoization",
            "algorithms",
            "conceptual_question",
        ],
        "queue_depth": 2,
    },
    {
        "name": "Priya Nair",
        "expertise_tags": [
            "hashing",
            "arrays",
            "search",
            "systems",
            "exam_logistics",
            "project_submission",
        ],
        "queue_depth": 1,
    },
    {
        "name": "Sam Ortiz",
        "expertise_tags": [
            "pointers",
            "memory",
            "c",
            "debugging",
            "grading_dispute",
            "emotional_stress",
            "retake_request",
            "accessibility_accommodation",
            "academic_integrity",
            "office_hours_access",
        ],
        "queue_depth": 0,
    },
]


class TaRoster(Base):
    __tablename__ = "ta_roster"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    expertise_tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    queue_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class TaRosterOut(BaseModel):
    id: int
    name: str
    expertise_tags: list[str] = Field(default_factory=list)
    queue_depth: int
    is_available: bool

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm_row(cls, row: TaRoster) -> "TaRosterOut":
        return cls(
            id=row.id,
            name=row.name,
            expertise_tags=json.loads(row.expertise_tags or "[]"),
            queue_depth=row.queue_depth,
            is_available=row.is_available,
        )
