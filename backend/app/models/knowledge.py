"""
ORM and Pydantic models for the curated course knowledge base.

Entries start as pending_review when a student question is submitted.
Only professor-approved entries are searchable by the student-facing KB agent.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base

KnowledgeStatus = Literal["pending_review", "approved", "rejected"]


class KnowledgeEntry(Base):
    __tablename__ = "knowledge_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    answer_draft: Mapped[str] = mapped_column(Text, nullable=False)
    student_hint: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str] = mapped_column(Text, nullable=False, default="")
    urgency: Mapped[str | None] = mapped_column(String, nullable=True)
    difficulty: Mapped[str | None] = mapped_column(String, nullable=True)
    learning_style: Mapped[str | None] = mapped_column(String, nullable=True)
    drafter_backend: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="pending_review",
        index=True,
    )
    source_request_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    material_source: Mapped[str | None] = mapped_column(String, nullable=True)
    # Set when a TA hands the draft to curation: resolved | needs_professor.
    ta_resolution: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    professor_note: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class KnowledgeEntryOut(BaseModel):
    id: int
    question_text: str
    answer_draft: str
    student_hint: str
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    urgency: str | None = None
    difficulty: str | None = None
    learning_style: str | None = None
    drafter_backend: str | None = None
    status: KnowledgeStatus
    source_request_id: int | None = None
    cluster_id: int | None = None
    course_id: int | None = None
    material_source: str | None = None
    ta_resolution: str | None = None
    professor_note: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class CourseMaterialIngest(BaseModel):
    """Paste or export course slides/notes into the approved KB corpus."""

    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=20, max_length=100_000)
    course_id: int = Field(ge=1)
    course: str | None = None
    source: str = Field(
        default="slides",
        description="slides | notes | canvas | canvas_export | syllabus",
    )
    auto_approve: bool = True


class CourseMaterialIngestOut(BaseModel):
    title: str
    source: str
    chunks_created: int
    entry_ids: list[int]
    message: str


class CanvasSyncRequest(BaseModel):
    course_id: int = Field(ge=1)
    auto_approve: bool = True


class CanvasSyncOut(BaseModel):
    course_id: int
    canvas_course_id: str | None = None
    mode: str
    files_seen: int
    chunks_created: int
    entry_ids: list[int]
    skipped: list[str] = Field(default_factory=list)
    message: str


class EscalationItem(BaseModel):
    request_id: int
    text: str
    category: str | None
    urgency: str | None
    cluster_id: int | None
    created_at: datetime
    reason: str
    age_minutes: float
    sensitive: bool = False


class ClusterTopicOut(BaseModel):
    cluster_id: int
    title: str
    keywords: list[str] = Field(default_factory=list)
    request_count: int
    request_ids: list[int] = Field(default_factory=list)
    sample_texts: list[str] = Field(default_factory=list)
    urgency_mix: dict[str, int] = Field(default_factory=dict)
    anonymous_count: int = 0
    sensitive_count: int = 0
    suggested_action: str
    suggestion_reason: str
    category: str | None = None


class ClusterCommandCenterOut(BaseModel):
    course: str | None = None
    course_id: int | None = None
    total_requests: int
    clusters: list[ClusterTopicOut]
    escalations: list[EscalationItem] = Field(default_factory=list)
    message: str


class FaqFromClusterRequest(BaseModel):
    cluster_id: int
    course_id: int | None = None
    course: str | None = None


class KnowledgeEntryUpdate(BaseModel):
    status: KnowledgeStatus | None = None
    answer_draft: str | None = None
    student_hint: str | None = None
    professor_note: str | None = None
    tags: list[str] | None = None
    difficulty: str | None = None


class KnowledgeSearchHit(BaseModel):
    entry: KnowledgeEntryOut
    similarity: float


class AgentAskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    top_k: int = Field(default=3, ge=1, le=8)
    course_id: int | None = None


class AgentAskResponse(BaseModel):
    answer: str
    student_hint: str | None = None
    confidence: float
    matched_count: int
    sources: list[KnowledgeSearchHit]
    used_approved_kb_only: bool = True
    # True when the KB cannot help — UI should push Quiet ask / TA outreach.
    should_seek_help: bool = False


class StruggleHeatmapCell(BaseModel):
    category: str
    week_start: str
    count: int


class StruggleHeatmapOut(BaseModel):
    cells: list[StruggleHeatmapCell]
    total_requests: int
