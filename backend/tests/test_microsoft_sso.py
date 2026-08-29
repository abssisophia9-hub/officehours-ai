"""Microsoft Entra ID sign-in: config flag, redirect, callback, and guards."""

import base64
import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import microsoft_sso

TENANT = "7025e04c-70ca-48bf-ab7b-73954cb846ad"
CLIENT = "11111111-2222-3333-4444-555555555555"


def _fake_id_token(claims: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJSUzI1NiJ9.{payload}.signature"


@pytest.fixture()
def ms_env(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_MS_TENANT_ID", TENANT)
    monkeypatch.setenv("OFFICEHOURS_MS_CLIENT_ID", CLIENT)
    monkeypatch.setenv("OFFICEHOURS_MS_CLIENT_SECRET", "s3cret")
    monkeypatch.setenv("OFFICEHOURS_FRONTEND_URL", "http://127.0.0.1:5180")


@pytest.fixture()
def client():
    return TestClient(app, follow_redirects=False)


def test_config_reports_microsoft_off_by_default(client, monkeypatch):
    monkeypatch.delenv("OFFICEHOURS_MS_TENANT_ID", raising=False)
    monkeypatch.delenv("OFFICEHOURS_MS_CLIENT_ID", raising=False)
    monkeypatch.delenv("OFFICEHOURS_MS_CLIENT_SECRET", raising=False)
    config = client.get("/auth/config").json()
    assert config["microsoft"] is False
    assert client.get("/auth/microsoft/login").status_code == 404


def test_config_reports_microsoft_on_when_configured(client, ms_env):
    assert client.get("/auth/config").json()["microsoft"] is True


def test_login_redirects_to_aui_tenant(client, ms_env):
    response = client.get("/auth/microsoft/login")
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith(f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize?")
    assert f"client_id={CLIENT}" in location
    assert "scope=openid+profile+email" in location
    assert "state=" in location


def test_callback_creates_user_and_hands_token_to_spa(client, ms_env, monkeypatch):
    claims = {
        "aud": CLIENT,
        "tid": TENANT,
        "email": "S.Abssi@aui.ma",
        "name": "Sophia Abssi",
    }
    monkeypatch.setattr(
        microsoft_sso, "exchange_code", lambda code: {"id_token": _fake_id_token(claims)}
    )
    state = microsoft_sso.new_state()
    response = client.get(f"/auth/microsoft/callback?code=abc&state={state}")
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("http://127.0.0.1:5180/sso#token=")

    token = location.split("#token=", 1)[1]
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "s.abssi@aui.ma"
    assert body["display_name"] == "Sophia Abssi"

    # SSO accounts never get a usable password.
    login = client.post(
        "/auth/login", json={"email": "s.abssi@aui.ma", "password": "anything"}
    )
    assert login.status_code == 401


def test_callback_rejects_foreign_domain(client, ms_env, monkeypatch):
    claims = {"aud": CLIENT, "tid": TENANT, "email": "someone@gmail.com", "name": "X"}
    monkeypatch.setattr(
        microsoft_sso, "exchange_code", lambda code: {"id_token": _fake_id_token(claims)}
    )
    state = microsoft_sso.new_state()
    response = client.get(f"/auth/microsoft/callback?code=abc&state={state}")
    assert response.status_code == 302
    assert "sso_error=" in response.headers["location"]
    assert "aui.ma" in response.headers["location"]


def test_callback_rejects_wrong_audience(client, ms_env, monkeypatch):
    claims = {"aud": "another-app", "tid": TENANT, "email": "s.abssi@aui.ma"}
    monkeypatch.setattr(
        microsoft_sso, "exchange_code", lambda code: {"id_token": _fake_id_token(claims)}
    )
    state = microsoft_sso.new_state()
    response = client.get(f"/auth/microsoft/callback?code=abc&state={state}")
    assert response.status_code == 302
    assert "sso_error=" in response.headers["location"]


def test_callback_rejects_unknown_or_reused_state(client, ms_env, monkeypatch):
    monkeypatch.setattr(
        microsoft_sso,
        "exchange_code",
        lambda code: {"id_token": _fake_id_token({"aud": CLIENT, "tid": TENANT, "email": "a.b@aui.ma"})},
    )
    response = client.get("/auth/microsoft/callback?code=abc&state=forged")
    assert response.status_code == 302
    assert "sso_error=" in response.headers["location"]

    state = microsoft_sso.new_state()
    first = client.get(f"/auth/microsoft/callback?code=abc&state={state}")
    assert "#token=" in first.headers["location"]
    replay = client.get(f"/auth/microsoft/callback?code=abc&state={state}")
    assert "sso_error=" in replay.headers["location"]


def test_callback_surfaces_microsoft_error(client, ms_env):
    response = client.get(
        "/auth/microsoft/callback?error=access_denied&error_description=User+cancelled"
    )
    assert response.status_code == 302
    assert "sso_error=User+cancelled" in response.headers["location"]
