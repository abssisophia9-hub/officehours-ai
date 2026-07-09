"""
WebSocket endpoint for live professor/TA dashboard updates.
"""

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.realtime.hub import hub, set_main_loop

router = APIRouter(tags=["realtime"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Ensure sync route handlers can schedule broadcasts onto this loop.
    set_main_loop(asyncio.get_running_loop())
    await hub.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "connected",
                "payload": {"message": "OfficeHours AI live channel ready"},
            }
        )
        while True:
            # Keep the socket alive; clients may send pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception:
        await hub.disconnect(websocket)
