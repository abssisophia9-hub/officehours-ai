"""
Professor analytics: struggle heatmap and escalation feed.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.knowledge import EscalationItem, KnowledgeEntry, StruggleHeatmapCell, StruggleHeatmapOut
from app.models.request import Request

ESCALATION_AGE_MINUTES = 30
HARD_URGENCIES = {"urgent", "high"}
MANUAL_MINUTES_PER_REQUEST = 8
AI_ASSIST_MINUTES_PER_REQUEST = 3


def build_struggle_heatmap(db: Session) -> StruggleHeatmapOut:
    requests = db.query(Request).order_by(Request.created_at).all()
    counts: dict[tuple[str, str], int] = defaultdict(int)

    for request in requests:
        category = request.category or "uncategorized"
        week_start = _week_start(request.created_at)
        counts[(category, week_start)] += 1

    cells = [
        StruggleHeatmapCell(category=category, week_start=week_start, count=count)
        for (category, week_start), count in sorted(
            counts.items(),
            key=lambda item: (item[0][1], -item[1], item[0][0]),
        )
    ]
    return StruggleHeatmapOut(cells=cells, total_requests=len(requests))


def build_escalation_feed(
    db: Session,
    *,
    age_threshold_minutes: int = ESCALATION_AGE_MINUTES,
) -> list[EscalationItem]:
    now = datetime.now(timezone.utc)
    requests = db.query(Request).order_by(Request.created_at.desc()).all()
    category_counts: dict[str, int] = defaultdict(int)
    for request in requests:
        category_counts[request.category or "uncategorized"] += 1

    items: list[EscalationItem] = []
    for request in requests:
        age_minutes = _age_minutes(request.created_at, now)
        urgency = (request.urgency or "").lower()
        category = request.category or "uncategorized"
        reasons: list[str] = []

        if age_minutes >= age_threshold_minutes:
            reasons.append(f"Unresolved for {int(age_minutes)}+ minutes")
        if urgency in HARD_URGENCIES:
            reasons.append(f"Marked {urgency} urgency")
        if category_counts[category] >= 3 and category != "uncategorized":
            reasons.append(f"Recurring topic ({category_counts[category]} requests)")

        if not reasons:
            continue

        items.append(
            EscalationItem(
                request_id=request.id,
                text=request.text,
                category=request.category,
                urgency=request.urgency,
                cluster_id=request.cluster_id,
                created_at=request.created_at,
                reason="; ".join(reasons),
                age_minutes=round(age_minutes, 1),
            )
        )

    items.sort(key=lambda item: (-item.age_minutes, item.request_id))
    return items[:50]


def build_oracle_metrics(db: Session) -> dict:
    requests = db.query(Request).all()
    entries = db.query(KnowledgeEntry).all()
    approved = [entry for entry in entries if entry.status == "approved"]
    pending = [entry for entry in entries if entry.status == "pending_review"]
    with_oracle = [request for request in requests if request.oracle_trace_json]
    assigned = [request for request in requests if request.assigned_ta]

    time_saved = max(
        0,
        len(with_oracle) * (MANUAL_MINUTES_PER_REQUEST - AI_ASSIST_MINUTES_PER_REQUEST),
    )

    recent_traces = []
    for request in sorted(requests, key=lambda item: item.id, reverse=True)[:8]:
        if not request.oracle_trace_json:
            continue
        try:
            import json

            trace = json.loads(request.oracle_trace_json)
        except Exception:
            continue
        recent_traces.append(
            {
                "request_id": request.id,
                "elapsed_ms": trace.get("elapsed_ms"),
                "steps": [
                    {"agent": step.get("agent"), "elapsed_ms": step.get("elapsed_ms")}
                    for step in trace.get("steps") or []
                ],
                "assigned_ta": request.assigned_ta,
                "oracle_category": request.oracle_category,
            }
        )

    return {
        "total_requests": len(requests),
        "oracle_runs": len(with_oracle),
        "matched_assignments": len(assigned),
        "kb_pending_review": len(pending),
        "kb_approved": len(approved),
        "kb_growth": len(entries),
        "time_saved_minutes": time_saved,
        "avg_manual_minutes_assumed": MANUAL_MINUTES_PER_REQUEST,
        "avg_ai_assist_minutes_assumed": AI_ASSIST_MINUTES_PER_REQUEST,
        "recent_agent_traces": recent_traces,
    }


def _week_start(value: datetime | None) -> str:
    if value is None:
        return "unknown"
    aware = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    monday = aware.date().fromordinal(aware.date().toordinal() - aware.weekday())
    return monday.isoformat()


def _age_minutes(created_at: datetime | None, now: datetime) -> float:
    if created_at is None:
        return 0.0
    aware = (
        created_at
        if created_at.tzinfo is not None
        else created_at.replace(tzinfo=timezone.utc)
    )
    return max(0.0, (now - aware).total_seconds() / 60.0)
