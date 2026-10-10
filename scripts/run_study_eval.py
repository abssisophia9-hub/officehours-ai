#!/usr/bin/env python3
"""Run the retrieval-only baseline in four filter modes, twice.

Once with MiniLM and once with the lexical backend. The production answer
cutoff stays 0.42. The threshold sweep only re-reads recorded scores.

Writes docs/eval_results/baseline_retrieval_only_<timestamp>.json and prints
the same summary.
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

_DB_DIR = tempfile.mkdtemp(prefix="study-eval-")
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_DIR}/study_eval.db"

from fastapi.testclient import TestClient  # noqa: E402

from app.database.session import SessionLocal  # noqa: E402
from app.eval.study_harness import (  # noqa: E402
    ANSWER_THRESHOLD,
    assert_flags_not_on_ask_route,
    corpus_files,
    evaluate,
    format_baseline,
    format_summary,
    ingest_corpus,
    load_questions,
)
from app.main import app  # noqa: E402

QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = BACKEND / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = BACKEND / "demo_data"
RESULTS = REPO / "docs" / "eval_results"
BACKENDS = ("sentence-transformers", "lexical")


def main() -> int:
    assert_flags_not_on_ask_route()
    if ANSWER_THRESHOLD != 0.42:
        raise RuntimeError(f"Production cutoff moved to {ANSWER_THRESHOLD}")
    questions = load_questions(QUESTIONS)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = corpus_files(manifest)
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

    reports = {}
    for backend in BACKENDS:
        os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = backend
        print(f"Evaluating {backend}")
        db = SessionLocal()
        try:
            report = evaluate(db, ingested["course_a_id"], questions, files)
        finally:
            db.close()
        report["embedding_backend"] = backend
        reports[backend] = report
        print(format_summary(report))

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    baseline = {
        "label": "baseline_retrieval_only",
        "answering": "retrieval_only",
        "created_at": stamp,
        "production_answer_cutoff": ANSWER_THRESHOLD,
        "cutoff_changed": False,
        "course_a": manifest["course_a"],
        "course_b": manifest["course_b"],
        "uploads": ingested["uploads"],
        "backends": reports,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"baseline_retrieval_only_{stamp}.json"
    out.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(format_baseline(baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
