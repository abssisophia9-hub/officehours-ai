"""Serialize Request ORM rows into API RequestOut payloads."""

from __future__ import annotations

import json

from app.models.request import OracleResultOut, Request, RequestOut
from app.services.oracle_service import build_oracle_public_payload


def to_request_out(request: Request, oracle: dict | None = None) -> RequestOut:
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

    return RequestOut(
        id=request.id,
        text=request.text,
        anonymous=request.anonymous,
        student_id=request.student_id,
        student_name=request.student_name,
        course=request.course,
        code_snippet=request.code_snippet,
        category=request.category,
        urgency=request.urgency,
        learning_style=request.learning_style,
        cluster_id=request.cluster_id,
        recommended_action=request.recommended_action,
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
    )
