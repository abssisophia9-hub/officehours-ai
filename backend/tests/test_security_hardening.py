"""Production security controls: rate limit, uploads, MS JWT, CORS, validation."""

from __future__ import annotations

import os
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

# Configure before importing the app.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
os.environ["OFFICEHOURS_RATE_LIMIT"] = "false"
os.environ["OFFICEHOURS_DEMO"] = "true"
os.environ["OFFICEHOURS_TRUST_PROXY"] = "false"

from app.database.session import Base, SessionLocal, engine
from app.main import app
from app.services import microsoft_sso
from app.services.demo_accounts import ensure_demo_accounts
from app.services.rate_limit import DEFAULT_LIMITS, limiter, rate_limit_enabled
from app.services.upload_security import assert_upload_allowed, safe_filename

client = TestClient(app)


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_demo_accounts(db)
    finally:
        db.close()
    limiter.reset()


def test_login_rejects_short_password():
    response = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "short"},
    )
    assert response.status_code == 422


def test_request_text_max_length_enforced():
    login = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["token"]
    course_id = login.json()["user"]["courses"][0]["id"]
    response = client.post(
        "/requests/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "text": "x" * 8001,
            "anonymous": True,
            "course_id": course_id,
        },
    )
    assert response.status_code == 422


def test_security_headers_and_request_id():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers.get("X-Request-Id")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"


def test_cors_allow_list_not_star():
    from app.main import _cors_origins

    origins = _cors_origins()
    assert "*" not in origins
    assert any("5180" in origin for origin in origins)


def test_ta_roster_requires_staff():
    student = client.post(
        "/auth/login",
        json={"email": "s.elidrissi@aui.ma", "password": "aui-demo"},
    ).json()
    denied = client.get(
        "/ta/roster/",
        headers={"Authorization": f"Bearer {student['token']}"},
    )
    assert denied.status_code == 403

    ta = client.post(
        "/auth/login",
        json={"email": "a.chen@aui.ma", "password": "aui-demo"},
    ).json()
    ok = client.get(
        "/ta/roster/",
        headers={"Authorization": f"Bearer {ta['token']}"},
    )
    assert ok.status_code == 200


def test_rate_limit_blocks_login_when_enabled(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_RATE_LIMIT", "true")
    assert rate_limit_enabled() is True
    limiter.reset()
    limit, _window = DEFAULT_LIMITS["/auth/login"]
    last = None
    for _ in range(limit + 2):
        last = client.post(
            "/auth/login",
            json={"email": "nobody@aui.ma", "password": "aui-demo-xx"},
        )
    assert last is not None
    assert last.status_code == 429
    monkeypatch.setenv("OFFICEHOURS_RATE_LIMIT", "false")
    limiter.reset()


def test_upload_magic_bytes_reject_mismatch():
    with pytest.raises(Exception) as exc:
        assert_upload_allowed(
            filename="notes.pdf",
            data=b"not-a-pdf-file",
            allowed_extensions={".pdf"},
            max_bytes=1_000_000,
        )
    assert exc.value.status_code == 400


def test_upload_magic_bytes_accept_pdf():
    ext = assert_upload_allowed(
        filename="notes.pdf",
        data=b"%PDF-1.4 minimal",
        allowed_extensions={".pdf"},
        max_bytes=1_000_000,
    )
    assert ext == ".pdf"
    assert safe_filename("../etc/passwd.pdf") == "passwd.pdf"


def test_microsoft_id_token_requires_valid_signature(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_MS_TENANT_ID", "tenant-1")
    monkeypatch.setenv("OFFICEHOURS_MS_CLIENT_ID", "client-1")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = int(time.time())
    good = jwt.encode(
        {
            "iss": "https://login.microsoftonline.com/tenant-1/v2.0",
            "aud": "client-1",
            "tid": "tenant-1",
            "exp": now + 300,
            "iat": now,
            "email": "s.abssi@aui.ma",
            "name": "Sophia",
        },
        private_key,
        algorithm="RS256",
    )
    claims = microsoft_sso.claims_from_id_token(good, key=private_key.public_key())
    assert claims["email"] == "s.abssi@aui.ma"

    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    forged = jwt.encode(
        {
            "iss": "https://login.microsoftonline.com/tenant-1/v2.0",
            "aud": "client-1",
            "tid": "tenant-1",
            "exp": now + 300,
            "iat": now,
            "email": "evil@aui.ma",
        },
        other,
        algorithm="RS256",
    )
    with pytest.raises(Exception):
        microsoft_sso.claims_from_id_token(forged, key=private_key.public_key())


def test_unhandled_error_does_not_leak_traceback():
    @app.get("/__test_boom")
    def _boom():
        raise RuntimeError("secret stack detail")

    quiet = TestClient(app, raise_server_exceptions=False)
    response = quiet.get("/__test_boom")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error."
    assert "secret stack" not in response.text
