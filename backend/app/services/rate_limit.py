"""In-process request throttle for hot student/TA paths.

Disabled when ``OFFICEHOURS_RATE_LIMIT=false`` (pytest default) so the suite
does not trip itself. Campus host should leave it on.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

# path prefix → (max requests, window seconds)
DEFAULT_LIMITS = {
    "/auth/login": (20, 60),
    "/requests/": (30, 60),
    "/agent/ask": (40, 60),
}


def rate_limit_enabled() -> bool:
    return os.getenv("OFFICEHOURS_RATE_LIMIT", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_s: int) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_s
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests — wait a moment and try again.",
                )
            bucket.append(now)


limiter = RateLimiter()


def client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(request: Request) -> None:
    if not rate_limit_enabled():
        return
    path = request.url.path
    for prefix, (limit, window_s) in DEFAULT_LIMITS.items():
        if path == prefix or path.startswith(prefix.rstrip("/") + "/"):
            if prefix == "/requests/" and request.method != "POST":
                return
            if prefix == "/agent/ask" and request.method != "POST":
                return
            if prefix == "/auth/login" and request.method != "POST":
                return
            limiter.check(f"{prefix}:{client_key(request)}", limit, window_s)
            return
