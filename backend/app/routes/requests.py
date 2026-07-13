"""
Routes for submitting and retrieving student requests.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.clustering import assign_cluster_id
from app.database.session import get_db
from app.models.action import RecommendationDecision
from app.models.followup import FollowUpCreate, FollowUpOut
from app.models.request import Request, RequestCreate, RequestOut, RequestStatusOut
from app.realtime.hub import hub
from app.services.followup_service import create_followup, list_followups, load_followups
from app.services.knowledge_service import create_pending_entry_from_request
from app.services.oracle_service import (
    apply_oracle_to_request,
    build_oracle_public_payload,
    run_oracle_pipeline,
)
from app.services.request_serializer import to_request_out
from app.services.request_status_service import build_request_status

router = APIRouter(prefix="/requests", tags=["requests"])


def _request_out(db, request: Request, oracle: dict | None = None) -> RequestOut:
    return to_request_out(
        request,
        oracle=oracle,
        followups=load_followups(db, request.id),
    )



@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    request_data = payload.model_dump()

    oracle = run_oracle_pipeline(
        db,
        question_text=payload.text,
        code_snippet=payload.code_snippet,
        course=payload.course,
        learning_style=payload.learning_style,
    )
    classification = oracle["classification"]
    analyzer = oracle["analyzer"]
    synthesizer = oracle["synthesizer"]

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
    if request_data.get("cluster_id") is None:
        existing_requests = db.query(Request).order_by(Request.id).all()
        request_data["cluster_id"] = assign_cluster_id(payload.text, existing_requests)

    db_request = Request(**request_data)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    db_request = apply_oracle_to_request(db, db_request, oracle)

    entry = create_pending_entry_from_request(
        db,
        db_request,
        urgency=str(db_request.urgency or ""),
        matched_keywords=list(analyzer.get("tags") or classification.get("matched_keywords") or []),
        learning_style=str(db_request.learning_style or "unknown"),
    )
    # Prefer Oracle Synthesizer outputs for TA teaching roadmap + student hint.
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

    public_oracle = build_oracle_public_payload(oracle)

    for step in public_oracle.get("steps") or []:
        await hub.broadcast(
            f"oracle.{step['agent']}.done",
            {
                "request_id": db_request.id,
                "elapsed_ms": step["elapsed_ms"],
                "agent": step["agent"],
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
            "oracle_category": db_request.oracle_category,
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
        },
    )
    if (db_request.urgency or "").lower() in {"urgent", "high"}:
        await hub.broadcast(
            "escalation",
            {
                "request_id": db_request.id,
                "urgency": db_request.urgency,
                "category": db_request.category,
                "reason": f"Marked {db_request.urgency} urgency",
            },
        )

    return _request_out(db, db_request, oracle=public_oracle)


@router.get("/", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db)):
    rows = db.query(Request).order_by(Request.id).all()
    return [_request_out(db, item) for item in rows]


@router.get("/{request_id}/status", response_model=RequestStatusOut)
def get_request_status(request_id: int, db: Session = Depends(get_db)):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    decisions = db.query(RecommendationDecision).order_by(RecommendationDecision.id).all()
    return build_request_status(db_request, decisions)


@router.get("/{request_id}/followups", response_model=list[FollowUpOut])
def get_request_followups(request_id: int, db: Session = Depends(get_db)):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return list_followups(db, request_id)


@router.post(
    "/{request_id}/followups",
    response_model=FollowUpOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_request_followup(
    request_id: int,
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    followup = create_followup(db, request_id, payload)
    await hub.broadcast(
        "request.followup",
        {
            "request_id": request_id,
            "followup": followup.model_dump(mode="json"),
        },
    )
    return followup


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return _request_out(db, db_request)

