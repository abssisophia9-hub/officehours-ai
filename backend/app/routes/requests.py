"""
Routes for submitting and retrieving student requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.clustering import assign_cluster_id
from app.database.session import get_db
from app.models.action import RecommendationDecision
from app.models.request import Request, RequestCreate, RequestOut, RequestStatusOut
from app.realtime.hub import hub
from app.services.classification_service import classify_and_recommend
from app.services.knowledge_service import create_pending_entry_from_request
from app.services.request_status_service import build_request_status

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
async def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    request_data = payload.model_dump()
    classification = classify_and_recommend(payload.text)

    if not request_data.get("category"):
        request_data["category"] = classification["category"]
    if not request_data.get("urgency"):
        request_data["urgency"] = classification.get("urgency")
    if not request_data.get("learning_style"):
        request_data["learning_style"] = classification.get("learning_style")
    if not request_data.get("recommended_action"):
        request_data["recommended_action"] = classification["recommended_action"]
    if request_data.get("cluster_id") is None:
        existing_requests = db.query(Request).order_by(Request.id).all()
        request_data["cluster_id"] = assign_cluster_id(payload.text, existing_requests)

    db_request = Request(**request_data)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    entry = create_pending_entry_from_request(
        db,
        db_request,
        urgency=str(classification.get("urgency") or db_request.urgency or ""),
        matched_keywords=list(classification.get("matched_keywords") or []),
        learning_style=str(
            classification.get("learning_style") or db_request.learning_style or "unknown"
        ),
    )

    await hub.broadcast(
        "request.created",
        {
            "id": db_request.id,
            "category": db_request.category,
            "urgency": db_request.urgency,
            "learning_style": db_request.learning_style,
            "cluster_id": db_request.cluster_id,
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

    return db_request


@router.get("/", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db)):
    return db.query(Request).order_by(Request.id).all()


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


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return db_request
