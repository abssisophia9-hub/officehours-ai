"""Canvas LTI 1.3 OIDC login + resource-link launch."""

from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.services import lti13
from app.services.canvas_launch_service import launch_from_canvas
from app.services.microsoft_sso import frontend_url

router = APIRouter(prefix="/lti", tags=["lti"])


def _fail(reason: str) -> RedirectResponse:
    return RedirectResponse(
        f"{frontend_url().rstrip('/')}/login?{urlencode({'sso_error': reason})}",
        status_code=302,
    )


@router.get("/config")
def lti_public_config():
    """URLs a Canvas admin pastes into an LTI 1.3 developer key."""
    if not lti13.lti_enabled():
        raise HTTPException(status_code=404, detail="LTI 1.3 is not configured.")
    return {
        "title": "OfficeHours",
        "description": "AUI campus office hours - Rooms, Quiet ask, course agent.",
        "target_link_uri": lti13.launch_url(),
        "oidc_initiation_url": lti13.launch_url().rsplit("/launch", 1)[0] + "/login",
        "redirect_uris": [lti13.launch_url()],
        "issuer": lti13.issuer(),
        "client_id": lti13.client_id(),
        "public_jwk_url": lti13.launch_url().rsplit("/launch", 1)[0] + "/jwks",
    }


@router.get("/jwks")
def lti_jwks():
    """Placeholder JWKS. We verify Canvas's tokens; we do not sign launches."""
    return JSONResponse({"keys": []})


@router.api_route("/login", methods=["GET", "POST"])
async def lti_login(request: Request):
    """OIDC login initiation - Canvas hits this when a student clicks the tool."""
    if not lti13.lti_enabled():
        raise HTTPException(status_code=404, detail="LTI 1.3 is not configured.")
    data = request.query_params
    if request.method == "POST":
        form = await request.form()
        data = form
    iss = str(data.get("iss") or "").rstrip("/")
    client = str(data.get("client_id") or "")
    if iss != lti13.issuer():
        return _fail("This launch is not from the configured Canvas issuer.")
    if client and client != lti13.client_id():
        return _fail("This launch is not from the configured Canvas developer key.")
    login_hint = str(data.get("login_hint") or "")
    message_hint = str(data.get("lti_message_hint") or "")
    if not login_hint:
        return _fail("Canvas did not send a login_hint.")
    state = lti13.new_login_state()
    nonce = lti13.peek_nonce(state)
    return RedirectResponse(
        lti13.authorize_redirect_url(
            login_hint=login_hint,
            lti_message_hint=message_hint,
            state=state,
            nonce=nonce or "",
        ),
        status_code=302,
    )


@router.post("/launch")
def lti_launch(
    db: Session = Depends(get_db),
    id_token: str | None = Form(default=None),
    state: str | None = Form(default=None),
    error: str | None = Form(default=None),
    error_description: str | None = Form(default=None),
):
    """Canvas form-posts the LTI id_token here after the student clicks the tool."""
    if not lti13.lti_enabled():
        raise HTTPException(status_code=404, detail="LTI 1.3 is not configured.")
    if error:
        return _fail(error_description or error)
    if not id_token or not state:
        return _fail("Canvas did not return an LTI id_token.")
    nonce = lti13.consume_state(state)
    if not nonce:
        return _fail("This Canvas launch expired. Open OfficeHours from the course again.")
    try:
        claims = lti13.decode_id_token(id_token, nonce=nonce)
        identity = lti13.identity_from_claims(claims)
        result = launch_from_canvas(db, **identity)
    except ValueError as exc:
        return _fail(str(exc))
    except Exception:
        return _fail("Could not finish the Canvas launch. Please try again.")
    return RedirectResponse(
        lti13.frontend_handoff(result["token"], result["course_id"]),
        status_code=302,
    )
