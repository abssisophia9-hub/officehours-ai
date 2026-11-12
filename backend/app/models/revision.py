"""Pydantic models for the Revision Agent (no grade tables)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Weakness = Literal["low", "med", "high"]
Preference = Literal[
    "example_driven",
    "step_by_step",
    "visual_structural",
    "conceptual",
    "unknown",
]
PlanMode = Literal["agent", "rule-based fallback"]
ThinkAction = Literal["search", "drop", "stop"]


class GradeTopicIn(BaseModel):
    """Client-side synthetic weakness row. Never includes numeric scores."""

    topic: str = Field(min_length=1, max_length=160)
    weakness: Weakness = "med"
    assignment_kind: Literal["text", "project", "other"] = "text"

    @field_validator("topic")
    @classmethod
    def _strip_topic(cls, value: str) -> str:
        cleaned = " ".join((value or "").split())
        if not cleaned:
            raise ValueError("topic required")
        return cleaned


class DeadlineIn(BaseModel):
    topic: str = Field(min_length=1, max_length=160)
    due_in_days: int = Field(ge=0, le=60, default=3)
    label: str | None = Field(default=None, max_length=120)


class RevisionPlanRequest(BaseModel):
    course_id: int = Field(ge=1)
    grades: list[GradeTopicIn] = Field(default_factory=list, max_length=24)
    preference: Preference = "unknown"
    deadlines: list[DeadlineIn] = Field(default_factory=list, max_length=12)
    available_minutes_today: int = Field(default=120, ge=30, le=480)


class ResourceOut(BaseModel):
    title: str
    url: str | None = None
    source: str
    why: str
    kind: str = "article"


class TimeSlotOut(BaseModel):
    day_offset: int
    label: str
    minutes: int
    topic: str
    focus: str


class IterationTraceOut(BaseModel):
    iteration: int
    action: ThinkAction
    query: str | None = None
    thinker: Literal["llm", "rules"]
    note: str | None = None
    search_hits: int = 0
    checked_ok: int = 0


class RevisionPlanOut(BaseModel):
    mode: PlanMode
    mode_label: str
    focus_topics: list[str] = Field(default_factory=list)
    preference: Preference
    resources: list[ResourceOut] = Field(default_factory=list)
    time_slots: list[TimeSlotOut] = Field(default_factory=list)
    ask_draft: str | None = None
    iterations: list[IterationTraceOut] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    caps: dict[str, Any] = Field(default_factory=dict)
    model: str | None = None
