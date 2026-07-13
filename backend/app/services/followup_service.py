"""Create and list follow-up messages on help requests."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.followup import FollowUpCreate, FollowUpOut, RequestFollowUp


def load_followups(db: Session, request_id: int) -> list[RequestFollowUp]:
    return (
        db.query(RequestFollowUp)
        .filter(RequestFollowUp.request_id == request_id)
        .order_by(RequestFollowUp.created_at.asc(), RequestFollowUp.id.asc())
        .all()
    )


def load_followups_map(
    db: Session, request_ids: list[int]
) -> dict[int, list[RequestFollowUp]]:
    if not request_ids:
        return {}
    rows = (
        db.query(RequestFollowUp)
        .filter(RequestFollowUp.request_id.in_(request_ids))
        .order_by(RequestFollowUp.created_at.asc(), RequestFollowUp.id.asc())
        .all()
    )
    grouped: dict[int, list[RequestFollowUp]] = {request_id: [] for request_id in request_ids}
    for row in rows:
        grouped.setdefault(row.request_id, []).append(row)
    return grouped


def to_followup_out(row: RequestFollowUp) -> FollowUpOut:
    return FollowUpOut.model_validate(row)


def list_followups(db: Session, request_id: int) -> list[FollowUpOut]:
    return [to_followup_out(row) for row in load_followups(db, request_id)]


def create_followup(
    db: Session, request_id: int, payload: FollowUpCreate
) -> FollowUpOut:
    row = RequestFollowUp(
        request_id=request_id,
        author_role=payload.author_role.strip().lower(),
        author_name=payload.author_name.strip(),
        message=payload.message.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return to_followup_out(row)
