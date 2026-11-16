"""
TA queue routes — staffing loop, dual-TA handoff, student reply, curation.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.knowledge import KnowledgeEntry
from app.models.request import WORK_STATUSES, Request
from app.models.ta import (
    HelpCoachOut,
    TaActionResponse,
    TaAssistRequest,
    TaAssistResponse,
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
from app.services.access_control import require_course_role, require_staff_anywhere
from app.services.course_ta_service import build_course_ta_load
from app.services.help_coach_service import build_help_coach, run_help_coach_assist
from app.services.knowledge_service import to_out
from app.services.ask_triage_service import ensure_default_roster
from app.services.notify_service import notify_request_owner
from app.services.pagination import clamp_page, page_or_list
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
    """Campus TA roster seed — staff only (not a student-facing surface)."""
    require_staff_anywhere(db, user)
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


@router.get("/queue/")
def list_ta_queue(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    course_id: int | None = Query(default=None),
    assignment: str | None = Query(
        default=None,
        description="desk | mine | backup | unassigned | all | in_progress",
    ),
    include_helped: bool = Query(default=False),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    if course_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="course_id is required.",
        )
    require_course_role(db, user, course_id, roles={"ta", "professor"})

    # Bound the SQL read: course-scoped, newest first, hard cap before desk filters.
    sql_cap = 500 if limit is None else min(max(limit + offset, limit or 1), 500)
    requests = (
        db.query(Request)
        .filter(Request.course_id == course_id)
        .order_by(Request.created_at.desc())
        .limit(sql_cap)
        .all()
    )
    source_ids = [row.id for row in requests]
    entries = {}
    if source_ids:
        for entry in (
            db.query(KnowledgeEntry)
            .filter(KnowledgeEntry.course_id == course_id)
            .filter(KnowledgeEntry.source_request_id.in_(source_ids))
            .all()
        ):
            entries[entry.source_request_id] = entry

    mode = (assignment or "desk").strip().lower()
    name = _ta_display(user)

    def _is_mine(request: Request, work: str) -> bool:
        assigned = (request.assigned_ta or "").strip()
        claimed = (getattr(request, "claimed_by", None) or "").strip()
        claimed_id = getattr(request, "claimed_by_user_id", None)
        return (
            assigned == name
            or claimed == name
            or claimed_id == user.id
            or (work in {"claimed", "in_progress"} and (claimed == name or claimed_id == user.id))
        )

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
        claimed_id = getattr(request, "claimed_by_user_id", None)
        unassigned = (not assigned or assigned == "Unassigned") and not claimed and not claimed_id

        if mode == "mine":
            if not _is_mine(request, work):
                continue
        elif mode == "backup":
            if backup != name:
                continue
        elif mode == "unassigned":
            if not unassigned:
                continue
        elif mode == "in_progress":
            if work != "in_progress" or not _is_mine(request, work):
                continue
        elif mode == "desk":
            if not (_is_mine(request, work) or backup == name or unassigned):
                continue

        similar_n = sum(
            1
            for peer in requests
            if peer.id != request.id
            and (
                (
                    peer.cluster_id is not None
                    and peer.cluster_id == request.cluster_id
                )
                or (
                    (peer.category or peer.triage_category)
                    and (peer.category or peer.triage_category)
                    == (request.category or request.triage_category)
                )
            )
        )
        items.append(
            TaQueueItem(
                request=to_request_out(request, db=db),
                knowledge_entry=to_out(entry) if entry else None,
                learning_style=(
                    request.learning_style
                    if request.learning_style and request.learning_style != "unknown"
                    else None
                ),
                urgency=request.urgency,
                similar_open_count=similar_n,
                help_coach=None,
            )
        )
    limit, offset = clamp_page(limit, offset)
    return page_or_list(items, limit=limit, offset=offset)


@router.get("/coach/", response_model=HelpCoachOut)
def get_help_coach(
    request_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Help Coach for one selected ask — not computed on the full queue list."""
    request = _get_request(db, request_id)
    _require_ta_for_request(db, user, request)
    entry = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_request_id == request.id)
        .order_by(KnowledgeEntry.id.desc())
        .first()
    )
    return HelpCoachOut.model_validate(
        build_help_coach(db, request, knowledge_entry=entry)
    )


