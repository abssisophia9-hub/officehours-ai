"""
Routes for knowledge-base curation and the student-facing KB agent.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.knowledge import (
    AgentAskRequest,
    AgentAskResponse,
    CanvasSyncOut,
    CanvasSyncRequest,
    ClusterCommandCenterOut,
    CourseMaterialIngest,
    CourseMaterialIngestOut,
    EscalationItem,
    FaqFromClusterRequest,
    KnowledgeEntry,
    KnowledgeEntryOut,
    KnowledgeEntryUpdate,
    StruggleHeatmapOut,
)
from app.realtime.hub import hub
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role
from app.services.analytics_service import (
    build_cluster_command_center,
    build_escalation_feed,
    build_oracle_metrics,
    build_struggle_heatmap,
)
from app.services.canvas_service import canvas_status, sync_course_materials
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.knowledge_service import (
    create_faq_from_cluster,
    ingest_course_material,
    list_entries,
    to_out,
    update_entry,
)
from app.services.oracle_service import lifetime_confusion_topics

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/", response_model=list[KnowledgeEntryOut])
def list_knowledge_entries(
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if status_filter and status_filter not in {"pending_review", "approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be pending_review, approved, or rejected",
        )
    return [
        to_out(entry)
        for entry in list_entries(db, status_filter=status_filter, course_id=course_id)
    ]


@router.get("/knowledge/canvas/status")
def get_canvas_status(
    course_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course, _membership = require_course_role(
        db, user, course_id, roles={"professor", "ta"}
    )
    return canvas_status(course)


@router.get("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
def get_knowledge_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    return to_out(entry)


@router.patch("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
async def patch_knowledge_entry(
    entry_id: int,
    payload: KnowledgeEntryUpdate,
    db: Session = Depends(get_db),
):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    updated = to_out(update_entry(db, entry, payload))
    await hub.broadcast(
        "knowledge.updated",
        {
            "id": updated.id,
            "status": updated.status,
            "source_request_id": updated.source_request_id,
            "learning_style": updated.learning_style,
        },
    )
    return updated


@router.post(
    "/knowledge/from-cluster",
    response_model=KnowledgeEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def faq_from_cluster(payload: FaqFromClusterRequest, db: Session = Depends(get_db)):
    entry = create_faq_from_cluster(
        db,
        cluster_id=payload.cluster_id,
        course=payload.course,
        course_id=payload.course_id,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No requests found for that cluster",
        )
    out = to_out(entry)
    await hub.broadcast(
        "knowledge.created",
        {
            "id": out.id,
            "status": out.status,
            "source_request_id": out.source_request_id,
            "cluster_id": out.cluster_id,
        },
    )
    return out


@router.post(
    "/knowledge/materials",
    response_model=CourseMaterialIngestOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_course_materials(
    payload: CourseMaterialIngest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course, _membership = require_course_role(
        db, user, payload.course_id, roles={"professor"}
    )
    entries = ingest_course_material(
        db,
        title=payload.title.strip(),
        content=payload.content,
        source=payload.source.strip().lower() or "slides",
        course_id=course.id,
        course=payload.course or course.code,
        auto_approve=payload.auto_approve,
    )
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable content to ingest.",
        )
    for entry in entries:
        await hub.broadcast(
            "knowledge.created",
            {
                "id": entry.id,
                "status": entry.status,
                "material_source": entry.material_source,
                "course_id": entry.course_id,
            },
        )
    return CourseMaterialIngestOut(
        title=payload.title.strip(),
        source=payload.source,
        chunks_created=len(entries),
        entry_ids=[entry.id for entry in entries],
        message=(
            f"Ingested {len(entries)} material chunk(s) into {course.code} KB "
            f"({'approved' if payload.auto_approve else 'pending_review'}). "
            "Students asking in this course can now match against this content."
        ),
    )


@router.post(
    "/knowledge/canvas/sync",
    response_model=CanvasSyncOut,
    status_code=status.HTTP_201_CREATED,
)
async def sync_canvas_materials(
    payload: CanvasSyncRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course, _membership = require_course_role(
        db, user, payload.course_id, roles={"professor"}
    )
    result = sync_course_materials(
        db, course, auto_approve=payload.auto_approve
    )
    for entry_id in result["entry_ids"]:
        await hub.broadcast(
            "knowledge.created",
            {
                "id": entry_id,
                "status": "approved" if payload.auto_approve else "pending_review",
                "material_source": "canvas",
                "course_id": course.id,
            },
        )
    return CanvasSyncOut(**result)


@router.post("/agent/ask", response_model=AgentAskResponse)
def ask_kb_agent(payload: AgentAskRequest, db: Session = Depends(get_db)):
    return answer_from_knowledge_base(
        db,
        payload.question,
        top_k=payload.top_k,
        course_id=payload.course_id,
    )


@router.get("/analytics/struggle-heatmap", response_model=StruggleHeatmapOut)
def struggle_heatmap(db: Session = Depends(get_db)):
    return build_struggle_heatmap(db)


@router.get("/analytics/escalations", response_model=list[EscalationItem])
def escalations(
    course: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return build_escalation_feed(db, course=course, course_id=course_id)


@router.get("/analytics/clusters", response_model=ClusterCommandCenterOut)
def cluster_command_center(
    course: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    return build_cluster_command_center(db, course=course, course_id=course_id)


@router.get("/analytics/oracle-metrics")
def oracle_metrics(db: Session = Depends(get_db)):
    return build_oracle_metrics(db)


@router.get("/analytics/lifetime-confusion")
def lifetime_confusion(db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=25)):
    return {
        "topics": lifetime_confusion_topics(db, limit=limit),
        "message": (
            "Lifetime agent foundation: approved KB topics that confuse students "
            "most this semester. Professor curation remains the gate."
        ),
    }
