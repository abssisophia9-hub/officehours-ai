"""
Routes for knowledge-base curation and the student-facing KB agent.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.knowledge import (
    AgentAskRequest,
    AgentAskResponse,
    EscalationItem,
    KnowledgeEntry,
    KnowledgeEntryOut,
    KnowledgeEntryUpdate,
    StruggleHeatmapOut,
)
from app.realtime.hub import hub
from app.services.analytics_service import build_escalation_feed, build_struggle_heatmap
from app.services.kb_agent_service import answer_from_knowledge_base
from app.services.knowledge_service import list_entries, to_out, update_entry

router = APIRouter(tags=["knowledge"])


@router.get("/knowledge/", response_model=list[KnowledgeEntryOut])
def list_knowledge_entries(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
):
    if status_filter and status_filter not in {"pending_review", "approved", "rejected"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status must be pending_review, approved, or rejected",
        )
    return [to_out(entry) for entry in list_entries(db, status_filter=status_filter)]


@router.get("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
def get_knowledge_entry(entry_id: int, db: Session = Depends(get_db)):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    return to_out(entry)


@router.patch("/knowledge/{entry_id}", response_model=KnowledgeEntryOut)
async def patch_knowledge_entry(
    entry_id: int,
    payload: KnowledgeEntryUpdate,
    db: Session = Depends(get_db),
):
    entry = db.get(KnowledgeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge entry not found",
        )
    updated = to_out(update_entry(db, entry, payload))
    await hub.broadcast(
        "knowledge.updated",
        {
            "id": updated.id,
            "status": updated.status,
            "source_request_id": updated.source_request_id,
            "learning_style": updated.learning_style,
        },
    )
    return updated


@router.post("/agent/ask", response_model=AgentAskResponse)
def ask_kb_agent(payload: AgentAskRequest, db: Session = Depends(get_db)):
    return answer_from_knowledge_base(db, payload.question, top_k=payload.top_k)


@router.get("/analytics/struggle-heatmap", response_model=StruggleHeatmapOut)
def struggle_heatmap(db: Session = Depends(get_db)):
    return build_struggle_heatmap(db)


@router.get("/analytics/escalations", response_model=list[EscalationItem])
def escalations(db: Session = Depends(get_db)):
    return build_escalation_feed(db)
