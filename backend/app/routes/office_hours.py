"""
Routes for professor office-hour availability windows.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import CourseMembership, User
from app.routes.auth import get_current_user
from app.services.access_control import require_staff_anywhere
from app.models.office_hours import (
    OfficeHoursWindow,
    OfficeHoursWindowCreate,
    OfficeHoursWindowOut,
)

router = APIRouter(prefix="/office-hours", tags=["office-hours"])

DAY_ORDER = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
}


def _require_professor(db: Session, user: User) -> None:
    professor = (
        db.query(CourseMembership.id)
        .filter(
            CourseMembership.user_id == user.id,
            CourseMembership.role == "professor",
        )
        .first()
    )
    if professor is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires a professor role on at least one course.",
        )


@router.get("/", response_model=list[OfficeHoursWindowOut])
def list_office_hours(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Campus-wide availability windows — professor or TA on any course."""
    require_staff_anywhere(db, user)
    windows = db.query(OfficeHoursWindow).all()
    return sorted(
        windows,
        key=lambda window: (DAY_ORDER.get(window.day, 99), window.start, window.id),
    )


@router.post(
    "/",
    response_model=OfficeHoursWindowOut,
    status_code=status.HTTP_201_CREATED,
)
def create_office_hours_window(
    payload: OfficeHoursWindowCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Only professors may publish campus office-hour windows."""
    _require_professor(db, user)
    window = OfficeHoursWindow(
        day=payload.day,
        start=payload.start,
        end=payload.end,
        location=payload.location.strip() or "TBD",
    )
    db.add(window)
    db.commit()
    db.refresh(window)
    return window


@router.delete("/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_office_hours_window(
    window_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_professor(db, user)
    window = db.get(OfficeHoursWindow, window_id)
    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office hours window not found",
        )

    db.delete(window)
    db.commit()
