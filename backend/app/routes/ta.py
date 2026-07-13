"""
TA queue routes. Resolutions update the shared KB curation queue (pending_review).
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.request import Request
from app.models.ta import TaQueueItem, TaResolveRequest, TaResolveResponse
from app.models.ta_roster import TaRoster, TaRosterOut
from app.realtime.hub import hub
from app.services.knowledge_service import to_out
from app.services.oracle_service import ensure_default_roster
from app.services.followup_service import load_followups_map
from app.services.request_serializer import to_request_out

router = APIRouter(prefix="/ta", tags=["ta"])


@router.get("/roster/", response_model=list[TaRosterOut])
def list_ta_roster(db: Session = Depends(get_db)):
    return [TaRosterOut.from_orm_row(row) for row in ensure_default_roster(db)]


@router.get("/queue/", response_model=list[TaQueueItem])
def list_ta_queue(db: Session = Depends(get_db)):
    requests = db.query(Request).order_by(Request.created_at.desc()).all()
    followups_by_request = load_followups_map(db, [request.id for request in requests])
    entries = {
        entry.source_request_id: entry
        for entry in db.query(KnowledgeEntry).all()
        if entry.source_request_id is not None
    }

    items: list[TaQueueItem] = []
    for request in requests:
        entry = entries.get(request.id)
        # Hide fully approved/rejected items from the active TA queue.
        if entry is not None and entry.status in {"approved", "rejected"}:
            continue
        items.append(
            TaQueueItem(
                request=to_request_out(
                    request,
                    followups=followups_by_request.get(request.id, []),
                ),
                knowledge_entry=to_out(entry) if entry else None,
                learning_style=request.learning_style,
                urgency=request.urgency,
            )
        )
    return items



@router.post("/resolve/", response_model=TaResolveResponse)
async def resolve_for_curation(payload: TaResolveRequest, db: Session = Depends(get_db)):
    request = db.get(Request, payload.request_id)
    if request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request not found",
        )

    entry = (
        db.query(KnowledgeEntry)
        .filter(KnowledgeEntry.source_request_id == request.id)
        .order_by(KnowledgeEntry.id.desc())
        .first()
    )
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No knowledge draft exists for this request",
        )

    note_prefix = f"[TA {payload.ta_name.strip()}] "
    entry.answer_draft = payload.teaching_notes.strip()
    if payload.student_hint:
        entry.student_hint = payload.student_hint.strip()
    entry.status = "pending_review"
    entry.reviewed_at = None
    existing_note = entry.professor_note or ""
    resolution_line = (
        f"{note_prefix}marked {payload.resolution_status} at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    entry.professor_note = (
        f"{existing_note}\n{resolution_line}".strip()
        if existing_note
        else resolution_line
    )

    db.add(entry)
    db.commit()
    db.refresh(entry)

    out = to_out(entry)
    await hub.broadcast(
        "knowledge.updated",
        {"id": out.id, "status": out.status, "source_request_id": out.source_request_id},
    )
    await hub.broadcast(
        "ta.resolved",
        {
            "request_id": request.id,
            "ta_name": payload.ta_name,
            "knowledge_entry_id": out.id,
            "resolution_status": payload.resolution_status,
        },
    )

    return TaResolveResponse(
        request_id=request.id,
        knowledge_entry=out,
        message=(
            "Resolution saved to the professor curation queue as pending_review. "
            "It will not reach the student KB agent until approved."
        ),
    )
