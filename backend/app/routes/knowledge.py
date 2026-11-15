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
from app.models.help_room import InsightFaqRequest, ReviewInsightsOut, ReviewTopicNoteUpdate
from app.models.knowledge import (
    AgentAskRequest,
    AgentAskResponse,
    CanvasSyncOut,
    CanvasSyncRequest,
    ClusterCommandCenterOut,
    CourseMaterialIngest,
    CourseMaterialIngestOut,
    MaterialUploadApproveOut,
    MaterialUploadOut,
    MaterialUploadRejectOut,
    EscalationItem,
    FaqFromClusterRequest,
    KnowledgeEntry,
    KnowledgeEntryOut,
    KnowledgeEntryUpdate,
    StruggleHeatmapOut,
)
from app.realtime.hub import hub
from app.routes.auth import get_current_user
from app.services.access_control import (
    require_course_member,
    require_course_role,
    require_staff_anywhere,
    user_course_ids,
    user_staff_course_ids,
)
from app.services.agent_metrics_service import (
    build_kb_hit_rate_report,
    create_gold_label,
    list_gold_labels,
    record_kb_ask_event,
)
from app.services.analytics_service import (
    build_cluster_command_center,
    build_escalation_feed,
    build_triage_metrics,
    build_review_insights,
    build_struggle_heatmap,
    upsert_review_topic_note,
)
from app.services.canvas_service import canvas_status, sync_course_materials
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.material_extract import extract_material_pages
from app.services.demo_mode import demo_mode
from app.services.knowledge_service import (
    approve_upload,
    list_course_uploads,
    reject_upload,
    create_faq_from_cluster,
    create_faq_from_insight,
    ingest_course_material,
    list_entries,
    list_upload_entries,
    to_out,
    update_entry,
)
from app.services.ask_triage_service import lifetime_confusion_topics
from app.services.pagination import clamp_page, page_or_list
from app.services.retrain_service import run_retrain

router = APIRouter(tags=["knowledge"])


def _reject_auto_approve_outside_demo(auto_approve: bool) -> None:
    """Normal deploys must not skip the professor stamp.

    ``auto_approve`` stays available for local demo and the existing test
    suite, both of which set ``OFFICEHOURS_DEMO``.
    """
    if auto_approve and not demo_mode():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "auto_approve is only available when OFFICEHOURS_DEMO is on. "
                "Leave the upload pending and approve it after review."
            ),
        )


@router.get("/knowledge/")
def list_knowledge_entries(
    status_filter: str | None = Query(default=None, alias="status"),
    course_id: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if status_filter and status_filter not in {"pending_review", "approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be pending_review, approved, or rejected",
        )
    if course_id is not None:
        course, membership = require_course_member(db, user, course_id)
        del course
        if status_filter in {None, "pending_review", "rejected"} and membership.role == "student":
            if status_filter in {"pending_review", "rejected"}:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Students can only list approved knowledge.",
                )
            status_filter = "approved"
        rows = [
            to_out(entry)
            for entry in list_entries(db, status_filter=status_filter, course_id=course_id)
        ]
        limit, offset = clamp_page(limit, offset)
        return page_or_list(rows, limit=limit, offset=offset)

    allowed = user_course_ids(db, user)
    staff_ids = set(user_staff_course_ids(db, user))
    entries = []
    for cid in allowed:
        want = status_filter
        if cid not in staff_ids:
            if status_filter in {"pending_review", "rejected"}:
                continue
            want = "approved"
        entries.extend(list_entries(db, status_filter=want, course_id=cid))
    rows = [to_out(entry) for entry in entries]
    limit, offset = clamp_page(limit, offset)
    return page_or_list(rows, limit=limit, offset=offset)


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