@router.post("/assist/", response_model=TaAssistResponse)
def help_coach_assist(
    payload: TaAssistRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Help Coach — TA co-pilot while helping.

    Modes: draft_reply | socratic | refresh_teaching | rewrite_reply.
    Uses local Synthesizer / approved-KB RAG (no external LLM).
    """
    request = _get_request(db, payload.request_id)
    _require_ta_for_request(db, user, request)
    entry = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_request_id == request.id)
        .order_by(KnowledgeEntry.id.desc())
        .first()
    )
    result = run_help_coach_assist(
        db,
        request,
        mode=payload.mode,
        knowledge_entry=entry,
        current_reply=payload.current_reply,
        focus=payload.focus,
    )

    # Persist refreshed teaching script onto the pending KB draft when asked.
    if payload.mode == "refresh_teaching" and entry is not None:
        if result.get("teaching_approach"):
            entry.answer_draft = str(result["teaching_approach"])
        if result.get("student_hint"):
            entry.student_hint = str(result["student_hint"])
        db.add(entry)
        db.commit()
        db.refresh(entry)

    return TaAssistResponse(
        request_id=request.id,
        mode=result["mode"],
        message=result["message"],
        draft_reply=result.get("draft_reply"),
        teaching_approach=result.get("teaching_approach"),
        student_hint=result.get("student_hint"),
        socratic_steps=list(result.get("socratic_steps") or []),
        help_coach=HelpCoachOut.model_validate(result["help_coach"]),
        backend=result.get("backend"),
    )


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
    if work == "helped":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This ask was already marked helped.",
        )

    claimed_at = _utcnow()
    result = db.execute(
        update(Request)
        .where(Request.id == request.id)
        .where(Request.work_status != "helped")
        .where(
            or_(
                Request.claimed_by_user_id.is_(None),
                Request.claimed_by_user_id == user.id,
            )
        )
        .values(
            work_status="claimed",
            claimed_by=ta_name,
            claimed_by_user_id=user.id,
            claimed_at=claimed_at,
        )
    )
    if result.rowcount != 1:
        db.rollback()
        fresh = _get_request(db, payload.request_id)
        owner = (getattr(fresh, "claimed_by", None) or "another TA").strip()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Already claimed by {owner}.",
        )
    db.commit()
    request = _get_request(db, payload.request_id)
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
        {
            "request_id": request.id,
            "claimed_by": ta_name,
            "claimed_by_user_id": user.id,
            "work_status": "claimed",
            "course_id": request.course_id,
        },
    )
    await notify_request_owner(
        db,
        request,
        kind="claimed",
        title=f"A TA claimed your ask #{request.id}",
        body=f"{ta_name} claimed request #{request.id}. Check status with your request code.",
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
    claimed_id = getattr(request, "claimed_by_user_id", None)
    assigned = (request.assigned_ta or "").strip()
    backup = (request.alternative_ta or "").strip()
    if payload.status in {"in_progress", "helped"}:
        owns = claimed_id == user.id or claimed == ta_name
        if (claimed or claimed_id) and not owns and assigned != ta_name and backup != ta_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the claimed / assigned TA can update this status.",
            )
        if not claimed and not claimed_id:
            request.claimed_by = ta_name
            request.claimed_by_user_id = user.id
            request.claimed_at = _utcnow()
    elif payload.status == "open":
        owns = claimed_id == user.id or claimed == ta_name
        if (claimed or claimed_id) and not owns and assigned != ta_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the claimed TA can release this ask.",
            )
        request.claimed_by = None
        request.claimed_by_user_id = None
        request.claimed_at = None

    request.work_status = payload.status
    if payload.status == "helped":
        request.helped_at = _utcnow()
    elif payload.status == "open":
        request.helped_at = None
    db.add(request)
    db.commit()
    db.refresh(request)
    await hub.broadcast(
        "ta.work_status",
        {
            "request_id": request.id,
            "work_status": payload.status,
            "claimed_by": request.claimed_by,
            "claimed_by_user_id": getattr(request, "claimed_by_user_id", None),
            "course_id": request.course_id,
        },
    )
    label = {
        "claimed": "Claimed",
        "in_progress": "Marked in progress — helping now",
        "helped": "Marked helped — student interaction done",
        "open": "Released",
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
    request.claimed_by_user_id = user.id
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
            "course_id": request.course_id,
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
        if not getattr(request, "claimed_by_user_id", None):
            request.claimed_by_user_id = user.id
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
        {"request_id": request.id, "ta_name": ta_name, "course_id": request.course_id},
    )
    await notify_request_owner(
        db,
        request,
        kind="replied",
        title=f"A TA replied to ask #{request.id}",
        body=reply[:400],
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

    # Students must see a written reply when an ask is newly resolved.
    # Already-helped rows stay valid (legacy / idempotent resolve).
    already_helped = str(getattr(request, "work_status", None) or "open") == "helped"
    if not already_helped and not str(getattr(request, "ta_reply", None) or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Send a reply to the student before resolving this ask.",
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
        if not getattr(request, "claimed_by_user_id", None):
            request.claimed_by_user_id = user.id

    db.add(entry)
    db.add(request)
    db.commit()
    db.refresh(entry)

    out = to_out(entry)
    await hub.broadcast(
        "knowledge.updated",
        {
            "id": out.id,
            "status": out.status,
            "source_request_id": out.source_request_id,
            "course_id": request.course_id,
        },
    )
    await hub.broadcast(
        "ta.resolved",
        {
            "request_id": request.id,
            "ta_name": ta_name,
            "knowledge_entry_id": out.id,
            "resolution_status": payload.resolution_status,
            "course_id": request.course_id,
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
