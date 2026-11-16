"""
Professor analytics: struggle heatmap, escalation feed, and cluster command center.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.summarizer import summarize_request_cluster
from app.models.auth import Course
from app.models.help_room import (
    HelpPost,
    ReviewInsightQuestionOut,
    ReviewInsightTopicOut,
    ReviewInsightsOut,
    ReviewTopicNote,
)
from app.models.knowledge import (
    ClusterCommandCenterOut,
    ClusterTopicOut,
    EscalationItem,
    KnowledgeEntry,
    StruggleHeatmapCell,
    StruggleHeatmapOut,
)
from app.models.request import Request

ESCALATION_AGE_MINUTES = 30
HARD_URGENCIES = {"urgent", "high"}
MANUAL_MINUTES_PER_REQUEST = 8
AI_ASSIST_MINUTES_PER_REQUEST = 3
SENSITIVE_CATEGORIES = {
    "emotional_stress",
    "accessibility_accommodation",
    "academic_integrity",
    "retake_request",
    "grading_dispute",
}
GROUP_REVIEW_MIN = 3
FAQ_MIN = 2


def build_struggle_heatmap(
    db: Session, *, course_ids: list[int] | None = None
) -> StruggleHeatmapOut:
    query = db.query(Request)
    if course_ids is not None:
        query = query.filter(Request.course_id.in_(course_ids))
    requests = query.order_by(Request.created_at).all()
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
    course: str | None = None,
    course_id: int | None = None,
    course_ids: list[int] | None = None,
) -> list[EscalationItem]:
    now = datetime.now(timezone.utc)
    query = db.query(Request)
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    elif course_ids is not None:
        query = query.filter(Request.course_id.in_(course_ids or [-1]))
    elif course:
        query = query.filter(Request.course == course)
    requests = query.order_by(Request.created_at.desc()).all()
    category_counts: dict[str, int] = defaultdict(int)
    for request in requests:
        category_counts[request.category or "uncategorized"] += 1

    items: list[EscalationItem] = []
    for request in requests:
        age_minutes = _age_minutes(request.created_at, now)
        urgency = (request.urgency or "").lower()
        category = request.category or "uncategorized"
        sensitive = bool(getattr(request, "sensitive", False)) or category in SENSITIVE_CATEGORIES
        reasons: list[str] = []

        if age_minutes >= age_threshold_minutes:
            reasons.append(f"Unresolved for {int(age_minutes)}+ minutes")
        if urgency in HARD_URGENCIES:
            reasons.append(f"Marked {urgency} urgency")
        if category_counts[category] >= 3 and category != "uncategorized":
            reasons.append(f"Recurring topic ({category_counts[category]} requests)")
        if sensitive:
            reasons.append("Sensitive / private follow-up needed")

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
                sensitive=sensitive,
            )
        )

    items.sort(key=lambda item: (not item.sensitive, -item.age_minutes, item.request_id))
    return items[:50]


def build_cluster_command_center(
    db: Session,
    *,
    course: str | None = None,
    course_id: int | None = None,
    course_ids: list[int] | None = None,
) -> ClusterCommandCenterOut:
    query = db.query(Request)
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    elif course_ids is not None:
        query = query.filter(Request.course_id.in_(course_ids or [-1]))
    elif course:
        query = query.filter(Request.course == course)
    requests = query.order_by(Request.created_at.desc()).all()

    by_cluster: dict[int, list[Request]] = defaultdict(list)
    for request in requests:
        if request.cluster_id is None:
            continue
        by_cluster[request.cluster_id].append(request)

    clusters: list[ClusterTopicOut] = []
    for cluster_id, members in by_cluster.items():
        summary = summarize_request_cluster([item.text for item in members])
        urgency_mix = dict(Counter((item.urgency or "unknown").lower() for item in members))
        anonymous_count = sum(1 for item in members if item.anonymous)
        sensitive_count = sum(
            1
            for item in members
            if bool(getattr(item, "sensitive", False))
            or (item.category or "") in SENSITIVE_CATEGORIES
        )
        suggested_action, suggestion_reason = _suggest_cluster_action(
            members,
            sensitive_count=sensitive_count,
            urgency_mix=urgency_mix,
        )
        category = Counter(item.category or "uncategorized" for item in members).most_common(1)[
            0
        ][0]
        clusters.append(
            ClusterTopicOut(
                cluster_id=cluster_id,
                title=str(summary["title"]),
                keywords=list(summary.get("keywords") or []),
                request_count=len(members),
                request_ids=[item.id for item in members],
                sample_texts=[item.text[:220] for item in members[:3]],
                urgency_mix=urgency_mix,
                anonymous_count=anonymous_count,
                sensitive_count=sensitive_count,
                suggested_action=suggested_action,
                suggestion_reason=suggestion_reason,
                category=None if category == "uncategorized" else category,
            )
        )

    clusters.sort(
        key=lambda item: (
            0 if item.suggested_action == "one_to_one" else 1,
            0 if item.suggested_action == "group_session" else 1,
            -item.request_count,
            item.cluster_id,
        )
    )

    return ClusterCommandCenterOut(
        course=course,
        course_id=course_id,
        total_requests=len(requests),
        clusters=clusters,
        escalations=build_escalation_feed(
            db, course=course, course_id=course_id, course_ids=course_ids
        )[:8],
        message=(
            "Group similar questions, prefer shared review when a topic repeats, "
            "draft FAQ answers for the KB, and route sensitive cases privately."
        ),
    )


def build_triage_metrics(
    db: Session, *, course_ids: list[int] | None = None
) -> dict:
    request_q = db.query(Request)
    entry_q = db.query(KnowledgeEntry)
    if course_ids is not None:
        request_q = request_q.filter(Request.course_id.in_(course_ids or [-1]))
        entry_q = entry_q.filter(KnowledgeEntry.course_id.in_(course_ids or [-1]))
    requests = request_q.all()
    entries = entry_q.all()
    approved = [entry for entry in entries if entry.status == "approved"]
    pending = [entry for entry in entries if entry.status == "pending_review"]
    with_triage = [request for request in requests if request.triage_trace_json]
    assigned = [request for request in requests if request.assigned_ta]

    time_saved = max(
        0,
        len(with_triage) * (MANUAL_MINUTES_PER_REQUEST - AI_ASSIST_MINUTES_PER_REQUEST),
    )

    recent_traces = []
    for request in sorted(requests, key=lambda item: item.id, reverse=True)[:8]:
        if not request.triage_trace_json:
            continue
        try:
            import json

            trace = json.loads(request.triage_trace_json)
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
                "triage_category": request.triage_category,
            }
        )

    return {
        "total_requests": len(requests),
        "triage_runs": len(with_triage),
        "matched_assignments": len(assigned),
        "kb_pending_review": len(pending),
        "kb_approved": len(approved),
        "kb_growth": len(entries),
        "time_saved_minutes": time_saved,
        "avg_manual_minutes_assumed": MANUAL_MINUTES_PER_REQUEST,
        "avg_ai_assist_minutes_assumed": AI_ASSIST_MINUTES_PER_REQUEST,
        "recent_agent_traces": recent_traces,
    }


def is_sensitive_category(category: str | None) -> bool:
    return (category or "") in SENSITIVE_CATEGORIES


def build_review_insights(db: Session, *, course_id: int) -> ReviewInsightsOut:
    """Chapter / topic signals for review sessions - Quiet ask + Stuck Room, not a new corpus."""
    course = db.get(Course, course_id)
    course_code = course.code if course else None

    request_query = db.query(Request).filter(Request.course_id == course_id)
    requests = request_query.order_by(Request.created_at.desc()).all()
    posts = (
        db.query(HelpPost)
        .filter(HelpPost.course_id == course_id)
        .order_by(HelpPost.created_at.desc())
        .all()
    )

    by_label: dict[str, dict] = {}
    notes = {
        row.topic_key: row
        for row in db.query(ReviewTopicNote)
        .filter(ReviewTopicNote.course_id == course_id)
        .all()
    }

    def bucket(label: str, kind: str) -> dict:
        key = f"{kind}:{label.lower()}"
        if key not in by_label:
            by_label[key] = {
                "topic_key": key,
                "label": label,
                "bucket": kind,
                "office_hours_count": 0,
                "stuck_post_count": 0,
                "samples": [],
                "questions": [],
                "request_ids": [],
                "cluster_ids": [],
            }
        return by_label[key]

    public_requests = 0
    for request in requests:
        category = request.triage_category or request.category or "uncategorized"
        if bool(getattr(request, "sensitive", False)) or is_sensitive_category(
            request.category
        ) or is_sensitive_category(request.triage_category):
            continue
        public_requests += 1
        display = category.replace("_", " ")
        row = bucket(display, "ask_category")
        row["office_hours_count"] += 1
        row["request_ids"].append(request.id)
        if request.cluster_id is not None:
            row["cluster_ids"].append(request.cluster_id)
        text = (request.text or "").strip()
        if text and text not in row["samples"] and len(row["samples"]) < 8:
            row["samples"].append(text[:220])
        if text and len(row["questions"]) < 12:
            row["questions"].append(
                ReviewInsightQuestionOut(
                    source="quiet_ask",
                    text=text[:400],
                    request_id=request.id,
                    cluster_id=request.cluster_id,
                )
            )

    for post in posts:
        label = post.chapter or "Unspecified chapter"
        row = bucket(label, "chapter")
        row["stuck_post_count"] += 1
        sample = (post.title or "").strip()
        if sample and sample not in row["samples"] and len(row["samples"]) < 8:
            row["samples"].append(sample[:220])
        if sample and len(row["questions"]) < 12:
            row["questions"].append(
                ReviewInsightQuestionOut(
                    source="stuck_room",
                    text=sample[:400],
                    stuck_post_id=post.id,
                )
            )

    topics: list[ReviewInsightTopicOut] = []
    for row in by_label.values():
        oh = row["office_hours_count"]
        stuck = row["stuck_post_count"]
        total = oh + stuck
        note = notes.get(row["topic_key"])
        cluster_id = None
        if row["cluster_ids"]:
            cluster_id = Counter(row["cluster_ids"]).most_common(1)[0][0]
        status = (note.review_status if note else None) or (
            "emphasize" if total >= 2 or oh >= 2 or stuck >= 2 else "watch"
        )
        topics.append(
            ReviewInsightTopicOut(
                topic_key=row["topic_key"],
                label=row["label"],
                bucket=row["bucket"],
                office_hours_count=oh,
                stuck_post_count=stuck,
                total_signal=total,
                sample_questions=row["samples"][:3],
                questions=row["questions"],
                request_ids=row["request_ids"],
                cluster_id=cluster_id,
                review_hint=_review_hint(row["label"], oh, stuck),
                emphasize=status == "emphasize" or (
                    note is None and (total >= 2 or oh >= 2 or stuck >= 2)
                ),
                review_status=status,
                next_cohort_note=note.next_cohort_note if note else None,
            )
        )
    topics.sort(key=lambda item: (-item.total_signal, item.label.lower()))

    if not topics:
        message = (
            "No review signals yet. Quiet asks and Stuck Room posts in this course "
            "will group here by triage category and student-labeled chapter."
        )
    else:
        hot = sum(1 for item in topics if item.emphasize)
        message = (
            f"{hot} topic{'s' if hot != 1 else ''} worth emphasizing in the next "
            "review or in the explanation for the following chapter. Sensitive / "
            "private asks stay out of this list."
        )

    return ReviewInsightsOut(
        course_id=course_id,
        course_code=course_code,
        topics=topics,
        office_hours_total=public_requests,
        stuck_post_total=len(posts),
        message=message,
    )


REVIEW_STATUSES = {"watch", "emphasize", "covered"}


def upsert_review_topic_note(
    db: Session,
    *,
    course_id: int,
    topic_key: str,
    review_status: str,
    next_cohort_note: str | None,
) -> ReviewTopicNote:
    status = (review_status or "watch").strip().lower()
    if status not in REVIEW_STATUSES:
        status = "watch"
    key = (topic_key or "").strip()[:200]
    note = (
        db.query(ReviewTopicNote)
        .filter(
            ReviewTopicNote.course_id == course_id,
            ReviewTopicNote.topic_key == key,
        )
        .one_or_none()
    )
    text = (next_cohort_note or "").strip()[:2000] or None
    now = datetime.now(timezone.utc)
    if note is None:
        note = ReviewTopicNote(
            course_id=course_id,
            topic_key=key,
            review_status=status,
            next_cohort_note=text,
            updated_at=now,
        )
        db.add(note)
    else:
        note.review_status = status
        note.next_cohort_note = text
        note.updated_at = now
    db.commit()
    db.refresh(note)
    return note


def _review_hint(label: str, office_hours_count: int, stuck_post_count: int) -> str:
    if stuck_post_count >= 2 and office_hours_count >= 2:
        return (
            f"Both Quiet ask and Stuck Room show {label} - emphasize it in the next "
            "review and consider a FAQ for later cohorts / related chapters."
        )
    if stuck_post_count >= 2:
        return (
            f"Classmates are posting stuck threads on {label} - walk through a simpler "
            "approach in review; a small perspective shift is often the unlock."
        )
    if office_hours_count >= 3:
        return (
            f"{office_hours_count} office-hours asks on {label} - schedule a short "
            "review or draft one FAQ so the next cohort does not repeat the same gap."
        )
    if office_hours_count >= 2:
        return (
            f"Repeated asks on {label} - tighten the explanation before the next "
            "related chapter."
        )
    if stuck_post_count >= 1:
        return (
            f"Early Stuck Room signal on {label} - watch if this grows by chapter end."
        )
    return f"Early office-hours signal on {label} - keep watching."


def _suggest_cluster_action(
    members: list[Request],
    *,
    sensitive_count: int,
    urgency_mix: dict[str, int],
) -> tuple[str, str]:
    count = len(members)
    hard = urgency_mix.get("urgent", 0) + urgency_mix.get("high", 0)
    if sensitive_count > 0 or hard >= max(1, count // 2):
        return (
            "one_to_one",
            "Sensitive or high-urgency cases should stay private - avoid public group review.",
        )
    if count >= GROUP_REVIEW_MIN:
        return (
            "group_session",
            f"{count} similar questions - a short shared review will help more students than separate replies.",
        )
    if count >= FAQ_MIN:
        return (
            "faq",
            f"{count} repeats - draft one FAQ answer for the course KB so the agent can handle the next ask.",
        )
    return (
        "manual_review",
        "Single or thin cluster - keep watching or answer individually.",
    )


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
