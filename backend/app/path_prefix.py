"""ASGI wrapper that accepts requests under ``OFFICEHOURS_ROOT_PATH``.

Strips the configured prefix from HTTP and WebSocket paths so existing
routes (``/health``, ``/ws``, …) keep their absolute paths in code.
When the prefix is empty, this is a no-op passthrough.
"""

from __future__ import annotations

from typing import Any, Callable, Awaitable


Send = Callable[[dict[str, Any]], Awaitable[None]]
Receive = Callable[[], Awaitable[dict[str, Any]]]


class PathPrefixASGI:
    """Serve the inner app under an optional URL prefix."""

    def __init__(self, app: Any, root_path: str):
        self.app = app
        self.root_path = (root_path or "").rstrip("/")

    def __getattr__(self, name: str) -> Any:
        # Expose FastAPI/Starlette attributes (router, state, …) for TestClient.
        return getattr(self.app, name)

    async def __call__(self, scope: dict[str, Any], receive: Receive, send: Send) -> None:
        if not self.root_path or scope.get("type") not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        root = self.root_path
        if path == root or path.startswith(root + "/"):
            new_scope = dict(scope)
            stripped = path[len(root) :] or "/"
            if not stripped.startswith("/"):
                stripped = "/" + stripped
            new_scope["path"] = stripped
            raw = new_scope.get("raw_path")
            if isinstance(raw, (bytes, bytearray)):
                prefix = root.encode("utf-8")
                if raw.startswith(prefix):
                    new_raw = raw[len(prefix) :] or b"/"
                    new_scope["raw_path"] = new_raw
            new_scope["root_path"] = (scope.get("root_path") or "") + root
            await self.app(new_scope, receive, send)
            return

        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 4404})
            return

        body = b'{"detail":"Not found. Check OFFICEHOURS_ROOT_PATH."}'
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
