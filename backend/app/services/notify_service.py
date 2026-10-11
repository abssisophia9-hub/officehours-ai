"""Claim / reply notifications: inbox + optional SMTP. WS is the campus push."""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from typing import Any

from sqlalchemy.orm import Session

from app.models.auth import User
from app.models.notification import Notification, NotificationOut
from app.models.request import Request
from app.realtime.hub import hub


def smtp_configured() -> bool:
    return bool((os.getenv("OFFICEHOURS_SMTP_HOST") or "").strip())


def _send_email(*, to_addr: str, subject: str, body: str) -> bool:
    host = (os.getenv("OFFICEHOURS_SMTP_HOST") or "").strip()
    if not host:
        return False
    port = int(os.getenv("OFFICEHOURS_SMTP_PORT") or "587")
    user = (os.getenv("OFFICEHOURS_SMTP_USER") or "").strip()
    password = os.getenv("OFFICEHOURS_SMTP_PASSWORD") or ""
    from_addr = (
        os.getenv("OFFICEHOURS_SMTP_FROM") or user or "officehours@aui.ma"
    ).strip()
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP(host, port, timeout=8) as smtp:
            smtp.ehlo()
            if os.getenv("OFFICEHOURS_SMTP_STARTTLS", "true").lower() in {
                "1",
                "true",
                "yes",
            }:
                smtp.starttls()
            if user:
                smtp.login(user, password)
            smtp.send_message(message)
        return True
    except Exception:
        return False


async def notify_user(
    db: Session,
    user: User,
    *,
    kind: str,
    title: str,
    body: str,
    request_id: int | None = None,
    course_id: int | None = None,
) -> Notification:
    row = Notification(
        user_id=user.id,
        kind=kind,
        title=title,
        body=body,
        request_id=request_id,
        course_id=course_id,
    )
    if user.email:
        row.email_sent = _send_email(to_addr=user.email, subject=title, body=body)
    db.add(row)
    db.commit()
    db.refresh(row)
    await hub.broadcast(
        "notification.created",
        {
            "id": row.id,
            "user_id": user.id,
            "kind": kind,
            "request_id": request_id,
            "course_id": course_id,
            "title": title,
        },
    )
    return row


async def notify_request_owner(
    db: Session,
    request: Request,
    *,
    kind: str,
    title: str,
    body: str,
) -> Notification | None:
    owner_id = getattr(request, "created_by_user_id", None)
    if not owner_id:
        return None
    owner = db.get(User, owner_id)
    if owner is None:
        return None
    return await notify_user(
        db,
        owner,
        kind=kind,
        title=title,
        body=body,
        request_id=request.id,
        course_id=request.course_id,
    )


def list_for_user(
    db: Session, user: User, *, limit: int = 30, unread_only: bool = False
) -> list[NotificationOut]:
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    rows = query.order_by(Notification.id.desc()).limit(limit).all()
    return [NotificationOut.model_validate(row) for row in rows]


def mark_read(db: Session, user: User, notification_id: int) -> NotificationOut | None:
    from datetime import datetime, timezone

    row = db.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        return None
    row.read_at = datetime.now(timezone.utc)
    db.add(row)
    db.commit()
    db.refresh(row)
    return NotificationOut.model_validate(row)


def unread_count(db: Session, user: User) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read_at.is_(None))
        .count()
    )


def inbox_payload(db: Session, user: User) -> dict[str, Any]:
    return {
        "unread": unread_count(db, user),
        "smtp_configured": smtp_configured(),
        "items": list_for_user(db, user),
    }
