import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"

from app.models.action import RecommendationDecision
from app.models.request import Request
from app.services.request_status_service import (
    STATUS_ACTION_PLANNED,
    STATUS_QUEUED,
    build_request_status,
)


def test_build_request_status_without_decision():
    request = Request(
        id=4,
        text="Need help with graphs.",
        anonymous=True,
        student_id=None,
        category="conceptual_question",
    )

    status = build_request_status(request, [])

    assert status["status"] == STATUS_QUEUED
    assert status["request_code"] == 4


def test_build_request_status_with_approved_decision():
    request = Request(
        id=2,
        text="Can we review integration?",
        anonymous=True,
        student_id=None,
        category="conceptual_question",
    )
    decision = RecommendationDecision(
        id=1,
        card_id="group_session:integration:cluster-1",
        action_kind="group_session",
        action_title="Schedule group review session",
        status="approved",
        cluster_id=1,
        professor_note=None,
        request_ids="[2]",
        action_plan=(
            '{"student_update":"Come during office hours for the group review.",'
            '"agenda_item":{"suggested_window":"Monday, 10:00-11:30"}}'
        ),
    )

    status = build_request_status(request, [decision])

    assert status["status"] == STATUS_ACTION_PLANNED
    assert status["recommended_next_step"] == "Schedule group review session"
    assert status["agenda_hint"] == "Monday, 10:00-11:30"
