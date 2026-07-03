from datetime import datetime

from app.models.action import RecommendationDecision
from app.models.office_hours import OfficeHoursWindow
from app.services.ics_calendar_service import (
    build_ics_calendar,
    ics_export_available,
    pick_office_hours_window,
)


def _decision(**overrides):
    defaults = {
        "id": 7,
        "card_id": "group_session:test:cluster-1",
        "action_kind": "group_session",
        "action_title": "Schedule group review",
        "status": "approved",
        "cluster_id": 1,
        "professor_note": None,
        "request_ids": "[1,2]",
        "action_plan": "{}",
    }
    defaults.update(overrides)
    return RecommendationDecision(**defaults)


def _window(day="Monday", start="10:00", end="11:30", location="Room 204"):
    return OfficeHoursWindow(
        id=1,
        day=day,
        start=start,
        end=end,
        location=location,
    )


def test_ics_export_available_for_supported_approved_decisions():
    assert ics_export_available(_decision(action_kind="group_session")) is True
    assert ics_export_available(_decision(action_kind="faq")) is False
    assert ics_export_available(_decision(status="dismissed")) is False


def test_pick_office_hours_window_chooses_nearest_upcoming_slot():
    now = datetime(2026, 7, 3, 12, 0)  # Friday
    windows = [
        _window(day="Wednesday", start="14:00", end="15:30", location="Zoom"),
        _window(day="Monday", start="10:00", end="11:30", location="Room 204"),
    ]

    selected = pick_office_hours_window(windows, now=now)

    assert selected.day == "Monday"


def test_build_ics_calendar_contains_event_fields():
    decision = _decision()
    action_plan = {
        "title": "Group review: recursion",
        "summary": "Group review action for 2 related requests.",
    }
    window = _window()
    now = datetime(2026, 7, 3, 9, 0)

    ics = build_ics_calendar(decision, action_plan, window, now=now)

    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Group review: recursion" in ics
    assert "LOCATION:Room 204" in ics
    assert "UID:officehours-decision-7@officehours-ai" in ics