@router.get("/knowledge/uploads", response_model=list[MaterialUploadOut])
def list_material_uploads(
    course_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Professor view of files uploaded to one course, grouped by upload."""
    require_course_role(db, user, course_id, roles={"professor"})
    return list_course_uploads(db, course_id)


@router.get("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
def get_knowledge_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    if entry.course_id is None:
        require_staff_anywhere(db, user)
    elif entry.status == "approved":
        require_course_member(db, user, entry.course_id)
    else:
        require_course_role(db, user, entry.course_id, roles={"professor", "ta"})
    return to_out(entry)


@router.patch("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
async def patch_knowledge_entry(
    entry_id: int,
    payload: KnowledgeEntryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    if entry.course_id is None:
        require_staff_anywhere(db, user)
    else:
        require_course_role(db, user, entry.course_id, roles={"professor"})
    updated = to_out(update_entry(db, entry, payload))
    await hub.broadcast(
        "knowledge.updated",
        {
            "id": updated.id,
            "status": updated.status,
            "source_request_id": updated.source_request_id,
            "learning_style": updated.learning_style,
            "course_id": updated.course_id,
        },
    )
    return updated


@router.post(
    "/knowledge/from-cluster",
    response_model=KnowledgeEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def faq_from_cluster(
    payload: FaqFromClusterRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.course_id is not None:
        require_course_role(db, user, payload.course_id, roles={"professor"})
    else:
        require_staff_anywhere(db, user)
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
            "course_id": out.course_id,
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
    _reject_auto_approve_outside_demo(payload.auto_approve)
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
        upload_id=entries[0].upload_id,
        message=(
            f"Saved {len(entries)} {'part' if len(entries) == 1 else 'parts'} of "
            f"“{payload.title.strip()}” as course material for {course.code}. "
            + (
                "Students can see it now."
                if payload.auto_approve
                else "Students can't see it until you approve it."
            )
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
    auto_approve: bool = Form(default=False),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload PDF slides, DOCX/TXT/MD notes, or a video transcript (.vtt/.srt)."""
    course, _membership = require_course_role(
        db, user, course_id, roles={"professor"}
    )
    _reject_auto_approve_outside_demo(auto_approve)
    data = await file.read()
    if len(data) > 20_000_000:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large (20 MB max).",
        )
    try:
        pages, material_source = extract_material_pages(file.filename or "", data)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    material_title = (title or "").strip() or (file.filename or "Uploaded material")
    entries = ingest_course_material(
        db,
        title=material_title,
        content="\n\n".join(page.text for page in pages),
        source=material_source,
        course_id=course.id,
        course=course.code,
        auto_approve=auto_approve,
        filename=file.filename or material_title,
        pages=[(page.page_number, page.text) for page in pages],
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
        upload_id=entries[0].upload_id,
        message=(
            f"Extracted {file.filename} ({material_source}) into {len(entries)} "
            f"KB chunk(s) for {course.code} - the course agent can use it "
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
    _reject_auto_approve_outside_demo(payload.auto_approve)
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


@router.post(
    "/knowledge/uploads/{upload_id}/approve",
    response_model=MaterialUploadApproveOut,
)
async def approve_material_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Professor stamp for every chunk created by one material upload."""
    pending = list_upload_entries(db, upload_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    course_ids = {entry.course_id for entry in pending}
    if len(course_ids) != 1 or None in course_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not tied to a single course",
        )
    course_id = next(iter(course_ids))
    require_course_role(db, user, course_id, roles={"professor"})
    updated = approve_upload(db, upload_id)
    for entry in updated:
        await hub.broadcast(
            "knowledge.updated",
            {
                "id": entry.id,
                "status": entry.status,
                "course_id": entry.course_id,
                "upload_id": entry.upload_id,
            },
        )
    return MaterialUploadApproveOut(
        upload_id=upload_id,
        course_id=course_id,
        approved_count=len(updated),
    )


@router.post(
    "/knowledge/uploads/{upload_id}/reject",
    response_model=MaterialUploadRejectOut,
)
async def reject_material_upload(
    upload_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Professor rejection for every chunk created by one material upload."""
    pending = list_upload_entries(db, upload_id)
    if not pending:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )
    course_ids = {entry.course_id for entry in pending}
    if len(course_ids) != 1 or None in course_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload is not tied to a single course",
        )
    course_id = next(iter(course_ids))
    require_course_role(db, user, course_id, roles={"professor"})
    updated = reject_upload(db, upload_id)
    for entry in updated:
        await hub.broadcast(
            "knowledge.updated",
            {
                "id": entry.id,
                "status": entry.status,
                "course_id": entry.course_id,
                "upload_id": entry.upload_id,
            },
        )
    return MaterialUploadRejectOut(
        upload_id=upload_id,
        course_id=course_id,
        rejected_count=len(updated),
    )


