"""
Course-scoped WebSocket.

Auth: ``Authorization: Bearer <token>`` preferred; ``?token=`` accepted for
legacy dashboard clients. ``course_id`` is required. Membership is checked
before the socket is accepted whenever the ASGI server allows rejecting the
handshake; otherwise we close immediately with 4401/4403.
"""

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database.session import SessionLocal
from app.realtime.hub import hub, set_main_loop
from app.services.access_control import get_membership
from app.services.security_log import audit
from app.services.session_tokens import user_from_token

router = APIRouter(tags=["realtime"])


def _extract_token(websocket: WebSocket, query_token: str | None) -> str | None:
    auth = websocket.headers.get("authorization") or websocket.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return (query_token or "").strip() or None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
):
    set_main_loop(asyncio.get_running_loop())
    bearer = _extract_token(websocket, token)
    db = SessionLocal()
    try:
        if not bearer or course_id is None:
            await websocket.accept()
            await websocket.send_json(
                {"type": "error", "payload": {"detail": "token and course_id required"}}
            )
            await websocket.close(code=4401)
            audit("ws.rejected", level="warning", reason="missing_credentials")
            return
        try:
            user = user_from_token(db, bearer)
            get_membership(db, user, course_id)
        except Exception:
            await websocket.accept()
            await websocket.send_json(
                {"type": "error", "payload": {"detail": "Not a member of this course."}}
            )
            await websocket.close(code=4403)
            audit(
                "ws.rejected",
                level="warning",
                reason="forbidden",
                course_id=course_id,
            )
            return
        user_id = user.id
    finally:
        db.close()

    await websocket.accept()
    await hub.connect(websocket, course_id=course_id)
    audit("ws.connected", course_id=course_id, user_id=user_id)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "payload": {
                    "message": "OfficeHours AI live channel ready",
                    "course_id": course_id,
                },
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception:
        await hub.disconnect(websocket)
