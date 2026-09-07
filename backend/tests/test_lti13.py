"""Canvas LTI 1.3 login initiation, signed launch, and demo-route lock."""

import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.main import app
from app.services import lti13
from app.services.lti13 import CONTEXT_CLAIM, CUSTOM_CLAIM, DEPLOYMENT_CLAIM, MESSAGE_TYPE_CLAIM, ROLES_CLAIM

ISSUER = "https://canvas.aui.ma"
CLIENT = "lti-client-1001"


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture()
def lti_env(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_LTI_ISSUER", ISSUER)
    monkeypatch.setenv("OFFICEHOURS_LTI_CLIENT_ID", CLIENT)
    monkeypatch.setenv("OFFICEHOURS_LTI_LAUNCH_URL", "http://127.0.0.1:8000/lti/launch")
    monkeypatch.setenv("OFFICEHOURS_FRONTEND_URL", "http://127.0.0.1:5180")
    monkeypatch.delenv("OFFICEHOURS_LTI_DEPLOYMENT_ID", raising=False)


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def _token(private_key, *, nonce: str, roles=None, extra=None):
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "aud": CLIENT,
        "sub": "canvas-user-9",
        "exp": now + 300,
        "iat": now,
        "nonce": nonce,
        "email": "S.Abssi@aui.ma",
        "name": "Sophia Abssi",
        MESSAGE_TYPE_CLAIM: "LtiResourceLinkRequest",
        DEPLOYMENT_CLAIM: "1",
        ROLES_CLAIM: roles
        or ["http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"],
        CONTEXT_CLAIM: {"id": "4001", "label": "CSC 2302", "title": "Data Structures"},
        CUSTOM_CLAIM: {"canvas_course_id": "4001", "canvas_user_sis_id": "117027"},
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_config_reports_lti_off_by_default(client, monkeypatch):
    monkeypatch.delenv("OFFICEHOURS_LTI_ISSUER", raising=False)
    monkeypatch.delenv("OFFICEHOURS_LTI_CLIENT_ID", raising=False)
    body = client.get("/auth/config").json()
    assert body["lti"] is False
    assert client.get("/lti/login").status_code == 404


def test_config_reports_lti_on(client, lti_env):
    assert client.get("/auth/config").json()["lti"] is True
    cfg = client.get("/lti/config").json()
    assert cfg["oidc_initiation_url"].endswith("/lti/login")
    assert cfg["target_link_uri"].endswith("/lti/launch")


def test_login_redirects_to_canvas_oidc(client, lti_env):
    response = client.get(
        "/lti/login",
        params={
            "iss": ISSUER,
            "client_id": CLIENT,
            "login_hint": "hint-1",
            "lti_message_hint": "msg-1",
            "target_link_uri": "http://127.0.0.1:8000/lti/launch",
        },
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(f"{ISSUER}/api/lti/authorize_redirect?")
    assert "response_mode=form_post" in location
    assert "login_hint=hint-1" in location
    assert "state=" in location
    assert "nonce=" in location


def test_login_rejects_wrong_issuer(client, lti_env):
    response = client.get(
        "/lti/login",
        params={"iss": "https://evil.example", "login_hint": "x"},
    )
    assert response.status_code == 302
    assert "sso_error=" in response.headers["location"]


def test_launch_provisions_student_from_signed_token(client, lti_env, rsa_key, monkeypatch):
    from app.database.session import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    state = lti13.new_login_state()
    nonce = lti13.peek_nonce(state)
    token = _token(rsa_key, nonce=nonce)
    real_decode = lti13.decode_id_token
    monkeypatch.setattr(
        lti13,
        "decode_id_token",
        lambda id_token, nonce: real_decode(id_token, nonce=nonce, key=rsa_key.public_key()),
    )

    response = client.post("/lti/launch", data={"id_token": token, "state": state})
    assert response.status_code == 302, response.text
    location = response.headers["location"]
    assert location.startswith("http://127.0.0.1:5180/sso#token=")
    assert "&course=" in location
    app_token = location.split("#token=", 1)[1].split("&", 1)[0]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {app_token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "s.abssi@aui.ma"
    assert body["display_name"] == "Sophia Abssi"
    assert body["student_id"] == "117027"
    assert body["courses"][0]["role"] == "student"
    assert body["courses"][0]["canvas_course_id"] == "4001"


def test_launch_maps_instructor_and_ta(rsa_key, lti_env):
    claims = jwt.decode(
        _token(
            rsa_key,
            nonce="n",
            roles=["http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"],
        ),
        rsa_key.public_key(),
        algorithms=["RS256"],
        audience=CLIENT,
        issuer=ISSUER,
    )
    assert lti13.identity_from_claims(claims)["canvas_role"] == "TeacherEnrollment"
    claims[ROLES_CLAIM] = [
        "http://purl.imsglobal.org/vocab/lis/v2/membership/Instructor#TeachingAssistant"
    ]
    assert lti13.identity_from_claims(claims)["canvas_role"] == "TaEnrollment"


def test_launch_rejects_unknown_state(client, lti_env, rsa_key, monkeypatch):
    real_decode = lti13.decode_id_token
    monkeypatch.setattr(
        lti13,
        "decode_id_token",
        lambda id_token, nonce: real_decode(id_token, nonce=nonce, key=rsa_key.public_key()),
    )
    response = client.post(
        "/lti/launch",
        data={"id_token": _token(rsa_key, nonce="x"), "state": "forged"},
    )
    assert response.status_code == 302
    assert "sso_error=" in response.headers["location"]


def test_unsigned_canvas_launch_hidden_when_not_demo(client, monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    monkeypatch.delenv("OFFICEHOURS_CANVAS_LAUNCH_SECRET", raising=False)
    response = client.post(
        "/canvas/launch",
        json={
            "canvas_course_id": "2101",
            "email": "o.tazi@aui.ma",
            "display_name": "Omar Tazi",
            "canvas_role": "StudentEnrollment",
        },
    )
    assert response.status_code == 404
