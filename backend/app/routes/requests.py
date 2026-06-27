"""
Routes for submitting and retrieving student requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.clustering import assign_cluster_id
from app.database.session import get_db
from app.models.request import Request, RequestCreate, RequestOut
from app.services.classification_service import classify_and_recommend

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    request_data = payload.model_dump()
    classification = classify_and_recommend(payload.text)

    if not request_data.get("category"):
        request_data["category"] = classification["category"]
    if not request_data.get("recommended_action"):
        request_data["recommended_action"] = classification["recommended_action"]
    if request_data.get("cluster_id") is None:
        existing_requests = db.query(Request).order_by(Request.id).all()
        request_data["cluster_id"] = assign_cluster_id(payload.text, existing_requests)

    db_request = Request(**request_data)
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    return db_request


@router.get("/", response_model=list[RequestOut])
def list_requests(db: Session = Depends(get_db)):
    return db.query(Request).order_by(Request.id).all()


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: int, db: Session = Depends(get_db)):
    db_request = db.get(Request, request_id)
    if db_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )
    return db_request
