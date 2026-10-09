"""Shared login helpers for API tests after campus routes require auth."""

from app.services.demo_accounts import DEMO_PASSWORD

PROFESSOR = "a.benali@aui.ma"
STUDENT = "s.elidrissi@aui.ma"
TA_ALICE = "a.chen@aui.ma"


def login(client, email=STUDENT):
    response = client.post(
        "/auth/login", json={"email": email, "password": DEMO_PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    user = response.json()["user"]
    return {"Authorization": f"Bearer {token}"}, user


def course_id_for(user, code="CSC 3374"):
    match = next((c for c in user["courses"] if c["code"] == code), None)
    assert match, f"no course {code} on {user.get('email')}"
    return match["id"]


def student_auth(client, code="CSC 3374"):
    headers, user = login(client, STUDENT)
    return headers, course_id_for(user, code)


def professor_auth(client, code="CSC 2302"):
    headers, user = login(client, PROFESSOR)
    return headers, course_id_for(user, code)


def alice_auth(client, code="CSC 2302"):
    headers, user = login(client, TA_ALICE)
    return headers, course_id_for(user, code)


def post_student_request(client, text, *, code="CSC 3374", **extra):
    headers, course_id = student_auth(client, code)
    payload = {
        "text": text,
        "anonymous": extra.pop("anonymous", True),
        "course_id": extra.pop("course_id", course_id),
        "course": extra.pop("course", code),
        **extra,
    }
    response = client.post("/requests/", headers=headers, json=payload)
    return response, headers, payload["course_id"]
