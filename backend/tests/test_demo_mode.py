"""Demo seed stays off unless OFFICEHOURS_DEMO is explicitly on."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.models.auth import User
from app.services.demo_accounts import ensure_demo_accounts


client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_auth_config_reports_demo_flag():
    body = client.get("/auth/config").json()
    assert "demo" in body
    assert "canvas_mode" in body


def test_production_flag_does_not_invent_demo_users(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
        assert db.query(User).count() == 0
    finally:
        db.close()
    denied = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    )
    assert denied.status_code == 401
