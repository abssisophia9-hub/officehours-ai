"""Revision Agent API — study plan from synthetic weak topics + preference."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.revision import RevisionPlanOut, RevisionPlanRequest
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role
from app.services.revision_service import build_revision_plan

router = APIRouter(prefix="/revision", tags=["revision"])


@router.post("/plan", response_model=RevisionPlanOut)
def create_revision_plan(
    payload: RevisionPlanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RevisionPlanOut:
    require_course_role(db, user, payload.course_id, roles={"student"})
    return build_revision_plan(db, payload, user_id=user.id)
