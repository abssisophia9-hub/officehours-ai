"""
TA queue routes — staffing loop, dual-TA handoff, student reply, curation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.knowledge import KnowledgeEntry
from app.models.request import WORK_STATUSES, Request
from app.models.ta import (
    TaActionResponse,
    TaClaimRequest,
    TaHandoffRequest,
    TaQueueItem,
    TaReplyRequest,
    TaResolveRequest,
    TaResolveResponse,
    TaWorkStatusRequest,
)
from app.models.ta_roster import TaRoster, TaRosterOut
from app.realtime.hub import hub
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role
from app.services.course_ta_service import build_course_ta_load
from app.services.knowledge_service import to_out
from app.services.triage_service import ensure_default_roster
from app.services.request_serializer import to_request_out

router = APIRouter(prefix="/ta", tags=["ta"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_ta_for_request(db: Session, user: User, request: Request) -> None:
    course_id = request.course_id
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request is not linked to a course.",
        )
    require_course_role(db, user, course_id, roles={"ta", "professor"})


def _get_request(db: Session, request_id: int) -> Request:
    request = db.get(Request, request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return request


def _ta_display(user: User) -> str:
    return (user.display_name or user.email or "TA").strip()


@router.get("/roster/", response_model=list[TaRosterOut])
def list_ta_roster(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    del user  # auth gate only
    return [TaRosterOut.from_orm_row(row) for row in ensure_default_roster(db)]


@router.get("/load/")
def course_ta_load(
    course_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Dual-TA load for one course — TA or professor of that course."""
    require_course_role(db, user, course_id, roles={"ta", "professor"})
    ensure_default_roster(db)
    return build_course_ta_load(db, course_id=course_id)


@router.get("/queue/", response_model=list[TaQueueItem])
def list_ta_queue(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    course_id: int | None = Query(default=None),
    course: str | None = Query(default=None),
    assignment: str | None = Query(
        default=None,
        description="mine | backup | unassigned | all | in_progress",
    ),
    include_helped: bool = Query(default=False),
):
    if course_id is None and not course:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="course_id is required.",
        )
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"ta", "professor"})

    query = db.query(Request).order_by(Request.created_at.desc())
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    elif course:
        query = query.filter(Request.course == course)
    requests = query.all()
    entries = {
        entry.source_request_id: entry
        for entry in db.query(KnowledgeEntry).all()
        if entry.source_request_id is not None
    }

    mode = (assignment or "all").strip().lower()
    name = _ta_display(user)

    items: list[TaQueueItem] = []
    for request in requests:
        entry = entries.get(request.id)
        if entry is not None and (
            entry.status in {"approved", "rejected"}
            or getattr(entry, "ta_resolution", None)
        ):
            continue

        work = str(getattr(request, "work_status", None) or "open")
        if work == "helped" and not include_helped:
            continue

        assigned = (request.assigned_ta or "").strip()
        backup = (request.alternative_ta or "").strip()
        claimed = (getattr(request, "claimed_by", None) or "").strip()

        if mode == "mine":
            if not (
                assigned == name
                or claimed == name
                or (work in {"claimed", "in_progress"} and claimed == name)
            ):
                continue
        elif mode == "backup":
            if backup != name:
                continue
        elif mode == "unassigned":
            if (assigned and assigned != "Unassigned") or claimed:
                continue
        elif mode == "in_progress":
            if work != "in_progress" or claimed != name:
                continue

        items.append(
            TaQueueItem(
                request=to_request_out(request, db=db),
                knowledge_entry=to_out(entry) if entry else None,
                learning_style=request.learning_style,
                urgency=request.urgency,
            )
        )
    return items


@router.post("/claim/", response_model=TaActionResponse)
async def claim_request(
    payload: TaClaimRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    ta_name = _ta_display(user)
    work = str(getattr(request, "work_status", None) or "open")
    claimed = (getattr(request, "claimed_by", None) or "").strip()
    if work in {"claimed", "in_progress"} and claimed and claimed != ta_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already claimed by {claimed}.",
        )
    if work == "helped":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ask was already marked helped.",
        )

    request.work_status = "claimed"
    request.claimed_by = ta_name
    request.claimed_at = _utcnow()
    # Claimer becomes primary if unassigned.
    if not (request.assigned_ta or "").strip() or request.assigned_ta == "Unassigned":
        previous_primary = (request.assigned_ta or "").strip()
        request.assigned_ta = ta_name
        if previous_primary and previous_primary not in {ta_name, "Unassigned"}:
            request.alternative_ta = previous_primary
    db.add(request)
    db.commit()
    db.refresh(request)
    await hub.broadcast(
        "ta.claimed",
        {"request_id": request.id, "claimed_by": ta_name, "work_status": "claimed"},
    )
    return TaActionResponse(
        request=to_request_out(request, db=db),
        message=f"Claimed by {ta_name}.",
    )


@router.post("/work-status/", response_model=TaActionResponse)
async def update_work_status(
    payload: TaWorkStatusRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    ta_name = _ta_display(user)
    if payload.status not in WORK_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"status must be one of: {', '.join(WORK_STATUSES)}",
        )

    claimed = (getattr(request, "claimed_by", None) or "").strip()
    assigned = (request.assigned_ta or "").strip()
    backup = (request.alternative_ta or "").strip()
    if payload.status in {"in_progress", "helped"}:
        if claimed and claimed != ta_name and assigned != ta_name and backup != ta_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the claimed / assigned TA can update this status.",
            )
        if not claimed:
            request.claimed_by = ta_name
            request.claimed_at = _utcnow()

    request.work_status = payload.status
    if payload.status == "helped":
        request.helped_at = _utcnow()
    db.add(request)
    db.commit()
    db.refresh(request)
    await hub.broadcast(
        "ta.work_status",
        {
            "request_id": request.id,
            "work_status": payload.status,
            "claimed_by": request.claimed_by,
        },
    )
    label = {
        "claimed": "Claimed",
        "in_progress": "Marked in progress — helping now",
        "helped": "Marked helped — student interaction done",
        "open": "Reopened",
    }.get(payload.status, payload.status)
    return TaActionResponse(
        request=to_request_out(request, db=db),
        message=label,
    )


