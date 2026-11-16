"""Canvas LTI 1.3 (OIDC) resource-link launches.

Canvas POSTs to ``/lti/login``, we redirect to Canvas's authorize endpoint,
Canvas POSTs an ``id_token`` to ``/lti/launch``. We verify the JWT against
Canvas JWKS, map the person + course + role, then reuse ``launch_from_canvas``.

Enabled when these are set:

    OFFICEHOURS_LTI_ISSUER        Canvas issuer, e.g. https://canvas.aui.ma
    OFFICEHOURS_LTI_CLIENT_ID     Developer key client_id
    OFFICEHOURS_LTI_AUTH_LOGIN_URL
                                  Canvas OIDC authorize URL
                                  (default {issuer}/api/lti/authorize_redirect)
    OFFICEHOURS_LTI_JWKS_URL      Canvas JWKS (default {issuer}/api/lti/security/jwks)
    OFFICEHOURS_LTI_LAUNCH_URL    This API's launch URL
                                  (default http://127.0.0.1:8000/lti/launch)
    OFFICEHOURS_LTI_DEPLOYMENT_ID Optional; reject other deployments if set
    OFFICEHOURS_FRONTEND_URL      Where the browser lands after launch
"""

from __future__ import annotations

import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import jwt

from app.services.microsoft_sso import frontend_url

_STATE_TTL_SECONDS = 600
_pending: dict[str, dict[str, Any]] = {}

ROLES_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/roles"
CONTEXT_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/context"
DEPLOYMENT_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/deployment_id"
CUSTOM_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/custom"
MESSAGE_TYPE_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/message_type"
LIS_CLAIM = "https://purl.imsglobal.org/spec/lti/claim/lis"


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def lti_enabled() -> bool:
    return bool(_env("OFFICEHOURS_LTI_ISSUER") and _env("OFFICEHOURS_LTI_CLIENT_ID"))


def issuer() -> str:
    return _env("OFFICEHOURS_LTI_ISSUER").rstrip("/")


def client_id() -> str:
    return _env("OFFICEHOURS_LTI_CLIENT_ID")


def auth_login_url() -> str:
    return _env("OFFICEHOURS_LTI_AUTH_LOGIN_URL") or f"{issuer()}/api/lti/authorize_redirect"


def jwks_url() -> str:
    return _env("OFFICEHOURS_LTI_JWKS_URL") or f"{issuer()}/api/lti/security/jwks"


def launch_url() -> str:
    configured = _env("OFFICEHOURS_LTI_LAUNCH_URL")
    if configured:
        return configured
    from app.root_path import root_path

    return f"http://127.0.0.1:8000{root_path()}/lti/launch"


def expected_deployment() -> str:
    return _env("OFFICEHOURS_LTI_DEPLOYMENT_ID")


def new_login_state(nonce: str | None = None) -> str:
    now = time.time()
    for key, row in list(_pending.items()):
        if row["expires"] < now:
            _pending.pop(key, None)
    state = secrets.token_urlsafe(24)
    _pending[state] = {
        "nonce": nonce or secrets.token_urlsafe(24),
        "expires": now + _STATE_TTL_SECONDS,
    }
    return state


def peek_nonce(state: str) -> str | None:
    row = _pending.get(state)
    if row is None or row["expires"] < time.time():
        return None
    return row["nonce"]


def consume_state(state: str) -> str | None:
    row = _pending.pop(state, None)
    if row is None or row["expires"] < time.time():
        return None
    return row["nonce"]


def authorize_redirect_url(*, login_hint: str, lti_message_hint: str, state: str, nonce: str) -> str:
    query = urlencode(
        {
            "scope": "openid",
            "response_type": "id_token",
            "response_mode": "form_post",
            "prompt": "none",
            "client_id": client_id(),
            "redirect_uri": launch_url(),
            "login_hint": login_hint,
            "lti_message_hint": lti_message_hint,
            "state": state,
            "nonce": nonce,
        }
    )
    return f"{auth_login_url()}?{query}"


def decode_id_token(id_token: str, *, nonce: str, key: Any = None) -> dict[str, Any]:
    """Verify Canvas's LTI id_token (RS256, audience, issuer, nonce)."""
    if key is None:
        jwks = jwt.PyJWKClient(jwks_url(), cache_jwk_set=True)
        key = jwks.get_signing_key_from_jwt(id_token).key
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=client_id(),
        issuer=issuer(),
        options={"require": ["exp", "iat", "nonce", "iss", "aud"]},
    )
    if claims.get("nonce") != nonce:
        raise ValueError("LTI nonce mismatch.")
    deployment = expected_deployment()
    if deployment and claims.get(DEPLOYMENT_CLAIM) != deployment:
        raise ValueError("LTI deployment id mismatch.")
    message_type = claims.get(MESSAGE_TYPE_CLAIM) or ""
    if message_type and message_type != "LtiResourceLinkRequest":
        raise ValueError(f"Unsupported LTI message type: {message_type}")
    return claims


def identity_from_claims(claims: dict[str, Any]) -> dict[str, str]:
    """Map LTI claims onto launch_from_canvas arguments."""
    email = (
        str(claims.get("email") or "").strip()
        or str((claims.get(LIS_CLAIM) or {}).get("person_contact_email_primary") or "").strip()
    ).lower()
    if not email or "@" not in email:
        raise ValueError("Canvas did not send an email. Set the developer key privacy to Public.")
    name = (
        str(claims.get("name") or "").strip()
        or f"{claims.get('given_name') or ''} {claims.get('family_name') or ''}".strip()
        or email.split("@", 1)[0]
    )
    context = claims.get(CONTEXT_CLAIM) or {}
    custom = claims.get(CUSTOM_CLAIM) or {}
    canvas_course_id = str(
        custom.get("canvas_course_id")
        or context.get("id")
        or ""
    ).strip()
    if not canvas_course_id:
        raise ValueError("Canvas launch is missing a course id.")
    return {
        "email": email,
        "display_name": name,
        "canvas_role": role_from_lti(claims.get(ROLES_CLAIM) or []),
        "canvas_course_id": canvas_course_id,
        "course_code": str(context.get("label") or "").strip() or None,
        "course_title": str(context.get("title") or "").strip() or None,
        "student_id": str(custom.get("canvas_user_sis_id") or "").strip() or None,
    }


def role_from_lti(roles: list[Any]) -> str:
    blob = " ".join(str(role).lower() for role in roles)
    if "teachingassistant" in blob or "/ta" in blob or "#ta" in blob:
        return "TaEnrollment"
    if "instructor" in blob or "teacher" in blob or "faculty" in blob:
        return "TeacherEnrollment"
    return "StudentEnrollment"


def frontend_handoff(token: str, course_id: int) -> str:
    from urllib.parse import quote

    return f"{frontend_url().rstrip('/')}/sso#token={quote(token)}&course={course_id}"
