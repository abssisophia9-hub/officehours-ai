"""Optional SPA hosting from the Vite build (``frontend/officehours-app/dist``).

Controlled by ``OFFICEHOURS_SERVE_FRONTEND``:

- ``true`` / ``1`` / ``on`` — serve dist when the directory exists
- ``false`` / ``0`` / ``off`` — never serve (local API-only / pytest)
- unset — auto-serve when dist exists and pytest is not loaded

Local Windows FYP keeps the Vite dev server on :5180; leave this off
(or unset with no dist) so ``GET /`` stays the JSON smoke response.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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


def mount_frontend(app: FastAPI) -> bool:
    """Mount asset files + SPA fallback. Returns True when mounted."""
    if not should_serve_frontend():
        return False

    dist = frontend_dist_dir()
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="spa-assets")

    index = dist / "index.html"

    @app.get("/{spa_path:path}", include_in_schema=False)
    async def spa_fallback(spa_path: str):
        # Prefer real files under dist (favicon, robots, …) before SPA shell.
        candidate = dist / spa_path
        if spa_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    return True
