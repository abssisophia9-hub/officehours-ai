"""Serialize Request ORM rows into API RequestOut payloads."""

from __future__ import annotations

import json

from app.models.request import OracleResultOut, Request, RequestOut
from app.services.oracle_service import build_oracle_public_payload
from app.services.study_buddy_service import solidarity_payload_for_request


def to_request_out(
    request: Request,
    oracle: dict | None = None,
    *,
    db=None,
) -> RequestOut:
    tags: list[str] = []
    if request.oracle_tags:
        try:
            parsed = json.loads(request.oracle_tags)
            if isinstance(parsed, list):
                tags = [str(item) for item in parsed]
        except json.JSONDecodeError:
            tags = []

    oracle_payload = None
    if oracle is not None:
        oracle_payload = OracleResultOut.model_validate(oracle)
    elif request.oracle_trace_json:
        try:
            trace = json.loads(request.oracle_trace_json)
            oracle_payload = OracleResultOut.model_validate(
                build_oracle_public_payload(trace)
            )
        except Exception:
            oracle_payload = None

    solidarity = {
        "similar_asks_this_week": 0,
        "solidarity_message": None,
        "study_buddy_eligible": False,
    }
    if db is not None:
        solidarity = solidarity_payload_for_request(db, request)

    return RequestOut(
        id=request.id,
        text=request.text,
        anonymous=request.anonymous,
        student_id=request.student_id if not request.anonymous else None,
        student_name=request.student_name if not request.anonymous else None,
        course=request.course,
        course_id=getattr(request, "course_id", None),
        code_snippet=request.code_snippet,
        category=request.category,
        urgency=request.urgency,
        learning_style=request.learning_style,
        cluster_id=request.cluster_id,
        recommended_action=request.recommended_action,
        sensitive=bool(getattr(request, "sensitive", False)),
        help_mode=str(getattr(request, "help_mode", None) or "message"),
        work_status=str(getattr(request, "work_status", None) or "open"),
        claimed_by=getattr(request, "claimed_by", None),
        claimed_by_user_id=getattr(request, "claimed_by_user_id", None),
        claimed_at=getattr(request, "claimed_at", None),
        helped_at=getattr(request, "helped_at", None),
        ta_reply=getattr(request, "ta_reply", None),
        ta_replied_at=getattr(request, "ta_replied_at", None),
        created_at=request.created_at,
        oracle_category=request.oracle_category,
        oracle_difficulty=request.oracle_difficulty,
        oracle_estimated_minutes=request.oracle_estimated_minutes,
        oracle_tags=tags,
        assigned_ta=request.assigned_ta,
        alternative_ta=request.alternative_ta,
        estimated_wait_minutes=request.estimated_wait_minutes,
        student_hint=request.student_hint,
        oracle=oracle_payload,
        similar_asks_this_week=int(solidarity.get("similar_asks_this_week") or 0),
        solidarity_message=solidarity.get("solidarity_message"),
        study_buddy_eligible=bool(solidarity.get("study_buddy_eligible")),
    )
