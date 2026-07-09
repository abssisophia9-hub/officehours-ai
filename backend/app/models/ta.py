"""
Pydantic models for TA queue operations that feed the professor KB curation loop.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge import KnowledgeEntryOut
from app.models.request import RequestOut

TaResolveStatus = Literal["resolved", "needs_professor"]


class TaQueueItem(BaseModel):
    request: RequestOut
    knowledge_entry: KnowledgeEntryOut | None = None
    learning_style: str | None = None
    urgency: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaResolveRequest(BaseModel):
    request_id: int
    ta_name: str = Field(min_length=1, max_length=120)
    teaching_notes: str = Field(min_length=3, max_length=8000)
    student_hint: str | None = Field(default=None, max_length=2000)
    resolution_status: TaResolveStatus = "resolved"


class TaResolveResponse(BaseModel):
    request_id: int
    knowledge_entry: KnowledgeEntryOut
    message: str
