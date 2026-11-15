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
