"""Public URL prefix for reverse-proxy sub-path deploys (AUI CDN).

``OFFICEHOURS_ROOT_PATH`` defaults to empty so local Windows scripts and
ports 5180/8000 keep working at the site root. Campus example:

    OFFICEHOURS_ROOT_PATH=/officehours-ai

Normalized form always starts with ``/`` and has no trailing slash
(except the empty default).
"""

from __future__ import annotations

import os


def normalize_root_path(raw: str | None = None) -> str:
    value = (raw if raw is not None else os.getenv("OFFICEHOURS_ROOT_PATH", "")).strip()
    if not value or value == "/":
        return ""
    if not value.startswith("/"):
        value = f"/{value}"
    return value.rstrip("/")


def root_path() -> str:
    return normalize_root_path()
