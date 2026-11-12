"""In-process request throttle for hot student/TA paths.

Disabled when ``OFFICEHOURS_RATE_LIMIT=false`` (pytest default) so the suite
does not trip itself. Campus host should leave it on.

Multi-worker note: buckets are per-process. For multiple uvicorn workers, put
rate limiting at the reverse proxy (nginx/Cloudflare) or run a single worker.
``OFFICEHOURS_TRUST_PROXY=true`` only when a trusted proxy strips client-supplied
``X-Forwarded-For``.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.services.client_ip import client_ip
from app.services.security_log import audit

# path prefix → (max requests, window seconds)
DEFAULT_LIMITS = {
    "/auth/login": (20, 60),
    "/requests/": (30, 60),
    "/agent/ask": (40, 60),
    "/revision/plan": (10, 60),
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

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def _prune(self, bucket: deque[float], *, now: float, window_s: int) -> None:
        cutoff = now - window_s
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

    def check(self, key: str, limit: int, window_s: int) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            self._prune(bucket, now=now, window_s=window_s)
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests — wait a moment and try again.",
                )
            bucket.append(now)

    def blocking(self, checks: list[tuple[str, str, int, int]]) -> str | None:
        """Name of the first full window. Does not record a hit."""
        now = time.monotonic()
        with self._lock:
            for name, key, limit, window_s in checks:
                bucket = self._hits[key]
                self._prune(bucket, now=now, window_s=window_s)
                if limit <= 0 or len(bucket) >= limit:
                    return name
            return None

    def allow_all(self, checks: list[tuple[str, str, int, int]]) -> str | None:
        """Record every hit, or record none.

        ``checks`` items are ``(name, key, limit, window_seconds)``. The
        return value is the name of the first full window. The study-agent
        policy uses this so one request cannot take a per-user slot and then
        fail a later cap.
        """
        now = time.monotonic()
        with self._lock:
            live: list[deque[float]] = []
            for name, key, limit, window_s in checks:
                bucket = self._hits[key]
                self._prune(bucket, now=now, window_s=window_s)
                if limit <= 0 or len(bucket) >= limit:
                    return name
                live.append(bucket)
            for bucket in live:
                bucket.append(now)
            return None


limiter = RateLimiter()


def client_key(request: Request) -> str:
    return client_ip(request)


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
            if prefix == "/revision/plan" and request.method != "POST":
                return
            if prefix == "/auth/login" and request.method != "POST":
                return
            try:
                limiter.check(f"{prefix}:{client_key(request)}", limit, window_s)
            except HTTPException:
                audit(
                    "rate_limit.exceeded",
                    level="warning",
                    path=path,
                    client=client_key(request),
                )
                raise
            return
