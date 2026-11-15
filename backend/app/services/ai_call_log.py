"""Structured AI / quota call logs — no student content, names, or IDs.

Emits one JSON line per external AI or quota-bearing call for ops summaries.
Never include question text, answers, names, emails, course titles as free text,
or API key values.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

_LOGGER = logging.getLogger("officehours.ai_call")
if not _LOGGER.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _LOGGER.addHandler(handler)
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False

# Forbidden field names — belt and suspenders if a caller slips.
_FORBIDDEN = {
    "question",
    "answer",
    "text",
    "body",
    "prompt",
    "user",
    "system",
    "name",
    "email",
    "student",
    "student_id",
    "user_id",
    "api_key",
    "authorization",
    "token",
}


def log_ai_call(
    *,
    agent: str,
    tool: str,
    status: str,
    latency_ms: float = 0.0,
    input_tokens: int = 0,
    output_tokens: int = 0,
    quota_units: int = 0,
    provider: str | None = None,
    model: str | None = None,
    error_type: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Write one structured ai_call event (JSON line to stderr)."""
    payload: dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": "ai_call",
        "agent": str(agent or "unknown")[:64],
        "tool": str(tool or "unknown")[:64],
        "status": str(status or "unknown")[:64],
        "latency_ms": round(float(latency_ms or 0.0), 3),
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "quota_units": int(quota_units or 0),
    }
    if provider:
        payload["provider"] = str(provider)[:64]
    if model:
        payload["model"] = str(model)[:96]
    if error_type:
        payload["error_type"] = str(error_type)[:96]
    if extra:
        for key, value in extra.items():
            if str(key).lower() in _FORBIDDEN:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                payload[str(key)[:64]] = value if not isinstance(value, str) else value[:120]
    _LOGGER.info(json.dumps(payload, default=str, separators=(",", ":")))
