"""KB hit-rate telemetry and gold-label helpers."""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.agent_metrics import (
    AgentGoldLabel,
    CourseKbHitRate,
    GoldLabelCreate,
    KbAskEvent,
    KbHitRateReport,
)
from app.models.auth import Course
from app.models.knowledge import AgentAskResponse


def record_kb_ask_event(
    db: Session,
    *,
    question: str,
    course_id: int | None,
    response: AgentAskResponse,
) -> KbAskEvent:
    hit = bool(response.matched_count > 0 and not response.should_seek_help)
    event = KbAskEvent(
        course_id=course_id,
        question=question.strip()[:4000],
        hit=hit,
        should_seek_help=bool(response.should_seek_help),
        confidence=float(response.confidence or 0.0),
        matched_count=int(response.matched_count or 0),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def build_kb_hit_rate_report(
    db: Session,
    *,
    course_id: int | None = None,
) -> KbHitRateReport:
    query = db.query(KbAskEvent)
    if course_id is not None:
        query = query.filter(KbAskEvent.course_id == course_id)
    events = query.all()

    total = len(events)
    hits = sum(1 for event in events if event.hit)
    misses = total - hits
    overall = round(hits / total, 4) if total else 0.0

    by_course_events: dict[int | None, list[KbAskEvent]] = defaultdict(list)
    for event in events:
        by_course_events[event.course_id].append(event)

    course_ids = [cid for cid in by_course_events if cid is not None]
    courses = {}
    if course_ids:
        for course in db.query(Course).filter(Course.id.in_(course_ids)).all():
            courses[course.id] = course

    by_course: list[CourseKbHitRate] = []
    for cid, rows in sorted(
        by_course_events.items(),
        key=lambda item: (-len(item[1]), item[0] is None, item[0] or 0),
    ):
        n = len(rows)
        h = sum(1 for row in rows if row.hit)
        hit_conf = [row.confidence for row in rows if row.hit]
        course = courses.get(cid) if cid is not None else None
        by_course.append(
            CourseKbHitRate(
                course_id=cid,
                course_code=course.code if course else None,
                course_title=course.title if course else None,
                asks=n,
                hits=h,
                misses=n - h,
                hit_rate=round(h / n, 4) if n else 0.0,
                avg_confidence_on_hits=(
                    round(sum(hit_conf) / len(hit_conf), 4) if hit_conf else None
                ),
            )
        )

    return KbHitRateReport(
        total_asks=total,
        total_hits=hits,
        total_misses=misses,
        overall_hit_rate=overall,
        by_course=by_course,
    )


def create_gold_label(db: Session, payload: GoldLabelCreate) -> AgentGoldLabel:
    row = AgentGoldLabel(
        label_id=payload.label_id,
        text=payload.text.strip(),
        gold_category=payload.gold_category.strip(),
        gold_assigned_ta=(payload.gold_assigned_ta or "").strip() or None,
        gold_hint_useful=payload.gold_hint_useful,
        department=(payload.department or "").strip() or None,
        course_code=(payload.course_code or "").strip() or None,
        course_id=payload.course_id,
        labeled_by=(payload.labeled_by or "").strip() or None,
        label_source="human_gold",
        notes=payload.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def list_gold_labels(
    db: Session,
    *,
    department: str | None = None,
    course_id: int | None = None,
    limit: int = 200,
) -> list[AgentGoldLabel]:
    query = db.query(AgentGoldLabel).order_by(AgentGoldLabel.id.desc())
    if department:
        query = query.filter(AgentGoldLabel.department == department.strip())
    if course_id is not None:
        query = query.filter(AgentGoldLabel.course_id == course_id)
    return query.limit(limit).all()
