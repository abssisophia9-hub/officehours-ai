"""
Routes for professor recommendation decisions and generated action plans.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role, require_staff_anywhere
from app.models.action import (
    RecommendationDecision,
    RecommendationDecisionCreate,
    RecommendationDecisionOut,
)
from app.models.office_hours import OfficeHoursWindow
from app.models.request import Request
from app.realtime.hub import hub
from app.services.action_orchestration_service import build_action_plan
from app.services.ics_calendar_service import (
    build_ics_calendar,
    ics_export_available,
    pick_office_hours_window,
)

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post(
    "/recommendations/",
    response_model=RecommendationDecisionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_recommendation_decision(
    payload: RecommendationDecisionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    related_requests = _get_related_requests(db, payload.request_ids)
    course_ids = {req.course_id for req in related_requests if req.course_id}
    if not course_ids:
        require_staff_anywhere(db, user)
    for cid in course_ids:
        require_course_role(db, user, cid, roles={"professor", "ta"})
    office_hours = db.query(OfficeHoursWindow).all()
    action_plan = build_action_plan(payload, related_requests, office_hours)

    decision = RecommendationDecision(
        card_id=payload.card_id,
        action_kind=payload.action_kind,
        action_title=payload.action_title,
        status=payload.status,
        cluster_id=payload.cluster_id,
        professor_note=payload.professor_note,
        request_ids=json.dumps(payload.request_ids),
        action_plan=json.dumps(action_plan),
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)

    meeting = action_plan.get("meeting") if isinstance(action_plan, dict) else None
    if (
        payload.status == "approved"
        and payload.action_kind == "group_session"
        and isinstance(meeting, dict)
    ):
        await hub.broadcast(
            "group.meeting.scheduled",
            {
                "decision_id": decision.id,
                "cluster_id": payload.cluster_id,
                "request_ids": payload.request_ids,
                "meeting": meeting,
                "title": action_plan.get("title"),
                "course_id": next(iter(course_ids), None),
            },
        )

    return _to_out(decision)


@router.get("/recommendations/", response_model=list[RecommendationDecisionOut])
def list_recommendation_decisions(
    course_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List decisions. When course_id is set, only decisions whose requests are in that course."""
    if course_id is not None:
        require_course_role(db, user, course_id, roles={"professor", "ta"})
        course_request_ids = {
            row.id
            for row in db.query(Request.id).filter(Request.course_id == course_id).all()
        }
        decisions = db.query(RecommendationDecision).order_by(RecommendationDecision.id).all()
        scoped = []
        for decision in decisions:
            try:
                ids = set(json.loads(decision.request_ids or "[]"))
            except json.JSONDecodeError:
                ids = set()
            if ids & course_request_ids:
                scoped.append(decision)
        return [_to_out(decision) for decision in scoped]

    staff_ids = require_staff_anywhere(db, user)
    course_request_ids = {
        row.id
        for row in db.query(Request.id).filter(Request.course_id.in_(staff_ids)).all()
    }
    decisions = db.query(RecommendationDecision).order_by(RecommendationDecision.id).all()
    scoped = []
    for decision in decisions:
        try:
            ids = set(json.loads(decision.request_ids or "[]"))
        except json.JSONDecodeError:
            ids = set()
        if ids & course_request_ids:
            scoped.append(decision)
    return [_to_out(decision) for decision in scoped]


@router.get("/recommendations/{decision_id}/calendar.ics")
def export_recommendation_calendar(
    decision_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_staff_anywhere(db, user)
    decision = db.get(RecommendationDecision, decision_id)
    if decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation decision not found",
        )

    if not ics_export_available(decision):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This decision does not support calendar export.",
        )

    window = pick_office_hours_window(db.query(OfficeHoursWindow).all())
    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No office-hour windows are configured for calendar export.",
        )

    action_plan = json.loads(decision.action_plan)
    ics_content = build_ics_calendar(decision, action_plan, window)
    filename = f"officehours-action-{decision_id}.ics"

    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _get_related_requests(db: Session, request_ids: list[int]) -> list[Request]:
    if not request_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one request ID is required.",
        )

    requests = db.query(Request).filter(Request.id.in_(request_ids)).all()
    found_ids = {request.id for request in requests}
    missing_ids = sorted(set(request_ids) - found_ids)
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request IDs not found: {missing_ids}",
        )

    return requests


def _to_out(decision: RecommendationDecision) -> RecommendationDecisionOut:
    return RecommendationDecisionOut(
        id=decision.id,
        card_id=decision.card_id,
        action_kind=decision.action_kind,
        action_title=decision.action_title,
        status=decision.status,
        cluster_id=decision.cluster_id,
        professor_note=decision.professor_note,
        request_ids=json.loads(decision.request_ids),
        action_plan=json.loads(decision.action_plan),
        created_at=decision.created_at,
        updated_at=decision.updated_at,
    )
