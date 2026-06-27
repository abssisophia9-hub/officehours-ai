"""
Routes for submitting and retrieving student requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.request import Request, RequestCreate, RequestOut

router = APIRouter(prefix="/requests", tags=["requests"])


@router.post("/", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def create_request(payload: RequestCreate, db: Session = Depends(get_db)):
    db_request = Request(**payload.model_dump())
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
