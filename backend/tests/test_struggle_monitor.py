"""Professor Insights early-warning monitor."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_DEMO"] = "true"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from tests.helpers import professor_auth, student_auth

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_struggle_monitor_demo_seed_and_range():
    headers, course_id = professor_auth(client, "CSC 2302")
    body = client.get(
        f"/analytics/struggle-monitor?course_id={course_id}&range=7d",
        headers=headers,
    ).json()
    assert body["range"] == "7d"
    assert body["kpis"]
    assert any(kpi["key"] == "asks" for kpi in body["kpis"])
    assert isinstance(body["asks_per_day"], list)
    assert body["demo_seeded"] is True or body["kpis"][0]["value"] != "0"

    off = client.get(
        f"/analytics/struggle-monitor?course_id={course_id}&range=30d",
        headers=headers,
    )
    assert off.status_code == 200
    assert off.json()["range"] == "30d"


def test_struggle_monitor_seed_skipped_when_demo_false(monkeypatch):
    from app.database.session import SessionLocal
    from app.services.analytics_service import seed_demo_struggle_volume

    headers, course_id = professor_auth(client, "CSC 2302")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    with SessionLocal() as db:
        assert seed_demo_struggle_volume(db, course_id=course_id) is False
    body = client.get(
        f"/analytics/struggle-monitor?course_id={course_id}&range=7d",
        headers=headers,
    ).json()
    assert body["demo_seeded"] is False


def test_struggle_monitor_demo_seed_on_csc_3374():
    """Sophia's CSC 3374 seat must get a filled monitor in demo mode."""
    headers, course_id = professor_auth(client, "CSC 3374")
    body = client.get(
        f"/analytics/struggle-monitor?course_id={course_id}&range=7d",
        headers=headers,
    ).json()
    assert body["range"] == "7d"
    asks_kpi = next(k for k in body["kpis"] if k["key"] == "asks")
    assert int(asks_kpi["value"]) >= 8
    assert body["enough_for_trend"] is True
    assert body["topics"]
    assert any(
        (k.get("delta_label") or "").endswith("last week")
        or "last week" in (k.get("delta_label") or "")
        for k in body["kpis"]
        if k.get("delta_label")
    )
    assert any("mpi" in (t["topic"] or "").lower() for t in body["topics"])


def test_struggle_monitor_topics_are_request_categories():
    """Bars use Request.category (Ask Triage / free-form), not syllabus chapters.

    Sophia: exam_logistics / conceptual_question are ask categories. Course-like
    slugs (hashing, heaps, mpi) share the same field — Insights UI partitions them.
    """
    headers, course_id = professor_auth(client, "CSC 2302")
    body = client.get(
        f"/analytics/struggle-monitor?course_id={course_id}&range=7d",
        headers=headers,
    ).json()
    assert body["topics"]
    for bar in body["topics"]:
        assert "topic" in bar
        assert isinstance(bar["topic"], str)
        assert bar["topic"].strip()
    # Day series uses ISO dates the UI formats as local "Nov 9".
    for point in body["asks_per_day"]:
        assert len(point["day"].split("-")) == 3
