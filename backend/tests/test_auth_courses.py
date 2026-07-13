import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"

from fastapi.testclient import TestClient

from app.database.session import Base, engine
from app.main import app
from app.services.demo_accounts import DEMO_PASSWORD


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_login_returns_courses_for_roles():
    with TestClient(app) as client:
        professor = client.post(
            "/auth/login",
            json={"email": "professor@aui.ma", "password": DEMO_PASSWORD},
        )
        assert professor.status_code == 200
        payload = professor.json()
        assert payload["token"]
        assert payload["user"]["display_name"]
        codes = {c["code"] for c in payload["user"]["courses"]}
        assert "CS 400" in codes
        assert "CS 330" in codes
        assert {c["role"] for c in payload["user"]["courses"]} == {"professor"}

        student = client.post(
            "/auth/login",
            json={"email": "student@aui.ma", "password": DEMO_PASSWORD},
        ).json()
        assert student["user"]["student_id"] == "117400"
        roles = {c["role"] for c in student["user"]["courses"]}
        assert roles == {"student"}

        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {student['token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == "student@aui.ma"


def test_invalid_login_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "professor@aui.ma", "password": "wrong"},
        )
        assert response.status_code == 401
