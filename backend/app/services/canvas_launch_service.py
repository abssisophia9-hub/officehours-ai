"""SaaS-style one-click launch from inside a Canvas course.

Models an LTI-style tool launch: Canvas sends who the user is, which course
they clicked from, and their role in that course. We then:

1. auto-provision the user (first launch = instant account),
2. auto-provision the course tenant (found by ``canvas_course_id``),
3. upsert the course membership with the role mapped from Canvas,
4. ingest the course's Canvas modules/slides into the course KB
   (spawning the dedicated course agent) when it is not provisioned yet,
5. mint a session token so the browser lands signed-in in the right
   workspace with the right course active.
"""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.services.auth_service import hash_password, new_session_token, session_expiry
from app.models.auth import AuthSession
from app.services.canvas_service import (
    canvas_course_snapshot,
    canvas_mode,
    sync_course_materials,
)

# Canvas / LTI enrollment role → product role. Unknown roles default to
# student, matching how LMS tools treat unrecognized launch roles.
CANVAS_ROLE_MAP = {
    "teacherenrollment": "professor",
    "teacher": "professor",
    "instructor": "professor",
    "professor": "professor",
    "taenrollment": "ta",
    "ta": "ta",
    "studentenrollment": "student",
    "student": "student",
    "learner": "student",
}


def map_canvas_role(canvas_role: str | None) -> str:
    return CANVAS_ROLE_MAP.get((canvas_role or "").strip().lower(), "student")


def launch_from_canvas(
    db: Session,
    *,
    canvas_course_id: str,
    email: str,
    display_name: str,
    canvas_role: str | None = None,
    course_code: str | None = None,
    course_title: str | None = None,
    term: str | None = None,
    student_id: str | None = None,
) -> dict[str, Any]:
    role = map_canvas_role(canvas_role)
    email = email.strip().lower()

    # 1. Course tenant: find by canvas id, else auto-provision.
    course = (
        db.query(Course)
        .filter(Course.canvas_course_id == str(canvas_course_id))
        .one_or_none()
    )
    provisioned_course = False
    if course is None:
        snapshot = canvas_course_snapshot(str(canvas_course_id)) or {}
        course = Course(
            code=course_code or snapshot.get("code") or f"CANVAS-{canvas_course_id}",
            title=course_title
            or snapshot.get("title")
            or f"Canvas course {canvas_course_id}",
            term=term or snapshot.get("term"),
            canvas_course_id=str(canvas_course_id),
            is_active=True,
        )
        db.add(course)
        db.flush()
        provisioned_course = True

    # 2. User: first launch creates the account (no password login needed —
    # sessions come from Canvas launches; a random secret fills the hash).
    user = db.query(User).filter(User.email == email).one_or_none()
    provisioned_user = False
    if user is None:
        user = User(
            email=email,
            password_hash=hash_password(secrets.token_urlsafe(24)),
            display_name=display_name.strip() or email.split("@", 1)[0],
            student_id=student_id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        provisioned_user = True
    else:
        if display_name.strip():
            user.display_name = display_name.strip()
        if student_id:
            user.student_id = student_id
        db.add(user)

    # 3. Membership: upsert with the Canvas-declared role.
    membership = (
        db.query(CourseMembership)
        .filter(
            CourseMembership.course_id == course.id,
            CourseMembership.user_id == user.id,
        )
        .one_or_none()
    )
    if membership is None:
        membership = CourseMembership(
            course_id=course.id, user_id=user.id, role=role
        )
        db.add(membership)
    elif membership.role != role:
        membership.role = role
        db.add(membership)

    # 4. Spawn/refresh the course agent KB. Professors always re-sync
    # (picking up newly uploaded module slides); students trigger the
    # first-launch provisioning sync only.
    from app.models.knowledge import KnowledgeEntry

    existing_chunks = (
        db.query(KnowledgeEntry.id)
        .filter(
            KnowledgeEntry.course_id == course.id,
            KnowledgeEntry.material_source == "canvas",
        )
        .count()
    )
    sync_result: dict[str, Any] | None = None
    if role == "professor" or existing_chunks == 0:
        sync_result = sync_course_materials(db, course, auto_approve=True)

    approved_chunks = (
        db.query(KnowledgeEntry.id)
        .filter(
            KnowledgeEntry.course_id == course.id,
            KnowledgeEntry.status == "approved",
        )
        .count()
    )

    # 5. Session token — browser lands signed-in.
    token = new_session_token()
    db.add(AuthSession(token=token, user_id=user.id, expires_at=session_expiry()))
    db.commit()
    db.refresh(course)
    db.refresh(user)

    return {
        "token": token,
        "user_id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "course_id": course.id,
        "course_code": course.code,
        "course_title": course.title,
        "role": role,
        "canvas_course_id": str(canvas_course_id),
        "mode": canvas_mode(),
        "provisioned_user": provisioned_user,
        "provisioned_course": provisioned_course,
        "synced": sync_result is not None,
        "sync": sync_result,
        "agent_ready": approved_chunks > 0,
        "kb_chunks": approved_chunks,
        "message": (
            f"{'Provisioned' if provisioned_course else 'Connected'} {course.code} "
            f"from Canvas as {role}. Course agent "
            f"{'ready' if approved_chunks > 0 else 'pending materials'} "
            f"({approved_chunks} KB chunk(s))."
        ),
    }
