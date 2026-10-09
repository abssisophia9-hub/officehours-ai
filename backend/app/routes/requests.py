"""
Routes for submitting and retrieving student requests.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.ai.clustering import assign_cluster_id
from app.database.session import get_db
from app.models.auth import User
from app.routes.auth import get_current_user
from app.services.access_control import (
    require_course_member,
    require_course_role,
    require_staff_anywhere,
    user_course_ids,
    user_staff_course_ids,
)
from app.models.action import RecommendationDecision
from app.models.request import (
    HELP_MODES,
    Request,
    RequestCreate,
    RequestOut,
    RequestStatusOut,
)
from app.realtime.hub import hub
from app.services.analytics_service import is_sensitive_category
from app.services.knowledge_service import create_pending_entry_from_request
from app.services.ask_triage_service import (
    apply_triage_to_request,
    build_triage_public_payload,
    run_ask_triage_pipeline,
)
from app.services.pagination import clamp_page
from app.services.request_serializer import to_request_out
from app.services.request_status_service import build_request_status
from app.services.study_buddy_service import (
    StudyBuddyOptInCreate,
    StudyBuddyStatusOut,
    get_study_buddy_status,
    opt_in_study_buddy,
)

router = APIRouter(prefix="/requests", tags=["requests"])

HELP_MODE_ACTIONS = {
    "face_to_face": (
        "Schedule or offer a face-to-face office-hours meeting "
        "(campus location / walk-in slot)."
    ),
    "online_meeting": (
        "Offer an online meeting (Zoom / Teams) — share a link and time window."
    ),
}


@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if payload.course_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="course_id is required.",
        )
    require_course_member(db, user, payload.course_id)
    request_data = payload.model_dump()

    help_mode = str(request_data.get("help_mode") or "message").strip().lower()
    if help_mode not in HELP_MODES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"help_mode must be one of: {', '.join(HELP_MODES)}",
        )
    request_data["help_mode"] = help_mode

    # Quiet / low-exposure asks never persist identity even if the client sent it.
    if request_data.get("anonymous"):
        request_data["student_id"] = None
        request_data["student_name"] = None
    else:
        # Identified asks should carry a name (and ideally a student ID).
        name = (request_data.get("student_name") or "").strip() or None
        sid = (request_data.get("student_id") or "").strip() or None
        if not name and not sid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Identified asks require student_name or student_id. "
                    "Use Quiet ask (anonymous) if you prefer not to share identity."
                ),
            )
        request_data["student_name"] = name
        request_data["student_id"] = sid

    triage = run_ask_triage_pipeline(
        db,
        question_text=payload.text,
        code_snippet=payload.code_snippet,
        course=payload.course,
        course_id=payload.course_id,
        learning_style=payload.learning_style,
    )
    classification = triage["classification"]
    analyzer = triage["analyzer"]
    synthesizer = triage["synthesizer"]

    if not request_data.get("category"):
        request_data["category"] = classification.get("category") or analyzer.get(
            "category"
        )
    if not request_data.get("urgency"):
        request_data["urgency"] = classification.get("urgency") or analyzer.get(
            "urgency"
        )
    if not request_data.get("learning_style"):
        request_data["learning_style"] = classification.get("learning_style")
    if not request_data.get("recommended_action"):
        request_data["recommended_action"] = classification.get("recommended_action")

    # Meeting preference overrides the default action when student asked for a meeting.
    if help_mode in {"face_to_face", "online_meeting"}:
        request_data["recommended_action"] = HELP_MODE_ACTIONS[help_mode]

    category = request_data.get("category")
    sensitive = bool(request_data.get("sensitive")) or is_sensitive_category(category)
    request_data["sensitive"] = sensitive
    if sensitive:
        request_data["recommended_action"] = (
            "Private 1:1 / admin route — do not discuss in a public group review"
        )
        if help_mode == "face_to_face":
            request_data["recommended_action"] = (
                "Private face-to-face follow-up — do not discuss in a public group review"
            )
        elif help_mode == "online_meeting":
            request_data["recommended_action"] = (
                "Private online 1:1 follow-up — do not discuss in a public group review"
            )

    if request_data.get("cluster_id") is None:
        existing_query = db.query(Request).order_by(Request.id)
        if payload.course_id is not None:
            existing_query = existing_query.filter(Request.course_id == payload.course_id)
        elif payload.course:
            existing_query = existing_query.filter(Request.course == payload.course)
        existing_requests = existing_query.all()
        request_data["cluster_id"] = assign_cluster_id(payload.text, existing_requests)

    db_request = Request(**request_data)
    db_request.created_by_user_id = user.id
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    db_request = apply_triage_to_request(db, db_request, triage)

    # Ask Triage classification can overwrite recommended_action; keep meeting preference.
    if help_mode in {"face_to_face", "online_meeting"}:
        if db_request.sensitive:
            if help_mode == "face_to_face":
                db_request.recommended_action = (
                    "Private face-to-face follow-up — do not discuss in a public group review"
                )
            else:
                db_request.recommended_action = (
                    "Private online 1:1 follow-up — do not discuss in a public group review"
                )
        else:
            db_request.recommended_action = HELP_MODE_ACTIONS[help_mode]
        db.add(db_request)
        db.commit()
        db.refresh(db_request)

    entry = create_pending_entry_from_request(
        db,
        db_request,
        urgency=str(db_request.urgency or ""),
        matched_keywords=list(analyzer.get("tags") or classification.get("matched_keywords") or []),
        learning_style=str(db_request.learning_style or "unknown"),
    )
    # Prefer Ask Triage Synthesizer outputs for TA teaching roadmap + student hint.
    entry.answer_draft = str(synthesizer.get("teaching_approach") or entry.answer_draft)
    entry.student_hint = str(synthesizer.get("student_hint") or entry.student_hint)
    entry.difficulty = str(
        (analyzer.get("difficulty") or entry.difficulty or "MEDIUM")
    ).lower()
    if analyzer.get("category"):
        entry.category = str(analyzer["category"])
    entry.drafter_backend = str(synthesizer.get("backend") or entry.drafter_backend)
    db.add(entry)
    db.commit()
    db.refresh(entry)

    public_triage = build_triage_public_payload(triage)

    for step in public_triage.get("steps") or []:
        await hub.broadcast(
            f"triage.{step['agent']}.done",
            {
                "request_id": db_request.id,
                "elapsed_ms": step["elapsed_ms"],
                "agent": step["agent"],
                "course_id": db_request.course_id,
            },
        )

    await hub.broadcast(
        "request.created",
        {
            "id": db_request.id,
            "category": db_request.category,
            "urgency": db_request.urgency,
            "learning_style": db_request.learning_style,
            "cluster_id": db_request.cluster_id,
            "assigned_ta": db_request.assigned_ta,
            "triage_category": db_request.triage_category,
            "course_id": db_request.course_id,
        },
    )
    await hub.broadcast(
        "knowledge.created",
        {
            "id": entry.id,
            "status": entry.status,
            "source_request_id": entry.source_request_id,
            "learning_style": entry.learning_style,
            "drafter_backend": entry.drafter_backend,
            "course_id": db_request.course_id,
        },
    )
    if (db_request.urgency or "").lower() in {"urgent", "high"} or db_request.sensitive:
        reason = (
            "Sensitive / private follow-up needed"
            if db_request.sensitive
            else f"Marked {db_request.urgency} urgency"
        )
        await hub.broadcast(
            "escalation",
            {
                "request_id": db_request.id,
                "urgency": db_request.urgency,
                "category": db_request.category,
                "sensitive": bool(db_request.sensitive),
                "reason": reason,
                "course_id": db_request.course_id,
            },
        )

    return to_request_out(db_request, triage=public_triage, db=db)


def _is_request_owner(user: User, db_request: Request) -> bool:
    return getattr(db_request, "created_by_user_id", None) == user.id


def _is_staff_on_request(db: Session, user: User, db_request: Request) -> bool:
    if db_request.course_id is None:
        return False
    try:
        require_course_role(db, user, db_request.course_id, roles={"ta", "professor"})
    except HTTPException:
        return False
    return True


def _require_request_access(db: Session, user: User, db_request: Request) -> None:
    """Full request body: staff on that course, or the student who submitted it."""
    if _is_request_owner(user, db_request) or _is_staff_on_request(db, user, db_request):
        return
    if db_request.course_id is None:
        require_staff_anywhere(db, user)
        return
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Request not found",
    )


def _require_status_access(db: Session, user: User, db_request: Request) -> None:
    """Request-code receipt: any course member can look up status, not the full row."""
    if db_request.course_id is None:
        require_staff_anywhere(db, user)
        return
    require_course_member(db, user, db_request.course_id)


@router.get("/")
def list_requests(
    course_id: int | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Request)
    if course_id is not None:
        _course, membership = require_course_member(db, user, course_id)
        query = query.filter(Request.course_id == course_id)
        if membership.role == "student":
            query = query.filter(Request.created_by_user_id == user.id)
    else:
        staff_ids = user_staff_course_ids(db, user)
        student_ids = [
            cid for cid in user_course_ids(db, user) if cid not in set(staff_ids)
        ]
        clauses = []
        if staff_ids:
            clauses.append(Request.course_id.in_(staff_ids))
        if student_ids:
            clauses.append(
                and_(
                    Request.course_id.in_(student_ids),
                    Request.created_by_user_id == user.id,
                )
            )
        if not clauses:
            return []
        query = query.filter(or_(*clauses))
    query = query.order_by(Request.id)
    limit, offset = clamp_page(limit, offset)
    if limit is None:
        rows = [to_request_out(item, db=db) for item in query.all()]
        return rows
    total = query.count()
    chunk = query.offset(offset).limit(limit).all()
    rows = [to_request_out(item, db=db) for item in chunk]
    return {
        "items": rows,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(rows) < total,
    }


@router.get("/{request_id}/status", response_model=RequestStatusOut)
def get_request_status(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    _require_status_access(db, user, db_request)

    # Avoid loading every decision campus-wide — match this request id only.
    marker = str(request_id)
    candidates = (
        db.query(RecommendationDecision)
        .filter(RecommendationDecision.request_ids.contains(marker))
        .order_by(RecommendationDecision.id)
        .all()
    )
    decisions = []
    for decision in candidates:
        try:
            ids = json.loads(decision.request_ids or "[]")
        except json.JSONDecodeError:
            ids = []
        if request_id in ids or str(request_id) in {str(x) for x in ids}:
            decisions.append(decision)
    return build_request_status(db_request, decisions)


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    _require_request_access(db, user, db_request)
    return to_request_out(db_request, db=db)


@router.get("/{request_id}/study-buddy", response_model=StudyBuddyStatusOut)
def study_buddy_status(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    _require_request_access(db, user, db_request)
    return get_study_buddy_status(db, db_request)


@router.post("/{request_id}/study-buddy", response_model=StudyBuddyStatusOut)
def study_buddy_opt_in(
    request_id: int,
    payload: StudyBuddyOptInCreate | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    _require_request_access(db, user, db_request)
    label = payload.display_label if payload else None
    return opt_in_study_buddy(db, db_request, display_label=label)
