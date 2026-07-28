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
        assert "CSC 2302" in codes
        assert "CSC 3323" in codes
        assert "CSC 3374" in codes
        assert {c["role"] for c in payload["user"]["courses"]} == {"professor"}
        assert all(c.get("canvas_course_id") for c in payload["user"]["courses"])

        student = client.post(
            "/auth/login",
            json={"email": "S.Elidrissi@aui.ma", "password": DEMO_PASSWORD},
        ).json()
        assert student["user"]["student_id"] == "117400"
        student_codes = {c["code"] for c in student["user"]["courses"]}
        assert len(student_codes) == 7
        assert "CSC 3374" in student_codes
        assert "COM 1301" in student_codes
        assert "MTH 1304" in student_codes
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
        for email, expected_roles in (
            ("a.benali@aui.ma", {"professor"}),
            # Alice is a TA and a student (different courses).
            ("a.chen@aui.ma", {"ta", "student"}),
            ("s.elidrissi@aui.ma", {"student"}),
        ):
            payload = client.post(
                "/auth/login",
                json={"email": email, "password": DEMO_PASSWORD},
            ).json()
            roles = {c["role"] for c in payload["user"]["courses"]}
            assert roles == expected_roles
            assert "@aui.ma" in payload["user"]["email"]
            local = payload["user"]["email"].split("@", 1)[0]
            assert "." in local
            assert not local.startswith("ta.")
            assert not local.startswith("professor")
            assert not local.startswith("student")


def test_ta_is_also_student_across_courses():
    """Campus reality: one person can TA one course and take others as a student."""
    with TestClient(app) as client:
        alice = client.post(
            "/auth/login",
            json={"email": "a.chen@aui.ma", "password": DEMO_PASSWORD},
        ).json()["user"]
        by_code = {c["code"]: c["role"] for c in alice["courses"]}
        assert by_code["CSC 2302"] == "ta"
        assert by_code["CSC 3323"] == "student"
        assert by_code["MTH 1304"] == "student"
        assert alice["student_id"] == "118110"

        bob = client.post(
            "/auth/login",
            json={"email": "b.martinez@aui.ma", "password": DEMO_PASSWORD},
        ).json()["user"]
        bob_roles = {c["code"]: c["role"] for c in bob["courses"]}
        assert bob_roles["CSC 3374"] == "ta"
        assert bob_roles["COM 1301"] == "student"


def test_invalid_login_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/auth/login",
            json={"email": "a.benali@aui.ma", "password": "wrong"},
        )
        assert response.status_code == 401
