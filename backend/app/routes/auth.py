"""Auth and course membership APIs for the unified multi-role product."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
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
    return {"demo": demo_mode(), "canvas_mode": canvas_mode()}


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
