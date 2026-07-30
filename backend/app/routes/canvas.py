"""SaaS-style Canvas launch endpoint.

``POST /canvas/launch`` models the click on the OfficeHours AI button inside
a Canvas course (LTI-style tool launch): Canvas supplies user identity,
course context, and enrollment role; we provision everything and hand back
a signed-in session scoped to that course.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.realtime.hub import hub
from app.services.canvas_launch_service import launch_from_canvas

router = APIRouter(prefix="/canvas", tags=["canvas"])


class CanvasLaunchRequest(BaseModel):
    canvas_course_id: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=5, max_length=200)
    display_name: str = Field(min_length=1, max_length=200)
    canvas_role: str | None = Field(
        default=None,
        description="Canvas enrollment role, e.g. StudentEnrollment / TeacherEnrollment / TaEnrollment",
    )
    course_code: str | None = None
    course_title: str | None = None
    term: str | None = None
    student_id: str | None = None
    demo_secret: str | None = Field(
        default=None,
        description=(
            "Optional shared secret when OFFICEHOURS_CANVAS_LAUNCH_SECRET is set. "
            "Unsigned launches are demo-only; production needs Canvas LTI 1.3."
        ),
    )


class CanvasLaunchOut(BaseModel):
    token: str
    user_id: int
    email: str
    display_name: str
    course_id: int
    course_code: str
    course_title: str
    role: str
    canvas_course_id: str
    mode: str
    provisioned_user: bool
    provisioned_course: bool
    synced: bool
    sync: dict | None = None
    agent_ready: bool
    kb_chunks: int
    message: str


@router.post("/launch", response_model=CanvasLaunchOut, status_code=status.HTTP_201_CREATED)
async def canvas_launch(payload: CanvasLaunchRequest, db: Session = Depends(get_db)):
    """JIT provision from a Canvas-like launch payload.

    Demo default: unsigned (anyone who can POST can impersonate). Set
    ``OFFICEHOURS_CANVAS_LAUNCH_SECRET`` to require ``demo_secret`` on the body.
    Production path is signed Canvas LTI 1.3 — not implemented here.
    """
    required = (os.getenv("OFFICEHOURS_CANVAS_LAUNCH_SECRET") or "").strip()
    if required and (payload.demo_secret or "").strip() != required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Canvas launch secret required. This endpoint is an unsigned "
                "demo simulator; production needs Canvas LTI 1.3."
            ),
        )

    result = launch_from_canvas(
        db,
        canvas_course_id=payload.canvas_course_id,
        email=payload.email,
        display_name=payload.display_name,
        canvas_role=payload.canvas_role,
        course_code=payload.course_code,
        course_title=payload.course_title,
        term=payload.term,
        student_id=payload.student_id,
    )
    if result["synced"] and result["sync"]:
        for entry_id in result["sync"].get("entry_ids", []):
            await hub.broadcast(
                "knowledge.created",
                {
                    "id": entry_id,
                    "status": "approved",
                    "material_source": "canvas",
                    "course_id": result["course_id"],
                },
            )
    return CanvasLaunchOut(**result)
