"""Student / staff inbox for claim and reply events."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.notification import NotificationOut
from app.routes.auth import get_current_user
from app.services.notify_service import inbox_payload, mark_read

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def my_inbox(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return inbox_payload(db, user)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    row = mark_read(db, user, notification_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return row
