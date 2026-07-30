"""Feedback routes — bug / issue reports from the account menu."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.feedback import BugReport, BugReportCreate, BugReportOut
from app.routes.auth import get_current_user

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/bugs", response_model=BugReportOut, status_code=status.HTTP_201_CREATED)
def create_bug_report(
    payload: BugReportCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    title = payload.title.strip()
    body = payload.body.strip()
    report = BugReport(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        role=(payload.role or "").strip().lower() or None,
        course_id=payload.course_id,
        course_code=(payload.course_code or "").strip() or None,
        page_path=(payload.page_path or "").strip() or None,
        title=title[:200],
        body=body[:5000],
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return BugReportOut.model_validate(report)
