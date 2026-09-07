"""Microsoft Entra ID (Azure AD) sign-in for the AUI tenant.

OAuth 2.0 authorization-code flow as a confidential client. Enabled only when
the app registration env vars are present:

    OFFICEHOURS_MS_TENANT_ID      AUI directory (tenant) ID
    OFFICEHOURS_MS_CLIENT_ID      App registration "Application (client) ID"
    OFFICEHOURS_MS_CLIENT_SECRET  Client secret value
    OFFICEHOURS_MS_REDIRECT_URI   This API's callback URL
                                  (default http://127.0.0.1:8000/auth/microsoft/callback)
    OFFICEHOURS_FRONTEND_URL      Where to send the browser after sign-in
                                  (default http://127.0.0.1:5180)
    OFFICEHOURS_MS_ALLOWED_DOMAIN Email domain allowed to sign in (default aui.ma)

The id_token is verified with Microsoft's JWKS (RS256), plus audience, issuer,
tenant, and expiry checks.
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt

_STATE_TTL_SECONDS = 600
_pending_states: dict[str, float] = {}


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def microsoft_enabled() -> bool:
    return bool(
        _env("OFFICEHOURS_MS_TENANT_ID")
        and _env("OFFICEHOURS_MS_CLIENT_ID")
        and _env("OFFICEHOURS_MS_CLIENT_SECRET")
    )


def frontend_url() -> str:
    return _env("OFFICEHOURS_FRONTEND_URL") or "http://127.0.0.1:5180"


def redirect_uri() -> str:
    return _env("OFFICEHOURS_MS_REDIRECT_URI") or "http://127.0.0.1:8000/auth/microsoft/callback"


def allowed_domain() -> str:
    return (_env("OFFICEHOURS_MS_ALLOWED_DOMAIN") or "aui.ma").lower().lstrip("@")


def _authority() -> str:
    return f"https://login.microsoftonline.com/{_env('OFFICEHOURS_MS_TENANT_ID')}"


def _issuer() -> str:
    # v2.0 tokens use this issuer form.
    return f"{_authority()}/v2.0"


def _jwks_url() -> str:
    return f"{_authority()}/discovery/v2.0/keys"


def new_state() -> str:
    now = time.time()
    for state, expires in list(_pending_states.items()):
        if expires < now:
            _pending_states.pop(state, None)
    state = secrets.token_urlsafe(24)
    _pending_states[state] = now + _STATE_TTL_SECONDS
    return state


def consume_state(state: str) -> bool:
    expires = _pending_states.pop(state, None)
    return expires is not None and expires >= time.time()


def authorize_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": _env("OFFICEHOURS_MS_CLIENT_ID"),
            "response_type": "code",
            "redirect_uri": redirect_uri(),
            "response_mode": "query",
            "scope": "openid profile email",
            "state": state,
        }
    )
    return f"{_authority()}/oauth2/v2.0/authorize?{query}"


def exchange_code(code: str) -> dict:
    """Trade the authorization code for tokens at Microsoft's token endpoint."""
    response = httpx.post(
        f"{_authority()}/oauth2/v2.0/token",
        data={
            "client_id": _env("OFFICEHOURS_MS_CLIENT_ID"),
            "client_secret": _env("OFFICEHOURS_MS_CLIENT_SECRET"),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri(),
            "scope": "openid profile email",
        },
        timeout=15.0,
    )
    response.raise_for_status()
    return response.json()


def claims_from_id_token(id_token: str, *, key: Any = None) -> dict:
    """Verify the id_token (RS256 JWKS) and check audience, issuer, tenant, exp."""
    if key is None:
        jwks = jwt.PyJWKClient(_jwks_url(), cache_jwk_set=True)
        key = jwks.get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=_env("OFFICEHOURS_MS_CLIENT_ID"),
        issuer=_issuer(),
        options={"require": ["exp", "iat", "iss", "aud"]},
    )
    if claims.get("tid") != _env("OFFICEHOURS_MS_TENANT_ID"):
        raise ValueError("id_token tenant mismatch.")
    return claims


def identity_from_claims(claims: dict) -> tuple[str, str]:
    """Return (email, display_name); raises ValueError outside the allowed domain."""
    email = (claims.get("email") or claims.get("preferred_username") or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Microsoft account has no usable email.")
    if email.split("@", 1)[1] != allowed_domain():
        raise ValueError(f"Only {allowed_domain()} accounts can sign in.")
    display_name = (claims.get("name") or email.split("@", 1)[0].replace(".", " ").title()).strip()
    return email, display_name
