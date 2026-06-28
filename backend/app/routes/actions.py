"""
Routes for professor recommendation decisions and generated action plans.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.action import (
    RecommendationDecision,
    RecommendationDecisionCreate,
    RecommendationDecisionOut,
)
from app.models.request import Request
from app.services.action_orchestration_service import build_action_plan

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post(
    "/recommendations/",
    response_model=RecommendationDecisionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_recommendation_decision(
    payload: RecommendationDecisionCreate,
    db: Session = Depends(get_db),
):
    related_requests = _get_related_requests(db, payload.request_ids)
    action_plan = build_action_plan(payload, related_requests)

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

    return _to_out(decision)


@router.get("/recommendations/", response_model=list[RecommendationDecisionOut])
def list_recommendation_decisions(db: Session = Depends(get_db)):
    decisions = db.query(RecommendationDecision).order_by(RecommendationDecision.id).all()
    return [_to_out(decision) for decision in decisions]


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
