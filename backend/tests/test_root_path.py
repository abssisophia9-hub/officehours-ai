"""OFFICEHOURS_ROOT_PATH sub-path deploy (AUI CDN).

Wraps the normal (root) app with PathPrefixASGI so other pytest modules that
imported ``app.main`` without a prefix stay valid. Production wiring in
``app.main`` applies the same wrapper when ``OFFICEHOURS_ROOT_PATH`` is set.
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ.setdefault("OFFICEHOURS_SERVE_FRONTEND", "false")
os.environ.setdefault("OFFICEHOURS_DEMO", "true")

from fastapi.testclient import TestClient

from app.database.session import Base, SessionLocal, engine
from app.main import app as inner_app
from app.path_prefix import PathPrefixASGI
from app.root_path import normalize_root_path
from app.services.demo_accounts import ensure_demo_accounts

PREFIX = "/officehours-ai"
client = TestClient(PathPrefixASGI(inner_app, PREFIX))


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()


def test_normalize_root_path():
    assert normalize_root_path("") == ""
    assert normalize_root_path("/") == ""
    assert normalize_root_path("officehours-ai") == "/officehours-ai"
    assert normalize_root_path("/officehours-ai/") == "/officehours-ai"
    assert normalize_root_path("/officehours-ai") == "/officehours-ai"


def test_health_under_prefix():
    bare = client.get("/health")
    assert bare.status_code == 404
    response = client.get(f"{PREFIX}/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["database_ok"] is True


def test_api_login_under_prefix():
    response = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    )
    assert response.status_code == 200
    assert response.json()["token"]


def test_websocket_under_prefix():
    login = client.post(
        f"{PREFIX}/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    )
    token = login.json()["token"]
    courses = client.get(
        f"{PREFIX}/courses/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert courses.status_code == 200
    course_id = courses.json()[0]["id"]
    with client.websocket_connect(
        f"{PREFIX}/ws?token={token}&course_id={course_id}"
    ) as websocket:
        message = websocket.receive_json()
        assert message["type"] == "connected"
        assert message["payload"]["course_id"] == course_id
