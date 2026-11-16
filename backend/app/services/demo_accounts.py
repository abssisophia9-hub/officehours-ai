"""Seed demo AUI accounts + multi-course memberships for supervisor testing.

AUI emails look like ``S.Abssi@aui.ma`` (first initial + '.' + last name).
They do **not** encode role - student / TA / professor comes only from
``course_memberships.role``.

Course codes follow the real AUI catalog style (``CSC 3374``, ``MTH 1304``):
English-language, American-style liberal-arts curriculum at the School of
Science & Engineering (SSE). A typical full-time undergrad load is about
6–7 courses per term.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.services.auth_service import hash_password
from app.services.demo_mode import demo_mode

DEMO_PASSWORD = "aui-demo"

# Old demo emails → AUI-format emails (migrate existing local DBs).
EMAIL_MIGRATIONS = {
    "professor@aui.ma": "a.benali@aui.ma",
    "ta.alice@aui.ma": "a.chen@aui.ma",
    "ta.bob@aui.ma": "b.martinez@aui.ma",
    "student@aui.ma": "s.elidrissi@aui.ma",
    "student2@aui.ma": "y.amrani@aui.ma",
}

# Fake US-style codes → real AUI catalog codes (same term).
COURSE_CODE_MIGRATIONS = {
    "CS 400": {
        "code": "CSC 2302",
        "title": "Data Structures",
        "canvas_course_id": "4001",
    },
    "CS 330": {
        "code": "CSC 3323",
        "title": "Analysis of Algorithms",
        "canvas_course_id": "3301",
    },
    "CS 210": {
        "code": "CSC 3351",
        "title": "Operating Systems",
        "canvas_course_id": "2101",
    },
}

# Catalog-accurate AUI courses used across demos / Canvas mirror.
DEMO_COURSES = {
    "CSC 2302": {
        "title": "Data Structures",
        "term": "Spring 2026",
        "canvas_course_id": "4001",
    },
    "CSC 3323": {
        "title": "Analysis of Algorithms",
        "term": "Spring 2026",
        "canvas_course_id": "3301",
    },
    "CSC 3374": {
        "title": "Adv. Distributed Programming Paradigms",
        "term": "Spring 2026",
        "canvas_course_id": "3374",
    },
    "CSC 3326": {
        "title": "Database Systems",
        "term": "Spring 2026",
        "canvas_course_id": "3326",
    },
    "CSC 3324": {
        "title": "Software Engineering I",
        "term": "Spring 2026",
        "canvas_course_id": "3324",
    },
    "MTH 1304": {
        "title": "Discrete Mathematics for Engineers",
        "term": "Spring 2026",
        "canvas_course_id": "1304",
    },
    # Liberal-arts core (AUI American curriculum); not Canvas-mirrored for demos.
    "COM 1301": {
        "title": "Public Speaking",
        "term": "Spring 2026",
        "canvas_course_id": None,
    },
    # Labeled demo section: professor, no TA. Used to show professor routing.
    "CSC 3390": {
        "title": "Demo seminar (no TA - professor only)",
        "term": "Spring 2026",
        "canvas_course_id": "3390",
    },
}


def _membership(code: str, role: str) -> dict:
    meta = DEMO_COURSES[code]
    return {
        "code": code,
        "title": meta["title"],
        "term": meta["term"],
        "role": role,
        "canvas_course_id": meta.get("canvas_course_id"),
    }


DEMO_USERS = [
    {
        "email": "a.benali@aui.ma",
        "display_name": "Prof. Amine Benali",
        "student_id": None,
        "memberships": [
            _membership("CSC 2302", "professor"),
            _membership("CSC 3323", "professor"),
            _membership("CSC 3374", "professor"),
            _membership("CSC 3390", "professor"),
        ],
    },
    {
        # COM 1301 is not Canvas-mirrored, so this is a separate demo professor
        # rather than another course on Prof. Benali (his login requires a Canvas id).
        # Also covers MTH 1304, which otherwise has no TA and no professor.
        "email": "n.elfassi@aui.ma",
        "display_name": "Prof. Nadia El Fassi (demo)",
        "student_id": None,
        "memberships": [
            _membership("COM 1301", "professor"),
            _membership("MTH 1304", "professor"),
        ],
    },
    {
        # Alice is staff on CSC 2302 (a course she already took).
        # Other memberships are leftover demo enrollments, not "TA of 2302 = student of 2302".
        "email": "a.chen@aui.ma",
        "display_name": "Alice Chen",
        "student_id": "118110",
        "handle": "a.chen",
        "country": "Morocco",
        "bio": "TA in Data Structures; student everywhere else.",
        "skills": ["C++", "Data Structures", "Office hours"],
        "memberships": [
            _membership("CSC 2302", "ta"),
            _membership("CSC 3323", "student"),
            _membership("MTH 1304", "student"),
            _membership("COM 1301", "student"),
        ],
    },
    {
        # Bob TAs three CSC courses and is enrolled as a student elsewhere.
        "email": "b.martinez@aui.ma",
        "display_name": "Bob Martinez",
        "student_id": "118210",
        "memberships": [
            _membership("CSC 2302", "ta"),
            _membership("CSC 3323", "ta"),
            _membership("CSC 3374", "ta"),
            _membership("MTH 1304", "student"),
            _membership("COM 1301", "student"),
        ],
    },
    {
        # Second TA on Algorithms + Databases - dual-TA sections.
        "email": "p.nair@aui.ma",
        "display_name": "Priya Nair",
        "student_id": "118310",
        "memberships": [
            _membership("CSC 3323", "ta"),
            _membership("CSC 3326", "ta"),
            _membership("MTH 1304", "student"),
        ],
    },
    {
        # Second TA on Distributed + sensitive-topic specialist.
        "email": "s.ortiz@aui.ma",
        "display_name": "Sam Ortiz",
        "student_id": "118410",
        "memberships": [
            _membership("CSC 3374", "ta"),
            _membership("CSC 3324", "ta"),
            _membership("COM 1301", "student"),
        ],
    },
    {
        "email": "s.elidrissi@aui.ma",
        "display_name": "Sara El Idrissi",
        "student_id": "117400",
        "handle": "s.elidrissi",
        "country": "Morocco",
        "bio": "SSE undergrad. I get stuck on the last invariant, then the aha is usually one missing check.",
        "skills": ["Python", "Data Structures", "Algorithms", "Discrete Math"],
        # Typical AUI undergrad load: ~6–7 courses / term (SSE + MTH + liberal arts).
        # CSC 3351 (OS) is intentionally left for Canvas auto-provision demos only.
        "memberships": [
            _membership("CSC 2302", "student"),
            _membership("CSC 3323", "student"),
            _membership("CSC 3374", "student"),
            _membership("CSC 3326", "student"),
            _membership("CSC 3324", "student"),
            _membership("MTH 1304", "student"),
            _membership("COM 1301", "student"),
            # Labeled demo: professor only, so Sara can show no-TA routing.
            _membership("CSC 3390", "student"),
        ],
    },
    {
        "email": "y.amrani@aui.ma",
        "display_name": "Youssef Amrani",
        "student_id": "117401",
        "handle": "y.amrani",
        "country": "Morocco",
        "bio": "Happy to walk traces and hashing walks. Ask if you want a second pair of eyes, not a write-up.",
        "skills": ["Algorithms", "Hashing", "Graph theory"],
        "memberships": [
            _membership("CSC 3323", "student"),
            _membership("CSC 3374", "student"),
            _membership("MTH 1304", "student"),
        ],
    },
]


def ensure_demo_accounts(db: Session) -> None:
    """Create or repair demo users/courses (idempotent, migrates old emails/codes).

    No-op unless ``OFFICEHOURS_DEMO`` is on. Production AUI deploy must not
    invent Sara/Youssef or sample courses - Canvas/LTI provisions those.
    """
    if not demo_mode():
        return
    _migrate_legacy_emails(db)
    _migrate_legacy_course_codes(db)

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
                course.title = membership["title"]
                canvas_id = membership.get("canvas_course_id")
                if canvas_id:
                    course.canvas_course_id = canvas_id
                db.add(course)
            courses_by_code[code] = course

        user = db.query(User).filter(User.email == spec["email"]).one_or_none()
        skills = spec.get("skills") or []
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(DEMO_PASSWORD),
                display_name=spec["display_name"],
                student_id=spec["student_id"],
                handle=spec.get("handle"),
                bio=spec.get("bio"),
                country=spec.get("country") or "Morocco",
                skills_json=json.dumps(skills) if skills else None,
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.display_name = spec["display_name"]
            user.student_id = spec["student_id"]
            user.is_active = True
            if spec.get("handle"):
                user.handle = spec["handle"]
            if spec.get("bio"):
                user.bio = spec["bio"]
            user.country = spec.get("country") or user.country or "Morocco"
            if skills:
                user.skills_json = json.dumps(skills)
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
    from app.services.gold_label_seed import seed_alice_gold_pass
    from app.services.ml_demo_seed import seed_ml_demo

    seed_alice_gold_pass(db)
    seed_ml_demo(db)


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


def _migrate_legacy_course_codes(db: Session) -> None:
    for old_code, meta in COURSE_CODE_MIGRATIONS.items():
        rows = db.query(Course).filter(Course.code == old_code).all()
        for course in rows:
            # Prefer renaming in place when the target code is free for this term.
            conflict = (
                db.query(Course)
                .filter(Course.code == meta["code"], Course.term == course.term)
                .one_or_none()
            )
            if conflict is None or conflict.id == course.id:
                course.code = meta["code"]
                course.title = meta["title"]
                if meta.get("canvas_course_id"):
                    course.canvas_course_id = meta["canvas_course_id"]
                db.add(course)
    db.flush()
