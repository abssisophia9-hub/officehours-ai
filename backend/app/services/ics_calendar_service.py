"""
Generate RFC 5545 calendar exports for professor-approved action plans.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

from app.models.action import RecommendationDecision
from app.models.office_hours import OfficeHoursWindow

DAY_TO_WEEKDAY = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
}

ICS_EXPORT_KINDS = {"group_session", "one_to_one", "ta_support"}


def ics_export_available(decision: RecommendationDecision) -> bool:
    if decision.status in {"dismissed", "editing"}:
        return False
    return decision.action_kind in ICS_EXPORT_KINDS


def pick_office_hours_window(
    windows: list[OfficeHoursWindow],
    *,
    now: datetime | None = None,
) -> OfficeHoursWindow | None:
    if not windows:
        return None

    current = now or datetime.now()
    ranked = sorted(
        windows,
        key=lambda window: _next_window_start(current, window),
    )
    return ranked[0]


def build_ics_calendar(
    decision: RecommendationDecision,
    action_plan: dict[str, object],
    window: OfficeHoursWindow,
    *,
    now: datetime | None = None,
) -> str:
    current = now or datetime.now()
    start = _next_window_start(current, window)
    end = _combine_day_and_time(start.date(), window.end)
    summary = str(action_plan.get("title", decision.action_title))
    description = str(action_plan.get("summary", decision.action_title))
    meeting = action_plan.get("meeting") if isinstance(action_plan.get("meeting"), dict) else {}
    location = str(
        meeting.get("place")
        or (action_plan.get("agenda_item") or {}).get("place")
        or window.location
    )
    uid = f"officehours-decision-{decision.id}@officehours-ai"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//OfficeHours AI//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{_format_ics_datetime(current)}",
        f"DTSTART:{_format_ics_datetime(start)}",
        f"DTEND:{_format_ics_datetime(end)}",
        f"SUMMARY:{_escape_ics_text(summary)}",
        f"DESCRIPTION:{_escape_ics_text(description)}",
        f"LOCATION:{_escape_ics_text(location)}",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines) + "\r\n"


def office_hours_snapshot(window: OfficeHoursWindow) -> dict[str, str]:
    return {
        "day": window.day,
        "start": window.start,
        "end": window.end,
        "location": window.location,
    }


def _next_window_start(now: datetime, window: OfficeHoursWindow) -> datetime:
    target_weekday = DAY_TO_WEEKDAY[window.day]
    days_ahead = (target_weekday - now.weekday()) % 7
    candidate_date = now.date() + timedelta(days=days_ahead)
    candidate_start = _combine_day_and_time(candidate_date, window.start)

    if candidate_start <= now:
        candidate_start = _combine_day_and_time(
            candidate_date + timedelta(days=7),
            window.start,
        )

    return candidate_start


def _combine_day_and_time(day: date, time_value: str) -> datetime:
    hour, minute = map(int, time_value.split(":"))
    return datetime(day.year, day.month, day.day, hour, minute)


def _format_ics_datetime(value: datetime) -> str:
    return value.strftime("%Y%m%dT%H%M%S")


def _escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )
