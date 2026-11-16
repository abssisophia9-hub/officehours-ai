"""Anonymous solidarity counts + opt-in study-buddy for non-sensitive clusters."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.social import StudyBuddyOptIn
from app.services.analytics_service import SENSITIVE_CATEGORIES, is_sensitive_category


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StudyBuddyOptInCreate(BaseModel):
    request_id: int = Field(ge=1)
    display_label: str | None = Field(default=None, max_length=80)


class StudyBuddyStatusOut(BaseModel):
    request_id: int
    cluster_id: int | None
    eligible: bool
    opted_in: bool
    peer_opt_in_count: int
    similar_asks_this_week: int
    solidarity_message: str | None = None
    study_buddy_message: str | None = None
    blocked_reason: str | None = None


def count_similar_asks_this_week(
    db: Session,
    *,
    cluster_id: int | None,
    course_id: int | None,
    exclude_request_id: int | None = None,
) -> int:
    if cluster_id is None:
        return 0
    since = _utcnow() - timedelta(days=7)
    query = db.query(Request).filter(
        Request.cluster_id == cluster_id,
        Request.created_at >= since,
    )
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    if exclude_request_id is not None:
        query = query.filter(Request.id != exclude_request_id)
    return int(query.count())


def solidarity_payload_for_request(db: Session, request: Request) -> dict:
    similar = count_similar_asks_this_week(
        db,
        cluster_id=request.cluster_id,
        course_id=request.course_id,
        exclude_request_id=request.id,
    )
    sensitive = bool(request.sensitive) or is_sensitive_category(request.category)
    if sensitive:
        return {
            "similar_asks_this_week": similar,
            "solidarity_message": None,
            "study_buddy_eligible": False,
        }
    message = None
    if similar >= 1:
        message = (
            f"{similar} other student{'s' if similar != 1 else ''} asked something "
            f"similar this week - you're not alone. Staff may offer a group review."
        )
    return {
        "similar_asks_this_week": similar,
        "solidarity_message": message,
        "study_buddy_eligible": similar >= 1
        and (request.category or "") not in SENSITIVE_CATEGORIES,
    }


def get_study_buddy_status(db: Session, request: Request) -> StudyBuddyStatusOut:
    sensitive = bool(request.sensitive) or is_sensitive_category(request.category)
    similar = count_similar_asks_this_week(
        db,
        cluster_id=request.cluster_id,
        course_id=request.course_id,
        exclude_request_id=request.id,
    )
    opted = (
        db.query(StudyBuddyOptIn)
        .filter(StudyBuddyOptIn.request_id == request.id)
        .one_or_none()
    )
    if sensitive or request.cluster_id is None:
        return StudyBuddyStatusOut(
            request_id=request.id,
            cluster_id=request.cluster_id,
            eligible=False,
            opted_in=opted is not None,
            peer_opt_in_count=0,
            similar_asks_this_week=similar,
            solidarity_message=None,
            blocked_reason=(
                "Private / sensitive asks stay one-to-one - no peer matching."
                if sensitive
                else "No topic cluster yet."
            ),
        )

    peer_query = db.query(StudyBuddyOptIn).filter(
        StudyBuddyOptIn.cluster_id == request.cluster_id,
        StudyBuddyOptIn.request_id != request.id,
    )
    if request.course_id is not None:
        peer_query = peer_query.filter(StudyBuddyOptIn.course_id == request.course_id)
    peer_count = peer_query.count()

    solidarity = None
    if similar >= 1:
        solidarity = (
            f"{similar} other student{'s' if similar != 1 else ''} asked something "
            f"similar this week - you're not alone."
        )
    buddy_msg = None
    if opted is not None:
        buddy_msg = (
            f"You're opted in. {peer_count} other student"
            f"{'s' if peer_count != 1 else ''} in this topic also opted in "
            f"(identities stay private until staff schedules a group review)."
        )
    elif similar >= 1:
        buddy_msg = (
            "Optional: opt in to a conceptual study-buddy / group review for this "
            "topic. Stress or private issues are never peer-matched."
        )

    return StudyBuddyStatusOut(
        request_id=request.id,
        cluster_id=request.cluster_id,
        eligible=True,
        opted_in=opted is not None,
        peer_opt_in_count=int(peer_count),
        similar_asks_this_week=similar,
        solidarity_message=solidarity,
        study_buddy_message=buddy_msg,
        blocked_reason=None,
    )


def opt_in_study_buddy(
    db: Session,
    request: Request,
    *,
    display_label: str | None = None,
) -> StudyBuddyStatusOut:
    status = get_study_buddy_status(db, request)
    if not status.eligible:
        return status
    existing = (
        db.query(StudyBuddyOptIn)
        .filter(StudyBuddyOptIn.request_id == request.id)
        .one_or_none()
    )
    if existing is None:
        db.add(
            StudyBuddyOptIn(
                request_id=request.id,
                cluster_id=int(request.cluster_id),
                course_id=request.course_id,
                display_label=(display_label or "").strip() or None,
            )
        )
        db.commit()
    return get_study_buddy_status(db, request)
