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

# Product policy for typical AUI sections — soft cap for UX copy; matching
# still uses every TA membership on the course.
TYPICAL_TA_CAP = 2


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
                depth = int(row.queue_depth) if row is not None else 0
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

    # Fallback: global demo roster (no course TAs provisioned yet).
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
                "queue_depth": int(row.queue_depth) if row else 0,
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
