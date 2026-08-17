"""Explicit demo switch for seeded AUI accounts and sample catalogs.

Production deploy: leave ``OFFICEHOURS_DEMO`` unset/false, set live Canvas
credentials, and let LTI/Canvas provision users and modules.

Local FYP demos: ``OFFICEHOURS_DEMO=true`` (``./scripts/run_product.sh``).
"""

from __future__ import annotations

import os


def demo_mode() -> bool:
    return os.getenv("OFFICEHOURS_DEMO", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
