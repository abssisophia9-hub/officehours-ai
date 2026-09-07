"""Resolve a bearer / query session token to a live user."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.auth import AuthSession, User
from app.services.demo_accounts import ensure_demo_accounts


def user_from_token(db: Session, token: str | None) -> User:
    ensure_demo_accounts(db)
    value = (token or "").strip()
    if not value:
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    if value.lower().startswith("bearer "):
        value = value.split(" ", 1)[1].strip()
    session = db.query(AuthSession).filter(AuthSession.token == value).one_or_none()
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid session.")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired.")
    user = (
        db.query(User)
        .filter(User.id == session.user_id, User.is_active.is_(True))
        .one_or_none()
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")
    return user