@router.post("/take-backup/", response_model=TaActionResponse)
async def take_as_backup(
    payload: TaHandoffRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Backup TA becomes primary; previous primary becomes backup."""
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    ta_name = _ta_display(user)
    backup = (request.alternative_ta or "").strip()
    primary = (request.assigned_ta or "").strip()
    if backup != ta_name and primary != ta_name:
        # Allow any course TA to take unowned asks; otherwise must be backup.
        if primary and primary != "Unassigned":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the backup TA can take over this ask.",
            )

    previous = primary if primary and primary != ta_name else None
    request.assigned_ta = ta_name
    if previous:
        request.alternative_ta = previous
    request.work_status = "claimed"
    request.claimed_by = ta_name
    request.claimed_at = _utcnow()
    db.add(request)
    db.commit()
    db.refresh(request)
    await hub.broadcast(
        "ta.handoff",
        {
            "request_id": request.id,
            "assigned_ta": ta_name,
            "alternative_ta": request.alternative_ta,
        },
    )
    return TaActionResponse(
        request=to_request_out(request, db=db),
        message=f"{ta_name} took primary ownership.",
    )


@router.post("/reply/", response_model=TaActionResponse)
async def reply_to_student(
    payload: TaReplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish an async reply the student can see on request status."""
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    ta_name = _ta_display(user)
    reply = payload.reply.strip()
    request.ta_reply = reply
    request.ta_replied_at = _utcnow()
    if payload.update_student_hint:
        request.student_hint = reply
    if str(getattr(request, "work_status", None) or "open") == "open":
        request.work_status = "in_progress"
        request.claimed_by = request.claimed_by or ta_name
        request.claimed_at = request.claimed_at or _utcnow()

    entry = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_request_id == request.id)
        .order_by(KnowledgeEntry.id.desc())
        .first()
    )
    if entry is not None and payload.update_student_hint:
        entry.student_hint = reply
        db.add(entry)

    db.add(request)
    db.commit()
    db.refresh(request)
    await hub.broadcast(
        "ta.replied",
        {"request_id": request.id, "ta_name": ta_name},
    )
    return TaActionResponse(
        request=to_request_out(request, db=db),
        message="Reply published for the student (request status).",
    )


@router.post("/resolve/", response_model=TaResolveResponse)
async def resolve_for_curation(
    payload: TaResolveRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    ta_name = _ta_display(user)

    notes = payload.teaching_notes.strip()
    if len(notes) < 3:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="teaching_notes must be at least 3 characters.",
        )

    entry = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_request_id == request.id)
        .order_by(KnowledgeEntry.id.desc())
        .first()
    )
    if entry is None:
        # Create a draft so TAs aren't dead-ended.
        entry = KnowledgeEntry(
            question_text=request.text,
            answer_draft=notes,
            student_hint=(payload.student_hint or "").strip() or "See teaching notes.",
            status="pending_review",
            source_request_id=request.id,
            course_id=request.course_id,
            category=request.category,
            learning_style=request.learning_style,
            urgency=request.urgency,
        )
        db.add(entry)
        db.flush()

    note_prefix = f"[TA {ta_name}] "
    entry.answer_draft = notes
    if payload.student_hint:
        entry.student_hint = payload.student_hint.strip()
    entry.status = "pending_review"
    entry.ta_resolution = payload.resolution_status
    entry.reviewed_at = None
    existing_note = entry.professor_note or ""
    resolution_line = (
        f"{note_prefix}marked {payload.resolution_status} at {_utcnow().isoformat()}"
    )
    entry.professor_note = (
        f"{existing_note}\n{resolution_line}".strip()
        if existing_note
        else resolution_line
    )

    # Decrement load for whoever claimed / was primary.
    for candidate in {ta_name, (request.assigned_ta or "").strip()}:
        if not candidate:
            continue
        roster_row = (
            db.query(TaRoster).filter(TaRoster.name == candidate).one_or_none()
        )
        if roster_row is not None and int(roster_row.queue_depth or 0) > 0:
            roster_row.queue_depth = int(roster_row.queue_depth or 0) - 1
            db.add(roster_row)
            break

    if str(getattr(request, "work_status", None) or "open") != "helped":
        request.work_status = "helped"
        request.helped_at = _utcnow()
        request.claimed_by = request.claimed_by or ta_name

    db.add(entry)
    db.add(request)
    db.commit()
    db.refresh(entry)

    out = to_out(entry)
    await hub.broadcast(
        "knowledge.updated",
        {"id": out.id, "status": out.status, "source_request_id": out.source_request_id},
    )
    await hub.broadcast(
        "ta.resolved",
        {
            "request_id": request.id,
            "ta_name": ta_name,
            "knowledge_entry_id": out.id,
            "resolution_status": payload.resolution_status,
        },
    )

    return TaResolveResponse(
        request_id=request.id,
        knowledge_entry=out,
        message=(
            "Helped + saved to professor curation as pending_review. "
            "It will not reach the student KB agent until approved."
        ),
    )
