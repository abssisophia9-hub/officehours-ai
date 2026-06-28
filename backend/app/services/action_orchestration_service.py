"""
Turn professor recommendation decisions into concrete next-step plans.
"""

from __future__ import annotations

from app.ai.summarizer import summarize_request_cluster
from app.models.action import RecommendationDecisionCreate
from app.models.request import Request


def build_action_plan(
    decision: RecommendationDecisionCreate,
    related_requests: list[Request],
) -> dict[str, object]:
    cluster_summary = summarize_request_cluster([request.text for request in related_requests])
    request_count = len(related_requests)
    identified_count = sum(1 for request in related_requests if not request.anonymous)
    anonymous_count = request_count - identified_count

    if decision.status == "dismissed":
        return {
            "plan_type": "dismissed",
            "title": "Dismissed recommendation",
            "summary": "Professor dismissed this recommendation card.",
            "agenda_item": None,
            "calendar": None,
            "student_update": "No automated student-facing update is sent.",
            "privacy": _privacy_summary(identified_count, anonymous_count),
            "cluster_summary": cluster_summary,
        }

    strategy = _strategy_for(decision.action_kind)
    title = f"{strategy['title_prefix']}: {cluster_summary['title']}"
    summary = _summary(decision, strategy, request_count)

    return {
        "plan_type": decision.action_kind,
        "title": title,
        "summary": summary,
        "agenda_item": {
            "label": title,
            "suggested_window": strategy["window"],
            "format": strategy["format"],
            "walk_in_policy": "Keep office hours open; this block gives students a shared starting point, not a hard appointment gate.",
        },
        "calendar": {
            "suggestion": strategy["calendar"],
            "ics_ready": False,
            "description": summary,
        },
        "student_update": _student_update(decision, strategy),
        "privacy": _privacy_summary(identified_count, anonymous_count),
        "cluster_summary": cluster_summary,
    }


def _strategy_for(action_kind: str) -> dict[str, str]:
    strategies = {
        "group_session": {
            "title_prefix": "Group review",
            "window": "Next office-hours block, 15-20 minutes",
            "format": "Open walk-in mini-session",
            "calendar": "Add an optional office-hours agenda block",
            "student_update": "Your request was grouped into a shared review topic. Come during office hours and look for this agenda item.",
        },
        "faq": {
            "title_prefix": "FAQ answer",
            "window": "Before or at start of next office hours",
            "format": "Posted answer / kiosk status update",
            "calendar": "No calendar block needed",
            "student_update": "A professor-approved answer is being prepared for this repeated question.",
        },
        "one_to_one": {
            "title_prefix": "Priority follow-up",
            "window": "Earliest professor availability",
            "format": "Private 1:1 follow-up",
            "calendar": "Suggest a private follow-up slot",
            "student_update": "Please attend office hours and mention your request code, or watch for direct follow-up if you submitted identified.",
        },
        "ta_support": {
            "title_prefix": "TA support",
            "window": "Next TA/project support block",
            "format": "Small-group troubleshooting",
            "calendar": "Add optional TA support agenda item",
            "student_update": "Your request was routed toward project/TA support.",
        },
        "admin_route": {
            "title_prefix": "Private admin route",
            "window": "Professor/private admin review",
            "format": "Private follow-up",
            "calendar": "Do not place on public office-hours board",
            "student_update": "This request needs private follow-up and will not be shown on a public board.",
        },
        "manual_review": {
            "title_prefix": "Manual review",
            "window": "Professor review queue",
            "format": "Professor decides next action",
            "calendar": "No calendar block until professor chooses action",
            "student_update": "Your request is queued for professor review.",
        },
    }

    return strategies.get(action_kind, strategies["manual_review"])


def _summary(
    decision: RecommendationDecisionCreate,
    strategy: dict[str, str],
    request_count: int,
) -> str:
    note = f" Professor note: {decision.professor_note.strip()}" if decision.professor_note else ""
    return (
        f"{strategy['title_prefix']} action for {request_count} related request"
        f"{'' if request_count == 1 else 's'}. {decision.action_title}.{note}"
    )


def _student_update(
    decision: RecommendationDecisionCreate,
    strategy: dict[str, str],
) -> str:
    if decision.status == "editing":
        return "Professor is editing the recommendation before students are notified."

    return strategy["student_update"]


def _privacy_summary(identified_count: int, anonymous_count: int) -> dict[str, object]:
    return {
        "identified_requests": identified_count,
        "anonymous_requests": anonymous_count,
        "identified_delivery": "Direct notification can be added later via roster/email integration.",
        "anonymous_delivery": "Use request code or public anonymized status board; do not expose student identity.",
    }
