"""Revision Strategist — student-only plan from dossier + web tools."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import User
from app.models.strategist import StrategistPlanOut, StrategistPlanRequest
from app.routes.auth import get_current_user
from app.services.access_control import require_course_role
from app.services.strategist_service import build_plan

router = APIRouter(prefix="/strategist", tags=["strategist"])


@router.post("/plan", response_model=StrategistPlanOut)
def strategist_plan(
    payload: StrategistPlanRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> StrategistPlanOut:
    course, _membership = require_course_role(
        db, user, payload.course_id, roles={"student"}
    )
    return build_plan(
        db,
        user_id=user.id,
        course_id=payload.course_id,
        course_code=course.code,
        grades=payload.grades,
        goal=payload.goal,
    )
