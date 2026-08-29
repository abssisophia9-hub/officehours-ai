"""Auth and course membership APIs for the unified multi-role product."""

from __future__ import annotations

from urllib.parse import quote, urlencode

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.auth import (
    AuthSession,
    Course,
    CourseMembership,
    CourseOut,
    LoginRequest,
    LoginResponse,
    User,
    UserOut,
)
from app.services.auth_service import (
    new_session_token,
    session_expiry,
    verify_password,
)
from app.services.demo_accounts import ensure_demo_accounts
from app.services.demo_mode import demo_mode
from app.services.canvas_service import canvas_mode
from app.services import lti13, microsoft_sso

router = APIRouter(prefix="/auth", tags=["auth"])
courses_router = APIRouter(prefix="/courses", tags=["courses"])


def _user_courses(db: Session, user_id: int) -> list[CourseOut]:
    rows = (
        db.query(CourseMembership, Course)
        .join(Course, Course.id == CourseMembership.course_id)
        .filter(CourseMembership.user_id == user_id, Course.is_active.is_(True))
        .order_by(Course.code.asc())
        .all()
    )
    return [
        CourseOut(
            id=course.id,
            code=course.code,
            title=course.title,
            term=course.term,
            role=membership.role,
            canvas_course_id=getattr(course, "canvas_course_id", None),
        )
        for membership, course in rows
    ]


def _serialize_user(db: Session, user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        student_id=user.student_id,
        courses=_user_courses(db, user.id),
    )


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    ensure_demo_accounts(db)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    session = db.query(AuthSession).filter(AuthSession.token == token).one_or_none()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid session.")
    from datetime import datetime, timezone

    if session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired.")
    user = db.query(User).filter(User.id == session.user_id, User.is_active.is_(True)).one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user


@router.get("/config")
def auth_config():
    """Public: whether this process is a demo seed or a community deploy."""
    return {
        "demo": demo_mode(),
        "canvas_mode": canvas_mode(),
        "microsoft": microsoft_sso.microsoft_enabled(),
        "lti": lti13.lti_enabled(),
    }


@router.get("/microsoft/login")
def microsoft_login():
    """Send the browser to Microsoft Entra ID (AUI tenant) to pick an account."""
    if not microsoft_sso.microsoft_enabled():
        raise HTTPException(status_code=404, detail="Microsoft sign-in is not configured.")
    return RedirectResponse(
        microsoft_sso.authorize_url(microsoft_sso.new_state()), status_code=302
    )


@router.get("/microsoft/callback")
def microsoft_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    db: Session = Depends(get_db),
):
    """Finish the Microsoft sign-in: mint an app session and hand it to the SPA."""
    front = microsoft_sso.frontend_url().rstrip("/")

    def fail(reason: str) -> RedirectResponse:
        return RedirectResponse(
            f"{front}/login?{urlencode({'sso_error': reason})}", status_code=302
        )

    if not microsoft_sso.microsoft_enabled():
        raise HTTPException(status_code=404, detail="Microsoft sign-in is not configured.")
    if error:
        return fail(error_description or error)
    if not code or not state:
        return fail("Microsoft did not return a sign-in code.")
    if not microsoft_sso.consume_state(state):
        return fail("Sign-in link expired. Please try again.")

    try:
        tokens = microsoft_sso.exchange_code(code)
        claims = microsoft_sso.claims_from_id_token(tokens["id_token"])
        email, display_name = microsoft_sso.identity_from_claims(claims)
    except ValueError as exc:
        return fail(str(exc))
    except Exception:
        return fail("Could not verify the Microsoft sign-in. Please try again.")

    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            # Not a usable password: SSO accounts can never log in with one.
            password_hash="microsoft_sso$-$-",
            display_name=display_name,
        )
        db.add(user)
        db.flush()
    elif not user.is_active:
        return fail("This account is disabled.")

    token = new_session_token()
    db.add(AuthSession(token=token, user_id=user.id, expires_at=session_expiry()))
    db.commit()
    return RedirectResponse(f"{front}/sso#token={quote(token)}", status_code=302)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ensure_demo_accounts(db)
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email, User.is_active.is_(True)).one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = new_session_token()
    db.add(
        AuthSession(
            token=token,
            user_id=user.id,
            expires_at=session_expiry(),
        )
    )
    db.commit()
    return LoginResponse(token=token, user=_serialize_user(db, user))


@router.post("/logout")
def logout(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        session = db.query(AuthSession).filter(AuthSession.token == token).one_or_none()
        if session is not None:
            db.delete(session)
            db.commit()
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize_user(db, user)


@courses_router.get("/mine", response_model=list[CourseOut])
def my_courses(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _user_courses(db, user.id)


@courses_router.get("/", response_model=list[CourseOut])
def list_courses_for_user(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _user_courses(db, user.id)
