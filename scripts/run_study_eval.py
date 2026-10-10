#!/usr/bin/env python3
"""Run the study-agent eval in filtered mode and plain RAG.

MiniLM (all-MiniLM-L6-v2) is the default. Set OFFICEHOURS_CLUSTERING_BACKEND
before launch to override (use lexical to match the test suite).

Writes a timestamped JSON file under docs/eval_results/ and prints the same
summary. Does not change retrieval.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BACKEND = REPO / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
os.environ.setdefault("OFFICEHOURS_RATE_LIMIT", "false")
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "sentence-transformers")

_DB_DIR = tempfile.mkdtemp(prefix="study-eval-")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_DIR}/study_eval.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.eval.study_harness import (  # noqa: E402
    assert_flags_not_on_ask_route,
    evaluate,
    format_summary,
    ingest_corpus,
    load_questions,
)
from app.main import app  # noqa: E402

QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = BACKEND / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = BACKEND / "demo_data"
RESULTS = REPO / "docs" / "eval_results"


def main() -> int:
    assert_flags_not_on_ask_route()
    questions = load_questions(QUESTIONS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    backend = os.environ["OFFICEHOURS_CLUSTERING_BACKEND"]
    print(f"Embedding backend: {backend}")
    print(f"Questions: {QUESTIONS}")
    print(f"Database: {os.environ['DATABASE_URL']}")

    with TestClient(app) as client:
        ingested = ingest_corpus(client, manifest, DEMO_ROOT)
    print(
        f"Ingested {len(ingested['uploads'])} files "
        f"into course {manifest['course_a']} ({ingested['course_a_id']}) "
        f"and {manifest['course_b']} ({ingested['course_b_id']})."
    )
    for upload in ingested["uploads"]:
        state = "approved" if upload["approved"] else "pending"
        print(f"  {upload['file']}: {upload['chunks']} chunks, {state}")

    db = SessionLocal()
    try:
        report = evaluate(db, ingested["course_a_id"], questions)
    finally:
        db.close()

    report["embedding_backend"] = backend
    report["course_a"] = manifest["course_a"]
    report["course_b"] = manifest["course_b"]
    report["uploads"] = ingested["uploads"]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"study_eval_{stamp}.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(format_summary(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
