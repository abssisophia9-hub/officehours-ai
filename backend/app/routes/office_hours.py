"""
Routes for professor office-hour availability windows.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
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


@router.get("/", response_model=list[OfficeHoursWindowOut])
def list_office_hours(db: Session = Depends(get_db)):
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
):
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
def delete_office_hours_window(window_id: int, db: Session = Depends(get_db)):
    window = db.get(OfficeHoursWindow, window_id)
    if window is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office hours window not found",
        )

    db.delete(window)
    db.commit()
