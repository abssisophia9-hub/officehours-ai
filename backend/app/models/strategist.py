"""Pydantic models for the Revision Strategist agent."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GradeRowIn(BaseModel):
    topic: str = Field(min_length=1, max_length=160)
    score: float = Field(ge=0, le=100)
    weight: float = Field(ge=0, le=100)
    source: str | None = Field(default=None, max_length=200)


class StrategistPlanRequest(BaseModel):
    course_id: int = Field(ge=1)
    grades: list[GradeRowIn] = Field(default_factory=list)
    goal: str | None = Field(default=None, max_length=500)


class AskSampleOut(BaseModel):
    text: str
    learning_style: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class LearnerDossierOut(BaseModel):
    dominant_style: str
    style_counts: dict[str, int] = Field(default_factory=dict)
    struggles: list[str] = Field(default_factory=list)
    how_they_ask: str
    ask_count: int = 0
    help_modes: dict[str, int] = Field(default_factory=dict)
    ask_samples: list[AskSampleOut] = Field(default_factory=list)


class ResourceHitOut(BaseModel):
    kind: str
    title: str
    url: str
    snippet: str | None = None
    query: str | None = None
    why: str | None = None


class ToolCallOut(BaseModel):
    tool: str
    query: str
    hit_count: int = 0


class FocusTopicOut(BaseModel):
    topic: str
    score: float | None = None
    weight: float | None = None
    source: str | None = None
    gap: float | None = None


class StrategistPlanOut(BaseModel):
    focus: FocusTopicOut
    dossier: LearnerDossierOut
    goal: str
    planner: str
    model: str
    resources: list[ResourceHitOut] = Field(default_factory=list)
    tool_calls: list[ToolCallOut] = Field(default_factory=list)
    week: list[list[str]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    trace: dict[str, Any] = Field(default_factory=dict)
