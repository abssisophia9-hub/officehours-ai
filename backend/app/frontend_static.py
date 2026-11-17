"""Optional SPA hosting from the Vite build (``frontend/officehours-app/dist``).

Controlled by ``OFFICEHOURS_SERVE_FRONTEND``:

- ``true`` / ``1`` / ``on`` — serve dist when the directory exists
- ``false`` / ``0`` / ``off`` — never serve (local API-only / pytest)
- unset — auto-serve when dist exists and pytest is not loaded

Local Windows FYP keeps the Vite dev server on :5180; leave this off
(or unset with no dist) so ``GET /`` stays the JSON smoke response.

Serving uses a single catch-all route (no ``StaticFiles`` mount) so assets
work under ``OFFICEHOURS_ROOT_PATH`` and path traversal cannot escape ``dist``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import unquote

from fastapi import FastAPI
from fastapi.responses import FileResponse


def frontend_dist_dir() -> Path:
    override = (os.getenv("OFFICEHOURS_FRONTEND_DIST") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    # backend/app/frontend_static.py → repo root / frontend/officehours-app/dist
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "frontend" / "officehours-app" / "dist"


def should_serve_frontend() -> bool:
    flag = (os.getenv("OFFICEHOURS_SERVE_FRONTEND") or "").strip().lower()
    dist = frontend_dist_dir()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return dist.is_dir() and (dist / "index.html").is_file()
    if "pytest" in sys.modules:
        return False
    return dist.is_dir() and (dist / "index.html").is_file()


def _safe_dist_file(dist: Path, spa_path: str) -> Path | None:
    """Return a real file under ``dist`` or None (SPA / missing / traversal)."""
    if not spa_path:
        return None
    # Decode %2e%2e etc. before joining; reject NUL.
    decoded = unquote(spa_path)
    if "\x00" in decoded:
        return None
    dist_root = dist.resolve()
    candidate = (dist_root / decoded).resolve()
    try:
        if not candidate.is_relative_to(dist_root):
            return None
    except (OSError, ValueError):
        return None
    if candidate.is_file():
        return candidate
    return None


def mount_frontend(app: FastAPI) -> bool:
    """Mount SPA catch-all (assets + index). Returns True when mounted."""
    if not should_serve_frontend():
        return False

    dist = frontend_dist_dir()
    index = dist / "index.html"

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str):
        # Prefer real files under dist (assets, favicon, …) before SPA shell.
        # Never serve paths that resolve outside dist (../ or %2e%2e).
        safe = _safe_dist_file(dist, spa_path)
        if safe is not None:
            return FileResponse(safe)
        return FileResponse(index)

    return True
