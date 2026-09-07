"""Trusted-proxy aware client identity for rate limiting."""

from __future__ import annotations

import os

from fastapi import Request


def trust_proxy_headers() -> bool:
    """When true, use the first X-Forwarded-For hop (only behind a trusted reverse proxy)."""
    return os.getenv("OFFICEHOURS_TRUST_PROXY", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def client_ip(request: Request) -> str:
    if trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
