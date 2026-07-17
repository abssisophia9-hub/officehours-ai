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
            json={"email": "a.benali@aui.ma", "password": DEMO_PASSWORD},
        )
        assert professor.status_code == 200
        payload = professor.json()
        assert payload["token"]
        assert payload["user"]["display_name"]
        codes = {c["code"] for c in payload["user"]["courses"]}
        assert "CS 400" in codes
        assert "CS 330" in codes
        assert {c["role"] for c in payload["user"]["courses"]} == {"professor"}
        assert all(c.get("canvas_course_id") for c in payload["user"]["courses"])

        student = client.post(
            "/auth/login",
            json={"email": "S.Elidrissi@aui.ma", "password": DEMO_PASSWORD},
        ).json()
        assert student["user"]["student_id"] == "117400"
        roles = {c["role"] for c in student["user"]["courses"]}
        assert roles == {"student"}

        me = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {student['token']}"},
        )
        assert me.status_code == 200
        assert me.json()["email"] == "s.elidrissi@aui.ma"


def test_email_does_not_encode_role():
    """AUI emails are Initial.Last@aui.ma for every role."""
    with TestClient(app) as client:
        for email, expected_role in (
            ("a.benali@aui.ma", "professor"),
            ("a.chen@aui.ma", "ta"),
            ("s.elidrissi@aui.ma", "student"),
        ):
            payload = client.post(
                "/auth/login",
                json={"email": email, "password": DEMO_PASSWORD},
            ).json()
            assert all(c["role"] == expected_role for c in payload["user"]["courses"])
            assert "@aui.ma" in payload["user"]["email"]
            local = payload["user"]["email"].split("@", 1)[0]
            assert "." in local
            assert not local.startswith("ta.")
            assert not local.startswith("professor")
            assert not local.startswith("student")


def test_invalid_login_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "a.benali@aui.ma", "password": "wrong"},
        )
        assert response.status_code == 401
