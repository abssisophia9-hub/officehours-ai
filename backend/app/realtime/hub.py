"""
In-process WebSocket hub. Connections subscribe to one course; events
without a course_id are dropped (no campus-wide fan-out).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket

_main_loop: asyncio.AbstractEventLoop | None = None


def set_main_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


class ConnectionHub:
    def __init__(self) -> None:
        self._course_ids: dict[WebSocket, int] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, *, course_id: int) -> None:
        async with self._lock:
            self._course_ids[websocket] = course_id

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._course_ids.pop(websocket, None)

    async def broadcast(self, event_type: str, payload: dict[str, Any]) -> None:
        course_id = payload.get("course_id")
        if course_id is None:
            return
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            return

        message = json.dumps({"type": event_type, "payload": payload})
        async with self._lock:
            targets = [
                socket
                for socket, subscribed in self._course_ids.items()
                if subscribed == course_id
            ]

        stale: list[WebSocket] = []
        for connection in targets:
            try:
                await connection.send_text(message)
            except Exception:
                stale.append(connection)

        if stale:
            async with self._lock:
                for connection in stale:
                    self._course_ids.pop(connection, None)

    @property
    def connection_count(self) -> int:
        return len(self._course_ids)


hub = ConnectionHub()


def broadcast_event(event_type: str, payload: dict[str, Any]) -> None:
    """
    Schedule a broadcast from sync or async route handlers.

    Sync FastAPI routes run in a threadpool, so we fall back to the loop
    captured at app startup via ``set_main_loop``.
    """
    coroutine = hub.broadcast(event_type, payload)

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        loop.create_task(coroutine)
        return

    if _main_loop is not None and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(coroutine, _main_loop)
        return

    coroutine.close()
