#!/usr/bin/env python3
"""Run the retrieval-only baseline, or the answer-check comparison.

Default: four filter modes, MiniLM and lexical. The production answer cutoff
stays 0.42. Writes docs/eval_results/baseline_retrieval_only_<timestamp>.json.

Answer check (demo data only, your own key, MiniLM, both filters on).
From the repo root in Windows PowerShell:

    $env:OFFICEHOURS_DEMO = "true"
    $env:OFFICEHOURS_ALLOW_EXTERNAL_LLM = "true"
    $env:GEMINI_API_KEY = "<your key>"
    $env:GEMINI_MODEL = "gemini-3.8-flash"
    $env:OFFICEHOURS_CLUSTERING_BACKEND = "sentence-transformers"
    .\\backend\\venv\\Scripts\\python.exe scripts\\run_study_eval.py --with-check

The key is read from the environment and is not printed or written.
A real run writes the JSON results and a CSV of answered questions beside it.
``--fake-check`` uses an echo client, prints the harness, and does not write
a results file. Those numbers are not a live model result.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

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
    evaluate_with_check,
    format_baseline,
    format_summary,
    format_with_check,
    ingest_corpus,
    load_questions,
    load_retrieval_baseline,
    newest_baseline_file,
    write_answer_label_csv,
)
from app.main import app  # noqa: E402

QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = BACKEND / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = BACKEND / "demo_data"
RESULTS = REPO / "docs" / "eval_results"
BACKENDS = ("sentence-transformers", "lexical")


class _EchoClient:
    """Quotes the first chunk. For a dry run only; not a model result."""

    def complete(self, *, system: str, user: str):
        payload = json.loads(user)
        chunk = payload["chunks"][0]
        body = {
            "answerable": True,
            "supporting_chunk_id": chunk["chunk_id"],
            "answer": "From the supplied chunk.",
            "quote": chunk["text"],
        }
        return SimpleNamespace(
            text=json.dumps(body),
            model="fake-echo",
            input_tokens=1,
            output_tokens=1,
            latency_ms=0.0,
        )


def _prepare() -> tuple[dict, dict, dict]:
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
    return questions, manifest, {**ingested, "files": files}


def run_with_check(client) -> int:
    if client is None and not (
        os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
    ):
        print(
            "GEMINI_API_KEY is not set. Refusing to call the model. "
            "Set it in your shell and run again. The key is not printed or stored."
        )
        return 2
    if client is None:
        os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "sentence-transformers"
        print(f"Model: {os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}")
        print("API key is present. It is not printed or written.")
    else:
        os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
        print("Fake client. Counts are not a live model result. No results file is written.")
    questions, manifest, ingested = _prepare()
    db = SessionLocal()
    try:
        report = evaluate_with_check(
            db,
            ingested["course_a_id"],
            questions,
            ingested["files"],
            client=client,
            checker_label="fake" if client is not None else "gemini",
        )
    finally:
        db.close()
    baseline_path = newest_baseline_file(RESULTS)
    baseline = load_retrieval_baseline(baseline_path) if baseline_path else None
    baseline_name = baseline_path.name if baseline_path else "(none)"
    print(format_with_check(report, baseline, baseline_name))
    if client is not None:
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "created_at": stamp,
        "baseline_file": baseline_name,
        "course_a": manifest["course_a"],
        "course_b": manifest["course_b"],
        "uploads": ingested["uploads"],
        **report,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / f"with_check_{stamp}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    labels = out.with_suffix(".csv")
    write_answer_label_csv(report, labels)
    print(f"Wrote {out}")
    print(f"Wrote {labels}")
    return 0


def run_baseline() -> int:
    """Retrieval only. An ambient external-LLM flag must not turn this into a check."""
    saved_flag = os.environ.get("OFFICEHOURS_ALLOW_EXTERNAL_LLM")
    os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "false"
    try:
        return _run_baseline()
    finally:
        if saved_flag is None:
            os.environ.pop("OFFICEHOURS_ALLOW_EXTERNAL_LLM", None)
        else:
            os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = saved_flag


def _run_baseline() -> int:
    questions, manifest, ingested = _prepare()
    files = ingested["files"]
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


POWERSHELL_WITH_CHECK = r""".\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Study-agent retrieval baseline or answer check.",
        epilog=(
            "Windows PowerShell, from the repo root, with your own key:\n"
            '  $env:OFFICEHOURS_DEMO = "true"\n'
            '  $env:OFFICEHOURS_ALLOW_EXTERNAL_LLM = "true"\n'
            '  $env:GEMINI_API_KEY = "<your key>"\n'
            '  $env:GEMINI_MODEL = "gemini-3.8-flash"\n'
            '  $env:OFFICEHOURS_CLUSTERING_BACKEND = "sentence-transformers"\n'
            f"  {POWERSHELL_WITH_CHECK}\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--with-check",
        action="store_true",
        help="MiniLM, both filters, live Gemini answer check. Requires GEMINI_API_KEY.",
    )
    parser.add_argument(
        "--fake-check",
        action="store_true",
        help="Echo client. Prints only and does not write a results file.",
    )
    args = parser.parse_args(argv)
    if args.with_check and args.fake_check:
        print("Use either --with-check or --fake-check.")
        return 2
    if args.with_check:
        return run_with_check(None)
    if args.fake_check:
        return run_with_check(_EchoClient())
    return run_baseline()


if __name__ == "__main__":
    raise SystemExit(main())
