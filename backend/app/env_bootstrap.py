"""Load ``backend/.env`` into the process environment once at import time.

Most runtime flags (``OFFICEHOURS_*``, ``GEMINI_API_KEY``, …) are read via
``os.getenv``. Pydantic Settings alone only maps Canvas fields. Call
``load_dotenv`` with ``override=False`` so CDN / process-manager env always
wins over a local file.
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_ENV_PATH = _BACKEND_DIR / ".env"

# Idempotent; safe if the file is missing (local prod / CDN injects env).
load_dotenv(_ENV_PATH, override=False)