@router.post("/agent/ask", response_model=AgentAskResponse)
def ask_kb_agent(
    payload: AgentAskRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_course_member(db, user, payload.course_id)
    response = answer_from_knowledge_base(
        db,
        payload.question,
        top_k=payload.top_k,
        course_id=payload.course_id,
        user_id=user.id,
    )
    record_kb_ask_event(
        db,
        question=payload.question,
        course_id=payload.course_id,
        response=response,
    )
    return response


@router.get("/analytics/struggle-heatmap", response_model=StruggleHeatmapOut)
def struggle_heatmap(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    allowed = require_staff_anywhere(db, user)
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        return build_struggle_heatmap(db, course_ids=[course_id])
    return build_struggle_heatmap(db, course_ids=allowed)


@router.get("/analytics/escalations", response_model=list[EscalationItem])
def escalations(
    course: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        return build_escalation_feed(db, course=course, course_id=course_id)
    allowed = require_staff_anywhere(db, user)
    return build_escalation_feed(db, course=course, course_ids=allowed)


@router.get("/analytics/clusters", response_model=ClusterCommandCenterOut)
def cluster_command_center(
    course: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        return build_cluster_command_center(db, course=course, course_id=course_id)
    allowed = require_staff_anywhere(db, user)
    return build_cluster_command_center(db, course=course, course_ids=allowed)


@router.get("/analytics/triage-metrics")
def triage_metrics(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        return build_triage_metrics(db, course_ids=[course_id])
    allowed = require_staff_anywhere(db, user)
    return build_triage_metrics(db, course_ids=allowed)


@router.get("/analytics/kb-hit-rate", response_model=KbHitRateReport)
def kb_hit_rate(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Per-course KB agent hit-rate (hit = answered from approved materials)."""
    if course_id is not None:
        require_course_member(db, user, course_id)
        return build_kb_hit_rate_report(db, course_id=course_id)
    allowed = require_staff_anywhere(db, user)
    return build_kb_hit_rate_report(db, course_ids=allowed)


@router.post(
    "/analytics/gold-labels",
    response_model=GoldLabelOut,
    status_code=status.HTTP_201_CREATED,
)
def submit_gold_label(
    payload: GoldLabelCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Store a human gold judgment for Analyzer / Matcher evaluation."""
    if payload.course_id is not None:
        require_course_role(db, user, payload.course_id, roles={"ta", "professor"})
    else:
        require_staff_anywhere(db, user)
    if not payload.labeled_by:
        payload.labeled_by = user.email
    return create_gold_label(db, payload)


@router.get("/analytics/gold-labels", response_model=list[GoldLabelOut])
def get_gold_labels(
    department: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=1000),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"ta", "professor"})
        return list_gold_labels(
            db, department=department, course_id=course_id, limit=limit
        )
    allowed = require_staff_anywhere(db, user)
    return list_gold_labels(
        db, department=department, course_ids=allowed, limit=limit
    )


@router.post("/analytics/retrain")
def retrain_from_gold(
    course_id: int | None = Query(default=None),
    apply_models: bool = Query(default=False),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Evaluate gold labels. Rewrite Analyzer joblib only if ALLOW_RETRAIN + apply."""
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor"})
    else:
        require_staff_anywhere(db, user)
    return run_retrain(db, course_id=course_id, apply_models=apply_models)


@router.get("/analytics/lifetime-confusion")
def lifetime_confusion(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    course_id: int | None = Query(default=None),
    limit: int = Query(default=8, ge=1, le=25),
):
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        scoped = [course_id]
    else:
        scoped = require_staff_anywhere(db, user)
    return {
        "topics": lifetime_confusion_topics(db, limit=limit, course_ids=scoped),
        "message": (
            "Lifetime agent foundation: approved KB topics that confuse students "
            "most this semester. Professor curation remains the gate."
        ),
    }


@router.get("/analytics/review-insights", response_model=ReviewInsightsOut)
def review_insights(
    course_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Professor chapter/topic review board from Quiet asks + Stuck Room posts."""
    require_course_role(db, user, course_id, roles={"professor"})
    return build_review_insights(db, course_id=course_id)


@router.patch("/analytics/review-insights", response_model=ReviewInsightsOut)
def update_review_insight_note(
    payload: ReviewTopicNoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_course_role(db, user, payload.course_id, roles={"professor"})
    upsert_review_topic_note(
        db,
        course_id=payload.course_id,
        topic_key=payload.topic_key,
        review_status=payload.review_status,
        next_cohort_note=payload.next_cohort_note,
    )
    return build_review_insights(db, course_id=payload.course_id)


@router.post(
    "/knowledge/from-insight",
    response_model=KnowledgeEntryOut,
    status_code=status.HTTP_201_CREATED,
)
async def faq_from_insight(
    payload: InsightFaqRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_course_role(db, user, payload.course_id, roles={"professor"})
    entry = create_faq_from_insight(
        db,
        course_id=payload.course_id,
        topic_key=payload.topic_key,
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No questions found for that review topic.",
        )
    out = to_out(entry)
    await hub.broadcast(
        "knowledge.created",
        {
            "id": out.id,
            "status": out.status,
            "source_request_id": out.source_request_id,
            "cluster_id": out.cluster_id,
            "course_id": out.course_id,
        },
    )
    return out
