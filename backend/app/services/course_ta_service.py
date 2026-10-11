"""Course-scoped TA roster for dual-TA Matcher + load views.

A course may have up to two (or more) TAs via ``course_memberships``.
Matcher candidates are built from those memberships, joined to ``ta_roster``
expertise / queue_depth by display name.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.auth import Course, CourseMembership, User
from app.models.request import Request
from app.models.ta_roster import DEFAULT_TA_ROSTER, TaRoster
from app.services.demo_mode import demo_mode

# Product policy for typical AUI sections — soft cap for UX copy; matching
# still uses every TA membership on the course.
TYPICAL_TA_CAP = 2


class NoCourseStaffError(Exception):
    """The course has no TA and no active professor, so an ask cannot be stored."""

    def __init__(self, course_code: str | None = None):
        code = (course_code or "").strip() or "This course"
        self.detail = (
            f"{code} has no TA and no professor, so this ask cannot be sent."
        )
        super().__init__(self.detail)


def course_ta_memberships(db: Session, course_id: int) -> list[tuple[User, CourseMembership]]:
    rows = (
        db.query(User, CourseMembership)
        .join(CourseMembership, CourseMembership.user_id == User.id)
        .filter(
            CourseMembership.course_id == course_id,
            CourseMembership.role == "ta",
            User.is_active.is_(True),
        )
        .order_by(User.display_name)
        .all()
    )
    return list(rows)


def build_course_matcher_roster(
    db: Session,
    *,
    course_id: int | None,
) -> list[dict[str, Any]]:
    """Roster dicts for ``match_ta`` — course TAs when available, else global."""
    roster_by_name = {row.name: row for row in db.query(TaRoster).all()}

    if course_id is not None:
        members = course_ta_memberships(db, course_id)
        if members:
            open_asks = (
                db.query(Request)
                .filter(
                    Request.course_id == course_id,
                    Request.work_status.in_(("open", "claimed", "in_progress")),
                )
                .all()
            )
            roster: list[dict[str, Any]] = []
            for user, _membership in members:
                name = (user.display_name or "").strip()
                if not name:
                    continue
                row = roster_by_name.get(name)
                tags = (
                    json.loads(row.expertise_tags or "[]")
                    if row is not None
                    else _default_tags_for(name)
                )
                depth = sum(
                    1
                    for req in open_asks
                    if req.assigned_ta == name
                    or getattr(req, "claimed_by_user_id", None) == user.id
                    or req.claimed_by == name
                )
                available = bool(row.is_available) if row is not None else True
                if not available:
                    continue
                roster.append(
                    {
                        "id": row.id if row is not None else user.id,
                        "name": name,
                        "user_id": user.id,
                        "expertise_tags": tags,
                        "queue_depth": depth,
                        "is_available": True,
                        "course_scoped": True,
                    }
                )
            if roster:
                return roster
        # Course is known but has no TA memberships — do not invent demo names.
        return []

    if not demo_mode():
        return []

    # Demo only: global roster when no course was supplied.
    return [
        {
            "id": row.id,
            "name": row.name,
            "expertise_tags": json.loads(row.expertise_tags or "[]"),
            "queue_depth": row.queue_depth,
            "is_available": True,
            "course_scoped": False,
        }
        for row in db.query(TaRoster).order_by(TaRoster.id).all()
        if row.is_available
    ]


def course_professor_users(db: Session, course_id: int) -> list[User]:
    """Active professors on a course, lowest user id first.

    When several professors share a course, the smallest ``user.id`` is the
    assignee. Email is only a tie-break; a user has one membership per course.
    """
    rows = (
        db.query(User)
        .join(CourseMembership, CourseMembership.user_id == User.id)
        .filter(
            CourseMembership.course_id == course_id,
            CourseMembership.role == "professor",
            User.is_active.is_(True),
        )
        .order_by(User.id.asc(), User.email.asc())
        .all()
    )
    return list(rows)


def _person_label(user: User) -> str:
    name = (user.display_name or "").strip()
    return name or (user.email or "Professor")


def describe_course_routing(db: Session, course_id: int) -> dict[str, Any]:
    """One line for the Ask form, before the student submits."""
    course = db.get(Course, course_id)
    code = course.code if course and course.code else "this course"
    if course_ta_memberships(db, course_id):
        return {
            "course_id": course_id,
            "course_code": code,
            "destination": "ta",
            "assignee_name": None,
            "line": f"Goes to: a TA for {code} (matched automatically)",
        }
    professors = course_professor_users(db, course_id)
    if professors:
        return {
            "course_id": course_id,
            "course_code": code,
            "destination": "professor",
            "assignee_name": _person_label(professors[0]),
            "line": f"Goes to: the professor of {code} (this course has no TA)",
        }
    return {
        "course_id": course_id,
        "course_code": code,
        "destination": "none",
        "assignee_name": None,
        "line": f"{code} has no TA and no professor, so this ask cannot be sent.",
    }


def assign_professor_when_no_ta(
    db: Session,
    *,
    course_id: int,
    analyzer: dict[str, Any],
    course_code: str | None = None,
) -> dict[str, Any]:
    """Route to the professor with the lowest user id. Raises if none exist."""
    professors = course_professor_users(db, course_id)
    if not professors:
        code = (course_code or "").strip() or None
        if not code:
            course = db.get(Course, course_id)
            code = course.code if course else None
        raise NoCourseStaffError(code)
    chosen = professors[0]
    name = _person_label(chosen)
    wait = int(analyzer.get("estimated_minutes") or 15)
    return {
        "assigned_ta": name,
        "alternative_ta": None,
        "estimated_wait_minutes": wait,
        "assignee_role": "professor",
        "assignee_user_id": chosen.id,
        "rationale": f"This course has no TA, so the ask went to {name}.",
        "backend": "professor_no_ta",
    }


def _default_tags_for(name: str) -> list[str]:
    for item in DEFAULT_TA_ROSTER:
        if item["name"] == name:
            return list(item["expertise_tags"])
    return ["conceptual_question"]


def build_course_ta_load(
    db: Session,
    *,
    course_id: int,
) -> dict[str, Any]:
    """Professor dual-TA load panel payload."""
    course = db.get(Course, course_id)
    members = course_ta_memberships(db, course_id)
    roster_by_name = {row.name: row for row in db.query(TaRoster).all()}

    open_requests = (
        db.query(Request)
        .filter(Request.course_id == course_id)
        .order_by(Request.created_at.desc())
        .all()
    )

    tas: list[dict[str, Any]] = []
    for user, _membership in members:
        name = user.display_name
        row = roster_by_name.get(name)
        primary = sum(1 for req in open_requests if req.assigned_ta == name)
        backup = sum(1 for req in open_requests if req.alternative_ta == name)
        tas.append(
            {
                "user_id": user.id,
                "name": name,
                "email": user.email,
                "queue_depth": sum(
                    1
                    for req in open_requests
                    if (req.work_status or "open") in {"open", "claimed", "in_progress"}
                    and (
                        req.assigned_ta == name
                        or getattr(req, "claimed_by_user_id", None) == user.id
                        or req.claimed_by == name
                    )
                ),
                "primary_assignments": primary,
                "backup_assignments": backup,
                "open_touch_count": primary + backup,
                "expertise_tags": (
                    json.loads(row.expertise_tags or "[]") if row else []
                ),
            }
        )

    tas.sort(key=lambda item: (-item["open_touch_count"], item["name"]))
    unassigned = sum(
        1
        for req in open_requests
        if not (req.assigned_ta or "").strip()
        or req.assigned_ta == "Unassigned"
    )

    return {
        "course_id": course_id,
        "course_code": course.code if course else None,
        "course_title": course.title if course else None,
        "ta_count": len(tas),
        "typical_ta_cap": TYPICAL_TA_CAP,
        "within_typical_cap": len(tas) <= TYPICAL_TA_CAP,
        "open_requests": len(open_requests),
        "unassigned_open": unassigned,
        "tas": tas,
        "message": (
            f"{len(tas)} TA(s) on this course"
            + (
                f" (typical AUI section uses up to {TYPICAL_TA_CAP})."
                if len(tas) <= TYPICAL_TA_CAP
                else f" — above the typical cap of {TYPICAL_TA_CAP}; Matcher still load-balances."
            )
        ),
    }
