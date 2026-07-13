"""Seed demo AUI accounts + multi-course memberships for supervisor testing."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.services.auth_service import hash_password

DEMO_PASSWORD = "aui-demo"

DEMO_USERS = [
    {
        "email": "professor@aui.ma",
        "display_name": "Prof. Amine Benali",
        "student_id": None,
        "memberships": [
            {"code": "CS 400", "title": "Data Structures", "term": "Spring 2026", "role": "professor"},
            {"code": "CS 330", "title": "Algorithms", "term": "Spring 2026", "role": "professor"},
        ],
    },
    {
        "email": "ta.alice@aui.ma",
        "display_name": "Alice Chen",
        "student_id": None,
        "memberships": [
            {"code": "CS 400", "title": "Data Structures", "term": "Spring 2026", "role": "ta"},
        ],
    },
    {
        "email": "ta.bob@aui.ma",
        "display_name": "Bob Martinez",
        "student_id": None,
        "memberships": [
            {"code": "CS 400", "title": "Data Structures", "term": "Spring 2026", "role": "ta"},
            {"code": "CS 330", "title": "Algorithms", "term": "Spring 2026", "role": "ta"},
        ],
    },
    {
        "email": "student@aui.ma",
        "display_name": "Sara El Idrissi",
        "student_id": "117400",
        "memberships": [
            {"code": "CS 400", "title": "Data Structures", "term": "Spring 2026", "role": "student"},
            {"code": "CS 330", "title": "Algorithms", "term": "Spring 2026", "role": "student"},
        ],
    },
    {
        "email": "student2@aui.ma",
        "display_name": "Youssef Amrani",
        "student_id": "117401",
        "memberships": [
            {"code": "CS 330", "title": "Algorithms", "term": "Spring 2026", "role": "student"},
        ],
    },
]


def ensure_demo_accounts(db: Session) -> None:
    """Idempotently create demo users/courses for the packaged product."""
    existing = db.query(User).filter(User.email == "professor@aui.ma").one_or_none()
    if existing is not None:
        return

    courses_by_code: dict[str, Course] = {}
    for spec in DEMO_USERS:
        for membership in spec["memberships"]:
            code = membership["code"]
            if code in courses_by_code:
                continue
            course = (
                db.query(Course).filter(Course.code == code, Course.term == membership["term"]).one_or_none()
            )
            if course is None:
                course = Course(
                    code=code,
                    title=membership["title"],
                    term=membership["term"],
                    is_active=True,
                )
                db.add(course)
                db.flush()
            courses_by_code[code] = course

        user = User(
            email=spec["email"],
            password_hash=hash_password(DEMO_PASSWORD),
            display_name=spec["display_name"],
            student_id=spec["student_id"],
            is_active=True,
        )
        db.add(user)
        db.flush()
        for membership in spec["memberships"]:
            db.add(
                CourseMembership(
                    course_id=courses_by_code[membership["code"]].id,
                    user_id=user.id,
                    role=membership["role"],
                )
            )
    db.commit()
