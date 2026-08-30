"""
Course-scoped WebSocket. Query: token + course_id. Members of that course only.
"""

import asyncio

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.database.session import SessionLocal
from app.realtime.hub import hub, set_main_loop
from app.services.access_control import get_membership
from app.services.session_tokens import user_from_token

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    course_id: int | None = Query(default=None),
):
    set_main_loop(asyncio.get_running_loop())
    await websocket.accept()
    db = SessionLocal()
    try:
        if not token or course_id is None:
            await websocket.send_json(
                {"type": "error", "payload": {"detail": "token and course_id required"}}
            )
            await websocket.close(code=4401)
            return
        try:
            user = user_from_token(db, token)
            get_membership(db, user, course_id)
        except Exception:
            await websocket.send_json(
                {"type": "error", "payload": {"detail": "Not a member of this course."}}
            )
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    await hub.connect(websocket, course_id=course_id)
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
