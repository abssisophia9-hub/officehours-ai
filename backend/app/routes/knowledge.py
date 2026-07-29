"""
Routes for knowledge-base curation and the student-facing KB agent.
"""

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.agent_metrics import (
    GoldLabelCreate,
    GoldLabelOut,
    KbHitRateReport,
)
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
from app.services.agent_metrics_service import (
    build_kb_hit_rate_report,
    create_gold_label,
    list_gold_labels,
    record_kb_ask_event,
)
from app.services.analytics_service import (
    build_cluster_command_center,
    build_escalation_feed,
    build_oracle_metrics,
    build_struggle_heatmap,
)
from app.services.canvas_service import canvas_status, sync_course_materials
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.material_extract import extract_material_text
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
    return canvas_status(db, course)


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
    "/knowledge/materials/upload",
    response_model=CourseMaterialIngestOut,
    status_code=status.HTTP_201_CREATED,
)
async def upload_course_material_file(
    course_id: int = Form(...),
    title: str | None = Form(default=None),
    auto_approve: bool = Form(default=True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload PDF slides, DOCX/TXT/MD notes, or a video transcript (.vtt/.srt)."""
    course, _membership = require_course_role(
        db, user, course_id, roles={"professor"}
    )
    data = await file.read()
    if len(data) > 20_000_000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (20 MB max).",
        )
    try:
        content, material_source = extract_material_text(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    material_title = (title or "").strip() or (file.filename or "Uploaded material")
    entries = ingest_course_material(
        db,
        title=material_title,
        content=content,
        source=material_source,
        course_id=course.id,
        course=course.code,
        auto_approve=auto_approve,
    )
    if not entries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No usable text could be extracted from that file.",
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
        title=material_title,
        source=material_source,
        chunks_created=len(entries),
        entry_ids=[entry.id for entry in entries],
        message=(
            f"Extracted {file.filename} ({material_source}) into {len(entries)} "
            f"KB chunk(s) for {course.code} — the course agent can use it "
            f"{'now' if auto_approve else 'after your approval'}."
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
    response = answer_from_knowledge_base(
        db,
        payload.question,
        top_k=payload.top_k,
        course_id=payload.course_id,
    )
    record_kb_ask_event(
        db,
        question=payload.question,
        course_id=payload.course_id,
        response=response,
    )
    return response


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


@router.get("/analytics/kb-hit-rate", response_model=KbHitRateReport)
def kb_hit_rate(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    """Per-course KB agent hit-rate (hit = answered from approved materials)."""
    return build_kb_hit_rate_report(db, course_id=course_id)


@router.post(
    "/analytics/gold-labels",
    response_model=GoldLabelOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_gold_label(payload: GoldLabelCreate, db: Session = Depends(get_db)):
    """Store a human gold judgment for Analyzer / Matcher evaluation."""
    return create_gold_label(db, payload)


@router.get("/analytics/gold-labels", response_model=list[GoldLabelOut])
def get_gold_labels(
    department: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    return list_gold_labels(db, department=department, limit=limit)


@router.get("/analytics/lifetime-confusion")
def lifetime_confusion(db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=25)):
    return {
        "topics": lifetime_confusion_topics(db, limit=limit),
        "message": (
            "Lifetime agent foundation: approved KB topics that confuse students "
            "most this semester. Professor curation remains the gate."
        ),
    }
