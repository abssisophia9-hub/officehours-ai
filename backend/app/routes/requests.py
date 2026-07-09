"""
Routes for submitting and retrieving student requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.clustering import assign_cluster_id
from app.database.session import get_db
from app.models.action import RecommendationDecision
from app.models.request import Request, RequestCreate, RequestOut, RequestStatusOut
from app.services.classification_service import classify_and_recommend
from app.services.knowledge_service import create_pending_entry_from_request
from app.services.request_status_service import build_request_status

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    request_data = payload.model_dump()
    classification = classify_and_recommend(payload.text)

    if not request_data.get("category"):
        request_data["category"] = classification["category"]
    if not request_data.get("urgency"):
        request_data["urgency"] = classification.get("urgency")
    if not request_data.get("recommended_action"):
        request_data["recommended_action"] = classification["recommended_action"]
    if request_data.get("cluster_id") is None:
        existing_requests = db.query(Request).order_by(Request.id).all()
        request_data["cluster_id"] = assign_cluster_id(payload.text, existing_requests)

    db_request = Request(**request_data)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    # Every question seeds a KB draft; professor approval gates student-agent use.
    create_pending_entry_from_request(
        db,
        db_request,
        urgency=str(classification.get("urgency") or db_request.urgency or ""),
        matched_keywords=list(classification.get("matched_keywords") or []),
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
