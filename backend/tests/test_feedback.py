"""Account-menu bug report endpoint."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services.demo_accounts import ensure_demo_accounts

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def test_bug_report_requires_auth():
    response = client.post(
        "/feedback/bugs",
        json={"title": "Broken", "body": "Something failed"},
    )
    assert response.status_code == 401


def test_bug_report_saved():
    token = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    ).json()["token"]
    created = client.post(
        "/feedback/bugs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Classmate notes download failed",
            "body": "Download button spun forever on Safari.",
            "role": "student",
            "course_code": "CSC 2302",
            "page_path": "/student",
        },
    )
    assert created.status_code == 201, created.text
    payload = created.json()
    assert payload["title"].startswith("Classmate")
    assert payload["course_code"] == "CSC 2302"
    assert payload["id"] >= 1
