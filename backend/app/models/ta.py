"""
Pydantic models for TA queue operations that feed the professor KB curation loop.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge import KnowledgeEntryOut
from app.models.request import RequestOut

TaResolveStatus = Literal["resolved", "needs_professor"]
TaWorkStatusUpdate = Literal["claimed", "in_progress", "helped"]


class TaQueueItem(BaseModel):
    request: RequestOut
    knowledge_entry: KnowledgeEntryOut | None = None
    learning_style: str | None = None
    urgency: str | None = None

    model_config = ConfigDict(from_attributes=True)


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
