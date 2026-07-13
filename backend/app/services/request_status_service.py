"""
Build privacy-safe request status responses for anonymous student lookup.
"""

from __future__ import annotations

import json

from app.models.action import RecommendationDecision
from app.models.request import Request

STATUS_QUEUED = "queued"
STATUS_UNDER_REVIEW = "under_review"
STATUS_ACTION_PLANNED = "action_planned"
STATUS_CLOSED = "closed"


def build_request_status(
    request: Request,
    decisions: list[RecommendationDecision],
) -> dict[str, object]:
    latest_decision = _latest_decision_for_request(request.id, decisions)
    status, headline, message = _status_copy(request, latest_decision)

    payload: dict[str, object] = {
        "request_code": request.id,
        "status": status,
        "headline": headline,
        "message": message,
        "category": request.category,
        "submitted_at": request.created_at,
        "anonymous_submission": request.anonymous,
        "student_hint": getattr(request, "student_hint", None),
        "assigned_ta": getattr(request, "assigned_ta", None),
        "estimated_wait_minutes": getattr(request, "estimated_wait_minutes", None),
    }

    if latest_decision and latest_decision.status == "approved":
        action_plan = json.loads(latest_decision.action_plan)
        payload["recommended_next_step"] = latest_decision.action_title
        if action_plan.get("agenda_item"):
            payload["agenda_hint"] = action_plan["agenda_item"]["suggested_window"]

    return payload


def _latest_decision_for_request(
    request_id: int,
    decisions: list[RecommendationDecision],
) -> RecommendationDecision | None:
    matching = [
        decision
        for decision in decisions
        if request_id in json.loads(decision.request_ids)
    ]
    if not matching:
        return None

    return max(matching, key=lambda decision: decision.updated_at)


def _status_copy(
    request: Request,
    decision: RecommendationDecision | None,
) -> tuple[str, str, str]:
    if decision is None:
        return (
            STATUS_QUEUED,
            "Waiting in queue",
            "Your request is in the professor review queue. Check back after office hours for updates.",
        )

    action_plan = json.loads(decision.action_plan)

    if decision.status == "approved":
        student_update = str(
            action_plan.get(
                "student_update",
                "A professor-approved next step is ready for this request.",
            )
        )
        return STATUS_ACTION_PLANNED, "Next step ready", student_update

    if decision.status == "editing":
        return (
            STATUS_UNDER_REVIEW,
            "Professor is reviewing",
            "A professor is editing the recommended next step before any student update is posted.",
        )

    return (
        STATUS_CLOSED,
        "No public update",
        "This request will not receive an automated public status update. Visit office hours if you still need help.",
    )
