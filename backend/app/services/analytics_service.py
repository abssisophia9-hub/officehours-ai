"""
Professor analytics: struggle heatmap, escalation feed, and cluster command center.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

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
    StruggleAskOut,
    StruggleDayPointOut,
    StruggleHeatmapCell,
    StruggleHeatmapOut,
    StruggleKpiOut,
    StruggleMonitorOut,
    StruggleNeedOut,
    StruggleTopicBarOut,
)
from app.models.request import Request
from app.services.demo_mode import demo_mode

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


OPEN_WORK_STATUSES = frozenset({"open", "claimed", "in_progress"})


def build_escalation_feed(
    db: Session,
    *,
    age_threshold_minutes: int = ESCALATION_AGE_MINUTES,
    course: str | None = None,
    course_id: int | None = None,
    course_ids: list[int] | None = None,
) -> list[EscalationItem]:
    """Open asks that need staff attention (urgent, sensitive, or waiting too long).

    "Urgent and sensitive" is only for unresolved asks (work_status open /
    claimed / in_progress). Helped / resolved rows never appear — age is wait
    time since created_at while still open, not age of a finished ask.
    """
    now = datetime.now(timezone.utc)
    query = db.query(Request)
    if course_id is not None:
        query = query.filter(Request.course_id == course_id)
    elif course_ids is not None:
        query = query.filter(Request.course_id.in_(course_ids or [-1]))
    elif course:
        query = query.filter(Request.course == course)
    requests = query.order_by(Request.created_at.desc()).all()
    # Recurring counts include all asks in the course (context), but only open
    # rows can enter the feed itself.
    category_counts: dict[str, int] = defaultdict(int)
    for request in requests:
        category_counts[request.category or "uncategorized"] += 1

    items: list[EscalationItem] = []
    for request in requests:
        work = str(getattr(request, "work_status", None) or "open").lower()
        if work not in OPEN_WORK_STATUSES:
            continue

        age_minutes = _age_minutes(request.created_at, now)
        urgency = (request.urgency or "").lower()
        category = request.category or "uncategorized"
        sensitive = bool(getattr(request, "sensitive", False)) or category in SENSITIVE_CATEGORIES
        reasons: list[str] = []

        if age_minutes >= age_threshold_minutes:
            reasons.append(f"Waiting {int(age_minutes)}+ minutes with no resolve")
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


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _range_bounds(range_key: str, now: datetime) -> tuple[datetime, datetime, int]:
    key = (range_key or "7d").lower()
    if key == "30d":
        days = 30
    elif key == "term":
        days = 90
    else:
        key = "7d"
        days = 7
    end = now
    start = now - timedelta(days=days)
    return start, end, days


def _delta_label(
    current: float | int,
    previous: float | int,
    *,
    suffix: str = "",
    period: str = "prior",
) -> str:
    diff = float(current) - float(previous)
    if isinstance(current, int) and isinstance(previous, int):
        shown = int(diff)
    else:
        shown = int(round(diff))
    if shown == 0:
        return f"0 vs {period}{suffix}"
    sign = "+" if shown > 0 else ""
    return f"{sign}{shown} vs {period}{suffix}"


def _demo_struggle_samples(course_code: str) -> list[tuple[str, str, str]]:
    """Course-aware demo asks so Insights looks filled on any demo seat."""
    code = (course_code or "").upper()
    if "3374" in code:
        return [
            ("mpi", "Why does MPI_Send block when the matching receive is late?", "high"),
            ("mpi", "When should I use MPI_Isend instead of a blocking send?", "medium"),
            ("mpi", "How do I size the buffer for MPI_Bcast safely?", "medium"),
            ("actors", "How do actor mailboxes avoid shared-memory races?", "high"),
            ("actors", "What happens if an actor crashes mid-message?", "medium"),
            ("csp", "How is CSP rendezvous different from async channels?", "medium"),
            ("distributed", "Why does partial failure break my distributed counter?", "high"),
            ("distributed", "How do I reason about exactly-once delivery here?", "medium"),
        ]
    if "3323" in code:
        return [
            ("complexity", "How do I tighten this Master Theorem case?", "high"),
            ("complexity", "Is this recurrence O(n log n) or worse?", "medium"),
            ("graphs", "Why is Dijkstra wrong on negative edges?", "high"),
            ("graphs", "BFS vs DFS for shortest path on unweighted graphs?", "medium"),
            ("dp", "How do I pick the DP state for this knapsack variant?", "medium"),
            ("dp", "Where does the overlapping subproblem show up?", "low"),
            ("greedy", "When does the greedy choice property fail?", "medium"),
            ("sorting", "Why is heap-sort not stable in our notes?", "low"),
        ]
    return [
        ("red_black_trees", "How do red-black tree rotations restore balance after insert?", "high"),
        ("red_black_trees", "I still miss when to use left vs right rotation on delete.", "medium"),
        ("hashing", "Why do hash collisions use chaining instead of probing here?", "medium"),
        ("hashing", "Walk me through load factor and when to resize the table.", "medium"),
        ("heaps", "Heapify from the middle of the array still confuses me.", "high"),
        ("heaps", "Is decrease-key on a binary heap O(log n) the way we covered?", "low"),
        ("amortized", "I need a clearer picture of amortized vs worst-case for dynamic arrays.", "medium"),
        ("graphs", "BFS vs DFS for shortest path on unweighted graphs?", "medium"),
    ]


def seed_demo_struggle_volume(db: Session, *, course_id: int) -> bool:
    """Demo-only realistic ask volume for Insights video. Never when DEMO=false."""
    if not demo_mode():
        return False
    existing = (
        db.query(Request)
        .filter(Request.course_id == course_id)
        .count()
    )
    if existing >= 24:
        return False
    course = db.query(Course).filter(Course.id == course_id).one_or_none()
    code = course.code if course else "CSC 2302"
    now = datetime.now(timezone.utc)
    samples = _demo_struggle_samples(code)
    created = 0
    # Dense recent window first so 7d / Needs you look like a live monitor.
    schedule: list[tuple[int, int, bool, str]] = []
    for day_back in range(0, 7):
        for idx, (category, text, urgency) in enumerate(samples):
            if (day_back + idx) % 2 != 0 and day_back > 1:
                continue
            schedule.append((day_back, idx, day_back == 0 and idx < 2, urgency))
    for day_back in range(7, 19):
        for idx, (_category, _text, urgency) in enumerate(samples):
            if (day_back + idx) % 3 != 0:
                continue
            schedule.append((day_back, idx, False, urgency))

    for day_back, idx, force_open, urgency in schedule:
        category, text, sample_urgency = samples[idx % len(samples)]
        created_at = now - timedelta(days=day_back, hours=(idx * 3) % 20)
        helped = False if force_open else (day_back + idx) % 4 != 0
        open_urgent = force_open or (not helped and sample_urgency == "high")
        replied = helped or ((day_back + idx) % 5 == 0 and not open_urgent)
        row = Request(
            text=f"{text} (demo seed)",
            anonymous=True,
            course=code,
            course_id=course_id,
            category=category,
            urgency="high" if open_urgent else sample_urgency,
            work_status="helped" if helped else "open",
            created_at=created_at,
            ta_replied_at=(created_at + timedelta(hours=2 + idx % 5)) if replied else None,
            helped_at=(created_at + timedelta(hours=4 + idx % 3)) if helped else None,
            sensitive=False,
        )
        db.add(row)
        created += 1
        if existing + created >= 42:
            break
    if created:
        db.commit()
        return True
    return False


def build_struggle_monitor(
    db: Session,
    *,
    course_id: int,
    range_key: str = "7d",
    topic: str | None = None,
) -> StruggleMonitorOut:
    """Early-warning monitor from real Request / KnowledgeEntry fields only."""
    now = datetime.now(timezone.utc)
    demo_seeded = False
    if demo_mode():
        demo_seeded = seed_demo_struggle_volume(db, course_id=course_id)

    start, end, days = _range_bounds(range_key, now)
    prev_start = start - timedelta(days=days)
    topic_filter = (topic or "").strip() or None

    all_requests = (
        db.query(Request)
        .filter(Request.course_id == course_id)
        .order_by(Request.created_at.desc())
        .all()
    )

    def in_window(row: Request, lo: datetime, hi: datetime) -> bool:
        created = _aware(row.created_at)
        return bool(created and lo <= created < hi)

    current = [r for r in all_requests if in_window(r, start, end)]
    previous = [r for r in all_requests if in_window(r, prev_start, start)]
    if topic_filter:
        current = [
            r
            for r in current
            if (r.category or "uncategorized").lower() == topic_filter.lower()
        ]
        previous = [
            r
            for r in previous
            if (r.category or "uncategorized").lower() == topic_filter.lower()
        ]

    topic_options = sorted(
        {
            (r.category or "uncategorized")
            for r in all_requests
            if (r.category or "").strip()
        }
    )

    approved_cats = {
        (entry.category or "").strip().lower()
        for entry in db.query(KnowledgeEntry)
        .filter(
            KnowledgeEntry.course_id == course_id,
            KnowledgeEntry.status == "approved",
        )
        .all()
        if (entry.category or "").strip()
    }

    asks_n = len(current)
    prev_asks = len(previous)
    resolved_n = sum(
        1 for r in current if str(r.work_status or "").lower() == "helped"
    )
    prev_resolved = sum(
        1 for r in previous if str(r.work_status or "").lower() == "helped"
    )
    resolved_pct = round(100.0 * resolved_n / asks_n, 1) if asks_n else 0.0
    prev_resolved_pct = (
        round(100.0 * prev_resolved / prev_asks, 1) if prev_asks else 0.0
    )

    reply_hours: list[float] = []
    for r in current:
        created = _aware(r.created_at)
        replied = _aware(getattr(r, "ta_replied_at", None))
        if created and replied and replied >= created:
            reply_hours.append((replied - created).total_seconds() / 3600.0)
    prev_reply_hours: list[float] = []
    for r in previous:
        created = _aware(r.created_at)
        replied = _aware(getattr(r, "ta_replied_at", None))
        if created and replied and replied >= created:
            prev_reply_hours.append((replied - created).total_seconds() / 3600.0)

    missing_fields: list[str] = []
    if not any(getattr(r, "ta_replied_at", None) for r in current):
        missing_fields.append(
            "median first-reply uses ta_replied_at; none set in this range"
        )

    median_reply = median(reply_hours) if reply_hours else None
    prev_median_reply = median(prev_reply_hours) if prev_reply_hours else None

    waiting = [
        r
        for r in current
        if str(r.work_status or "open").lower() in OPEN_WORK_STATUSES
        and _age_minutes(r.created_at, now) >= ESCALATION_AGE_MINUTES
    ]
    prev_waiting = [
        r
        for r in previous
        if str(r.work_status or "open").lower() in OPEN_WORK_STATUSES
        and _age_minutes(r.created_at, now) >= ESCALATION_AGE_MINUTES
    ]

    topic_counts = Counter((r.category or "uncategorized") for r in current)
    prev_topic_counts = Counter((r.category or "uncategorized") for r in previous)
    top_topic = topic_counts.most_common(1)[0][0] if topic_counts else None
    period = (
        "last week"
        if days == 7
        else "prior 30 days"
        if days == 30
        else "prior term"
    )

    kpis = [
        StruggleKpiOut(
            key="asks",
            label="Asks",
            value=str(asks_n),
            delta_label=_delta_label(asks_n, prev_asks, period=period),
        ),
        StruggleKpiOut(
            key="resolved_pct",
            label="% resolved",
            value=f"{resolved_pct:.0f}%",
            delta_label=_delta_label(
                resolved_pct, prev_resolved_pct, suffix=" pp", period=period
            ),
        ),
        StruggleKpiOut(
            key="median_first_reply",
            label="Median first reply",
            value=(f"{median_reply:.1f} h" if median_reply is not None else "—"),
            delta_label=(
                _delta_label(
                    median_reply,
                    prev_median_reply or 0.0,
                    suffix=" h",
                    period=period,
                )
                if median_reply is not None and prev_median_reply is not None
                else None
            ),
            missing=(
                "No ta_replied_at in this range"
                if median_reply is None
                else None
            ),
        ),
        StruggleKpiOut(
            key="waiting",
            label="Waiting too long",
            value=str(len(waiting)),
            delta_label=_delta_label(
                len(waiting), len(prev_waiting), period=period
            ),
        ),
        StruggleKpiOut(
            key="top_topic",
            label="Top topic",
            value=(top_topic or "—").replace("_", " "),
            delta_label=(
                _delta_label(
                    topic_counts.get(top_topic, 0),
                    prev_topic_counts.get(top_topic, 0),
                    period=period,
                )
                if top_topic
                else None
            ),
        ),
    ]

    day_counts: dict[str, int] = defaultdict(int)
    cursor = start.date()
    end_day = end.date()
    while cursor <= end_day:
        day_counts[cursor.isoformat()] = 0
        cursor += timedelta(days=1)
    for r in current:
        created = _aware(r.created_at)
        if created:
            day_counts[created.date().isoformat()] += 1
    asks_per_day = [
        StruggleDayPointOut(day=day, count=count)
        for day, count in sorted(day_counts.items())
    ]

    topics: list[StruggleTopicBarOut] = []
    for name, count in topic_counts.most_common():
        prev = prev_topic_counts.get(name, 0)
        if count > prev:
            trend = "up"
        elif count < prev:
            trend = "down"
        else:
            trend = "flat"
        ids = [r.id for r in current if (r.category or "uncategorized") == name]
        topics.append(
            StruggleTopicBarOut(
                topic=name,
                count=count,
                pct=round(100.0 * count / asks_n, 1) if asks_n else 0.0,
                trend=trend,
                has_approved_material=name.lower() in approved_cats,
                request_ids=ids,
            )
        )

    needs: list[StruggleNeedOut] = []
    for bar in topics:
        if bar.count >= 3 and not bar.has_approved_material:
            needs.append(
                StruggleNeedOut(
                    kind="add_material",
                    title=bar.topic.replace("_", " "),
                    detail=f"{bar.count} asks and no approved material for this topic.",
                    action_label="Add material",
                    action_href="/professor",
                    topic=bar.topic,
                    ask_count=bar.count,
                )
            )
    # Struggle Radar overdue lane: open asks waiting more than 24 hours.
    overdue_cut = 24 * 60
    for r in waiting:
        age = float(_age_minutes(r.created_at, now))
        if age < overdue_cut:
            continue
        text = (r.text or "").strip()
        if bool(getattr(r, "anonymous", False)):
            preview = "Anonymous ask waiting too long"
        else:
            preview = text[:120] or f"Ask #{r.id}"
        needs.append(
            StruggleNeedOut(
                kind="overdue_ask",
                title=preview,
                detail=f"Waiting {int(age)} minutes · {(r.category or 'topic').replace('_', ' ')}",
                action_label="Open Your desk",
                action_href="/professor/asks",
                request_id=r.id,
                topic=r.category,
                age_minutes=age,
            )
        )

    enough = asks_n >= 8
    message = (
        "Early warning from live asks in this range."
        if enough
        else "Not enough asks yet for a trend"
    )

    return StruggleMonitorOut(
        range=("30d" if days == 30 else "term" if days == 90 else "7d"),
        topic_filter=topic_filter,
        topic_options=topic_options,
        kpis=kpis,
        asks_per_day=asks_per_day,
        topics=topics,
        needs_you=needs[:24],
        selected_asks=[],
        enough_for_trend=enough,
        missing_fields=missing_fields,
        demo_seeded=demo_seeded,
        message=message,
    )


def struggle_monitor_asks(
    db: Session,
    *,
    course_id: int,
    range_key: str,
    topic: str,
) -> list[StruggleAskOut]:
    """Ask list for a topic bar click — never reveals anonymous identity."""
    now = datetime.now(timezone.utc)
    start, end, _ = _range_bounds(range_key, now)
    topic_key = (topic or "").strip().lower()
    rows = (
        db.query(Request)
        .filter(Request.course_id == course_id)
        .order_by(Request.created_at.desc())
        .all()
    )
    out: list[StruggleAskOut] = []
    for r in rows:
        created = _aware(r.created_at)
        if not created or not (start <= created < end):
            continue
        if (r.category or "uncategorized").lower() != topic_key:
            continue
        anonymous = bool(getattr(r, "anonymous", False))
        text = "Anonymous ask" if anonymous else ((r.text or "").strip()[:220] or f"Ask #{r.id}")
        out.append(
            StruggleAskOut(
                request_id=r.id,
                text=text,
                topic=r.category,
                work_status=str(r.work_status or "open"),
                created_at=created,
                anonymous=anonymous,
            )
        )
    return out[:40]
