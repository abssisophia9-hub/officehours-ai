"""
Pydantic models for TA queue operations that feed the professor KB curation loop.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge import KnowledgeEntryOut
from app.models.request import RequestOut

TaResolveStatus = Literal["resolved", "needs_professor"]
TaWorkStatusUpdate = Literal["open", "claimed", "in_progress", "helped"]
TaAssistMode = Literal[
    "draft_reply", "socratic", "refresh_teaching", "rewrite_reply"
]


class HelpCoachSimilarOpen(BaseModel):
    id: int
    text: str
    work_status: str | None = None
    assigned_ta: str | None = None
    cluster_id: int | None = None
    category: str | None = None
    match_reason: str | None = None


class HelpCoachKbHit(BaseModel):
    id: int | None = None
    question_text: str | None = None
    category: str | None = None
    similarity: float | None = None
    student_hint: str | None = None
    answer_preview: str | None = None


class HelpCoachOut(BaseModel):
    """TA-facing Help Coach packet (while helping, not only at intake)."""

    ask_kind: Literal["factual", "conceptual"] | None = None
    teaching_approach: str | None = None
    student_hint: str | None = None
    kb_insight: str | None = None
    difficulty: str | None = None
    estimated_minutes: int | None = None
    learning_style: str | None = None
    category: str | None = None
    similar_open_count: int = 0
    similar_open: list[HelpCoachSimilarOpen] = Field(default_factory=list)
    similar_kb: list[HelpCoachKbHit] = Field(default_factory=list)
    socratic_steps: list[str] = Field(default_factory=list)
    group_help_suggested: bool = False
    coach_summary: str | None = None


class TaQueueItem(BaseModel):
    request: RequestOut
    knowledge_entry: KnowledgeEntryOut | None = None
    learning_style: str | None = None
    urgency: str | None = None
    similar_open_count: int = 0
    help_coach: HelpCoachOut | None = None

    model_config = ConfigDict(from_attributes=True)


class TaAssistRequest(BaseModel):
    request_id: int
    mode: TaAssistMode = "draft_reply"
    # Optional focus note (e.g. "uncle rotation") or existing reply to rewrite.
    focus: str | None = Field(default=None, max_length=500)
    current_reply: str | None = Field(default=None, max_length=4000)


class TaAssistResponse(BaseModel):
    request_id: int
    mode: TaAssistMode
    message: str
    draft_reply: str | None = None
    teaching_approach: str | None = None
    student_hint: str | None = None
    socratic_steps: list[str] = Field(default_factory=list)
    help_coach: HelpCoachOut
    backend: str | None = None
    # Escape hatch for clients that want raw coach fields.
    extras: dict[str, Any] = Field(default_factory=dict)


class TaResolveRequest(BaseModel):
    request_id: int
    teaching_notes: str = Field(min_length=3, max_length=8000)
    student_hint: str | None = Field(default=None, max_length=2000)
    resolution_status: TaResolveStatus = "resolved"
    # Optional legacy field — ignored when auth is present; kept for older clients.
    ta_name: str | None = Field(default=None, max_length=120)


class TaResolveResponse(BaseModel):
    request_id: int
    knowledge_entry: KnowledgeEntryOut
    message: str


class TaClaimRequest(BaseModel):
    request_id: int


class TaWorkStatusRequest(BaseModel):
    request_id: int
    status: TaWorkStatusUpdate


class TaReplyRequest(BaseModel):
    request_id: int
    reply: str = Field(min_length=3, max_length=4000)
    # Also refresh the student_hint on the request / KB draft when provided.
    update_student_hint: bool = True


class TaHandoffRequest(BaseModel):
    request_id: int
    """Backup TA takes primary ownership."""


class TaActionResponse(BaseModel):
    request: RequestOut
    message: str
