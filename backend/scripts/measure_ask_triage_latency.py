#!/usr/bin/env python3
"""Measure Ask Triage end-to-end latency for FYP evidence tables.

Writes ``reports/final_report/ask_triage_latency.json`` with p50/p95 over a
small synthetic ask set. Uses the FastAPI TestClient (no live server required).

Example::

    cd backend
    OFFICEHOURS_CLUSTERING_BACKEND=lexical \\
      venv/bin/python scripts/measure_ask_triage_latency.py
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

SAMPLES = [
    "I still don't understand red-black tree deletion rotations.",
    "When is the CSC 2302 final and what chapters are covered?",
    "Can I get an extension on the hashing project?",
    "I'm stressed about the algorithms midterm and don't know where to start.",
    "How do I prove induction for the recurrence we did in class?",
]


def percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def main() -> None:
    client = TestClient(app)
    timings_ms: list[float] = []
    rows: list[dict] = []

    for text in SAMPLES:
        started = time.perf_counter()
        response = client.post(
            "/requests/",
            json={
                "text": text,
                "anonymous": True,
                "help_mode": "message",
            },
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        timings_ms.append(elapsed_ms)
        body = response.json() if response.status_code < 500 else {}
        rows.append(
            {
                "status_code": response.status_code,
                "elapsed_ms": round(elapsed_ms, 2),
                "category": body.get("triage_category") or body.get("category"),
                "assigned_ta": (body.get("triage") or {}).get("matcher", {}).get(
                    "assigned_ta"
                )
                if isinstance(body.get("triage"), dict)
                else body.get("assigned_ta"),
            }
        )

    ordered = sorted(timings_ms)
    summary = {
        "n": len(timings_ms),
        "clustering_backend": os.environ.get(
            "OFFICEHOURS_CLUSTERING_BACKEND", "default"
        ),
        "mean_ms": round(statistics.mean(timings_ms), 2),
        "p50_ms": round(percentile(ordered, 50), 2),
        "p95_ms": round(percentile(ordered, 95), 2),
        "max_ms": round(max(timings_ms), 2),
        "samples": rows,
        "note": (
            "In-process TestClient latency with lexical clustering by default. "
            "Not a production load test; use for FYP evidence tables."
        ),
    }

    out = REPO / "reports" / "final_report" / "ask_triage_latency.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
