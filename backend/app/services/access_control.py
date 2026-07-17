"""Course membership access helpers for protected routes."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User


def get_membership(db: Session, user: User, course_id: int) -> CourseMembership:
    membership = (
        db.query(CourseMembership)
        .filter(
            CourseMembership.user_id == user.id,
            CourseMembership.course_id == course_id,
        )
        .one_or_none()
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this course.",
        )
    return membership


def require_course_role(
    db: Session,
    user: User,
    course_id: int,
    *,
    roles: set[str],
) -> tuple[Course, CourseMembership]:
    course = db.get(Course, course_id)
    if course is None or not course.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found.",
        )
    membership = get_membership(db, user, course_id)
    if membership.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {', '.join(sorted(roles))}.",
        )
    return course, membership
