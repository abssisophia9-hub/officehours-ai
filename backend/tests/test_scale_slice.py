"""Postgres-ready engine, pagination envelopes, inbox notify, gold evaluate."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_RATE_LIMIT"] = "false"
os.environ["OFFICEHOURS_ALLOW_RETRAIN"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts
from app.database.session import SessionLocal
from app.services.pagination import page_or_list

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def _login(email: str) -> dict:
    body = client.post(
        "/auth/login",
        json={"email": email, "password": "aui-demo"},
    ).json()
    return {
        "headers": {"Authorization": f"Bearer {body['token']}"},
        "user": body["user"],
    }


def _course(user: dict, code: str) -> int:
    return next(c["id"] for c in user["courses"] if c["code"] == code)


def test_health_reports_sqlite_dialect():
    health = client.get("/health").json()
    assert health["database"] == "sqlite"


def test_page_or_list_compat_and_envelope():
    rows = [1, 2, 3, 4]
    assert page_or_list(rows, limit=None, offset=0) == rows
    page = page_or_list(rows, limit=2, offset=2)
    assert page["items"] == [3, 4]
    assert page["total"] == 4
    assert page["has_more"] is False


def test_ta_queue_page_envelope():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    client.post(
        "/requests/",
        headers=student["headers"],
        json={
            "text": "Why is dequeue O(n) on a Python list used as a queue?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    )
    raw = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all",
        headers=alice["headers"],
    )
    assert raw.status_code == 200
    assert isinstance(raw.json(), list)
    page = client.get(
        f"/ta/queue/?course_id={course_id}&assignment=all&limit=1&offset=0",
        headers=alice["headers"],
    )
    assert page.status_code == 200
    body = page.json()
    assert "items" in body
    assert body["limit"] == 1
    assert body["total"] >= 1


def test_claim_writes_inbox_for_submitter():
    student = _login("s.elidrissi@aui.ma")
    alice = _login("a.chen@aui.ma")
    course_id = _course(student["user"], "CSC 2302")
    created = client.post(
        "/requests/",
        headers=student["headers"],
        json={
            "text": "Hash collisions on insert — anyone?",
            "anonymous": True,
            "course": "CSC 2302",
            "course_id": course_id,
        },
    ).json()
    claim = client.post(
        "/ta/claim/",
        headers=alice["headers"],
        json={"request_id": created["id"]},
    )
    assert claim.status_code == 200, claim.text
    inbox = client.get("/notifications/", headers=student["headers"]).json()
    assert inbox["unread"] >= 1
    assert any("claimed" in (item["kind"] or "") for item in inbox["items"])
    assert inbox["smtp_configured"] is False


def test_retrain_evaluates_without_rewriting_joblib():
    prof = _login("a.benali@aui.ma")
    course_id = _course(prof["user"], "CSC 2302")
    result = client.post(
        f"/analytics/retrain?course_id={course_id}&apply_models=false",
        headers=prof["headers"],
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["n_labels"] >= 1
    assert body["applied_models"] is False
    student = _login("s.elidrissi@aui.ma")
    denied = client.post(
        f"/analytics/retrain?course_id={course_id}",
        headers=student["headers"],
    )
    assert denied.status_code == 403
