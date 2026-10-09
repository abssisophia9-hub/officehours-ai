"""Structured security and operations logging.

Never log passwords, session tokens, Microsoft/LTI secrets, or raw id_tokens.
Emit JSON lines to stderr so campus hosts can ship them to a log collector.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_LOGGER = logging.getLogger("officehours.security")
if not _LOGGER.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False

# Keys that must never appear in audit payloads.
_REDACT = {
    "password",
    "password_hash",
    "token",
    "authorization",
    "client_secret",
    "id_token",
    "access_token",
    "refresh_token",
    "demo_secret",
    "cookie",
}


def _scrub(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _REDACT:
                out[key] = "[redacted]"
            else:
                out[key] = _scrub(item)
        return out
    if isinstance(value, list):
        return [_scrub(item) for item in value]
    if isinstance(value, str) and len(value) > 500:
        return value[:500] + "…"
    return value


def audit(event: str, *, level: str = "info", **fields: Any) -> None:
    """Write one structured audit event."""
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **_scrub(fields),
    }
    line = json.dumps(payload, default=str, separators=(",", ":"))
    if level == "warning":
        _LOGGER.warning(line)
    elif level == "error":
        _LOGGER.error(line)
    else:
        _LOGGER.info(line)
