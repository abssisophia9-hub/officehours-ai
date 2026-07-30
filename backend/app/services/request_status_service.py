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
STATUS_TA_HELPING = "ta_helping"
STATUS_TA_REPLIED = "ta_replied"
STATUS_HELPED = "helped"


def build_request_status(
    request: Request,
    decisions: list[RecommendationDecision],
) -> dict[str, object]:
    latest_decision = _latest_decision_for_request(request.id, decisions)
    status, headline, message = _status_copy(request, latest_decision)

    work = str(getattr(request, "work_status", None) or "open")
    claimed_by = getattr(request, "claimed_by", None)
    ta_reply = getattr(request, "ta_reply", None)

    payload: dict[str, object] = {
        "request_code": request.id,
        "status": status,
        "headline": headline,
        "message": message,
        "category": request.category,
        "submitted_at": request.created_at,
        "anonymous_submission": request.anonymous,
        "help_mode": getattr(request, "help_mode", None) or "message",
        "work_status": work,
        "claimed_by": claimed_by,
        "ta_reply": ta_reply,
        "student_hint": getattr(request, "student_hint", None),
        "assigned_ta": getattr(request, "assigned_ta", None),
        "estimated_wait_minutes": getattr(request, "estimated_wait_minutes", None),
    }

    if latest_decision and latest_decision.status == "approved":
        action_plan = json.loads(latest_decision.action_plan)
        payload["recommended_next_step"] = latest_decision.action_title
        if action_plan.get("agenda_item"):
            payload["agenda_hint"] = action_plan["agenda_item"]["suggested_window"]
    elif ta_reply:
        payload["recommended_next_step"] = (
            "A TA sent you a reply — read it above and follow up in office hours "
            "if you still need help."
        )
    else:
        help_mode = str(getattr(request, "help_mode", None) or "message")
        if work == "in_progress":
            who = claimed_by or request.assigned_ta or "a TA"
            payload["recommended_next_step"] = (
                f"{who} is helping with your ask now."
            )
        elif work == "claimed":
            who = claimed_by or request.assigned_ta or "a TA"
            payload["recommended_next_step"] = (
                f"{who} claimed your ask and will follow up soon."
            )
        elif work == "helped":
            payload["recommended_next_step"] = (
                "A TA marked this as helped. Visit office hours if you still need more."
            )
        elif help_mode == "face_to_face":
            payload["recommended_next_step"] = (
                "You asked for a face-to-face meeting — keep your request code and "
                "check campus office-hours times for your course."
            )
        elif help_mode == "online_meeting":
            payload["recommended_next_step"] = (
                "You asked for an online meeting — a TA or the professor will share "
                "a link once a slot is offered."
            )

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
    if getattr(request, "ta_reply", None):
        return (
            STATUS_TA_REPLIED,
            "TA reply ready",
            str(request.ta_reply),
        )

    work = str(getattr(request, "work_status", None) or "open")
    if work == "in_progress":
        who = getattr(request, "claimed_by", None) or request.assigned_ta or "A TA"
        return (
            STATUS_TA_HELPING,
            "TA is helping",
            f"{who} is working on your ask right now.",
        )
    if work == "claimed":
        who = getattr(request, "claimed_by", None) or request.assigned_ta or "A TA"
        return (
            STATUS_TA_HELPING,
            "Claimed by a TA",
            f"{who} claimed your ask and will follow up soon.",
        )
    if work == "helped":
        return (
            STATUS_HELPED,
            "Marked helped",
            "A TA finished helping with this ask. Come to office hours if you need more.",
        )

    if decision is None:
        return (
            STATUS_QUEUED,
            "Waiting in queue",
            "Your request is in the TA / professor review queue. Check back after office hours for updates.",
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
