"""Seed demo AUI accounts + multi-course memberships for supervisor testing.

AUI emails look like ``S.Abssi@aui.ma`` (first initial + '.' + last name).
They do **not** encode role — student / TA / professor comes only from
``course_memberships.role``.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.services.auth_service import hash_password

DEMO_PASSWORD = "aui-demo"

# Old demo emails → AUI-format emails (migrate existing local DBs).
EMAIL_MIGRATIONS = {
    "professor@aui.ma": "a.benali@aui.ma",
    "ta.alice@aui.ma": "a.chen@aui.ma",
    "ta.bob@aui.ma": "b.martinez@aui.ma",
    "student@aui.ma": "s.elidrissi@aui.ma",
    "student2@aui.ma": "y.amrani@aui.ma",
}

DEMO_USERS = [
    {
        "email": "a.benali@aui.ma",
        "display_name": "Prof. Amine Benali",
        "student_id": None,
        "memberships": [
            {
                "code": "CS 400",
                "title": "Data Structures",
                "term": "Spring 2026",
                "role": "professor",
                "canvas_course_id": "4001",
            },
            {
                "code": "CS 330",
                "title": "Algorithms",
                "term": "Spring 2026",
                "role": "professor",
                "canvas_course_id": "3301",
            },
        ],
    },
    {
        "email": "a.chen@aui.ma",
        "display_name": "Alice Chen",
        "student_id": None,
        "memberships": [
            {
                "code": "CS 400",
                "title": "Data Structures",
                "term": "Spring 2026",
                "role": "ta",
                "canvas_course_id": "4001",
            },
        ],
    },
    {
        "email": "b.martinez@aui.ma",
        "display_name": "Bob Martinez",
        "student_id": None,
        "memberships": [
            {
                "code": "CS 400",
                "title": "Data Structures",
                "term": "Spring 2026",
                "role": "ta",
                "canvas_course_id": "4001",
            },
            {
                "code": "CS 330",
                "title": "Algorithms",
                "term": "Spring 2026",
                "role": "ta",
                "canvas_course_id": "3301",
            },
        ],
    },
    {
        "email": "s.elidrissi@aui.ma",
        "display_name": "Sara El Idrissi",
        "student_id": "117400",
        "memberships": [
            {
                "code": "CS 400",
                "title": "Data Structures",
                "term": "Spring 2026",
                "role": "student",
                "canvas_course_id": "4001",
            },
            {
                "code": "CS 330",
                "title": "Algorithms",
                "term": "Spring 2026",
                "role": "student",
                "canvas_course_id": "3301",
            },
        ],
    },
    {
        "email": "y.amrani@aui.ma",
        "display_name": "Youssef Amrani",
        "student_id": "117401",
        "memberships": [
            {
                "code": "CS 330",
                "title": "Algorithms",
                "term": "Spring 2026",
                "role": "student",
                "canvas_course_id": "3301",
            },
        ],
    },
]


def ensure_demo_accounts(db: Session) -> None:
    """Create or repair demo users/courses (idempotent, migrates old emails)."""
    _migrate_legacy_emails(db)

    courses_by_code: dict[str, Course] = {}
    for spec in DEMO_USERS:
        for membership in spec["memberships"]:
            code = membership["code"]
            if code in courses_by_code:
                continue
            course = (
                db.query(Course)
                .filter(Course.code == code, Course.term == membership["term"])
                .one_or_none()
            )
            if course is None:
                course = Course(
                    code=code,
                    title=membership["title"],
                    term=membership["term"],
                    canvas_course_id=membership.get("canvas_course_id"),
                    is_active=True,
                )
                db.add(course)
                db.flush()
            else:
                canvas_id = membership.get("canvas_course_id")
                if canvas_id and not getattr(course, "canvas_course_id", None):
                    course.canvas_course_id = canvas_id
                    db.add(course)
            courses_by_code[code] = course

        user = db.query(User).filter(User.email == spec["email"]).one_or_none()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=spec["display_name"],
                student_id=spec["student_id"],
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.display_name = spec["display_name"]
            user.student_id = spec["student_id"]
            user.is_active = True
            db.add(user)

        for membership in spec["memberships"]:
            course = courses_by_code[membership["code"]]
            row = (
                db.query(CourseMembership)
                .filter(
                    CourseMembership.course_id == course.id,
                    CourseMembership.user_id == user.id,
                )
                .one_or_none()
            )
            if row is None:
                db.add(
                    CourseMembership(
                        course_id=course.id,
                        user_id=user.id,
                        role=membership["role"],
                    )
                )
            elif row.role != membership["role"]:
                row.role = membership["role"]
                db.add(row)

    db.commit()


def _migrate_legacy_emails(db: Session) -> None:
    for old_email, new_email in EMAIL_MIGRATIONS.items():
        old = db.query(User).filter(User.email == old_email).one_or_none()
        if old is None:
            continue
        conflict = db.query(User).filter(User.email == new_email).one_or_none()
        if conflict is None:
            old.email = new_email
            db.add(old)
        # If both exist, leave them; new seed path will keep the AUI-format user.
    db.flush()
