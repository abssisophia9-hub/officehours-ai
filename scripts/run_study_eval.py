#!/usr/bin/env python3
"""Run the retrieval-only baseline, or the answer-check comparison.

Default: four filter modes, MiniLM and lexical. The production answer cutoff
stays 0.42. Writes docs/eval_results/baseline_retrieval_only_<timestamp>.json.

Answer check (synthetic demo data only, your own key, MiniLM, both filters on).
From the repo root in Windows PowerShell:

    $env:OFFICEHOURS_DEMO = "true"
    $env:OFFICEHOURS_ALLOW_EXTERNAL_LLM = "true"
    $env:OFFICEHOURS_LLM_ENABLED = "true"
    $env:OFFICEHOURS_LLM_PROVIDER = "gemini"
    $env:OFFICEHOURS_GEMINI_FREE_TIER_ACK = "true"
    $env:GEMINI_API_KEY = "<your key>"
    $env:GEMINI_MODEL = "gemini-3.5-flash-lite"
    $env:OFFICEHOURS_CLUSTERING_BACKEND = "sentence-transformers"
    .\\backend\\venv\\Scripts\\python.exe scripts\\run_study_eval.py --with-check --provider gemini

Claude uses the same command with --provider claude, ANTHROPIC_API_KEY, and
ANTHROPIC_MODEL. The key is read from the environment and is not printed.
A real run writes JSON and a CSV of answered questions. The file name includes
the provider and model. --resume keeps finished questions. --rerun-errors
reruns only questions whose not-found came from an error.
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
from app.ai.claude_client import ANSWER_CHECK_PROMPT_VERSION  # noqa: E402
from app.ai.gemini_client import warn_gemini_free_tier  # noqa: E402
from app.eval.study_harness import (  # noqa: E402
    ANSWER_THRESHOLD,
    assert_flags_not_on_ask_route,
    checked_result_filename,
    configured_model,
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


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _refuse_live(provider: str) -> str | None:
    """None when a real run may start. The message never includes a key."""
    if provider not in {"gemini", "claude"}:
        return (
            "OFFICEHOURS_LLM_PROVIDER must be gemini or claude. "
            "Pass --provider. Refusing to call a model."
        )
    if not _truthy("OFFICEHOURS_ALLOW_EXTERNAL_LLM"):
        return "OFFICEHOURS_ALLOW_EXTERNAL_LLM must be true. Refusing to call a model."
    if not _truthy("OFFICEHOURS_DEMO"):
        return "OFFICEHOURS_DEMO must be true. Course material will not be sent."
    if provider == "gemini":
        if not _truthy("OFFICEHOURS_GEMINI_FREE_TIER_ACK"):
            return (
                "OFFICEHOURS_GEMINI_FREE_TIER_ACK is not true. "
                "The free tier may use prompts to improve Google products. "
                "Set it only when the run sends synthetic demo data."
            )
        if not os.getenv("GEMINI_API_KEY", "").strip():
            return (
                "GEMINI_API_KEY is not set. Refusing to call the model. "
                "Set it in your shell and run again. The key is not printed or stored."
            )
        return None
    if not os.getenv("ANTHROPIC_API_KEY", "").strip():
        return (
            "ANTHROPIC_API_KEY is not set. Refusing to call the model. "
            "Set it in your shell and run again. The key is not printed or stored."
        )
    return None


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)


def _load_prior(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if "sections" not in payload:
        raise ValueError(f"Results file has no sections: {path}")
    return payload


def run_with_check(client, *, provider=None, resume=None, rerun_errors=None) -> int:
    prior = None
    prior_path = None
    if client is None:
        chosen = (provider or os.getenv("OFFICEHOURS_LLM_PROVIDER") or "").strip().lower()
        refusal = _refuse_live(chosen)
        if refusal:
            print(refusal)
            return 2
        os.environ["OFFICEHOURS_LLM_PROVIDER"] = chosen
        os.environ["OFFICEHOURS_CLUSTERING_BACKEND"] = "sentence-transformers"
        model = configured_model(chosen)
        print(f"Provider: {chosen}")
        print(f"Model: {model}")
        print(f"Prompt version: {ANSWER_CHECK_PROMPT_VERSION}")
        print("API key is present. It is not printed or written.")
        if chosen == "gemini":
            warn_gemini_free_tier()
        provider = chosen
    else:
        os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
        print("Fake client. Counts are not a live model result. No results file is written.")
        provider = None

    if resume or rerun_errors:
        prior_path = Path(resume or rerun_errors)
        try:
            prior = _load_prior(prior_path)
        except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
            print(str(exc) if str(exc) else f"Could not read {prior_path}")
            return 2

    questions, manifest, ingested = _prepare()
    baseline_path = newest_baseline_file(RESULTS)
    baseline = load_retrieval_baseline(baseline_path) if baseline_path else None
    baseline_name = baseline_path.name if baseline_path else "(none)"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = None
    if client is None:
        model_for_name = configured_model(provider) or "unknown"
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / checked_result_filename(provider or "unset", model_for_name, stamp)

    def on_progress(report: dict) -> None:
        if out is None:
            return
        _write_json(out, _payload(report))

    def _payload(report: dict) -> dict:
        return {
            "created_at": stamp,
            "baseline_file": baseline_name,
            "course_a": manifest["course_a"],
            "course_b": manifest["course_b"],
            "uploads": ingested["uploads"],
            "resumed_from": str(prior_path) if prior_path else None,
            **report,
        }

    db = SessionLocal()
    try:
        report = evaluate_with_check(
            db,
            ingested["course_a_id"],
            questions,
            ingested["files"],
            client=client,
            checker_label="fake" if client is not None else provider,
            provider=provider,
            prior=prior,
            rerun_errors_only=rerun_errors is not None,
            on_progress=on_progress if client is None else None,
        )
    finally:
        db.close()
    print(format_with_check(report, baseline, baseline_name))
    if report.get("stopped"):
        print(
            f"Stopped on {report['stopped']}. Finished questions are in the results file. "
            "Run the same command with --resume <file> after the quota window resets. "
            "Use --rerun-errors <file> to rerun only error rows."
        )
    if client is not None:
        return 0
    assert out is not None
    _write_json(out, _payload(report))
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


POWERSHELL_WITH_CHECK = r".\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini"
POWERSHELL_RESUME = r".\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini --resume docs\eval_results\with_check_gemini_gemini-3.5-flash-lite_<stamp>.json"
POWERSHELL_RERUN_ERRORS = r".\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini --rerun-errors docs\eval_results\with_check_gemini_gemini-3.5-flash-lite_<stamp>.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Study-agent retrieval baseline or answer check.",
        epilog=(
            "Windows PowerShell, from the repo root, with your own key:\n"
            '  $env:OFFICEHOURS_DEMO = "true"\n'
            '  $env:OFFICEHOURS_ALLOW_EXTERNAL_LLM = "true"\n'
            '  $env:OFFICEHOURS_LLM_ENABLED = "true"\n'
            '  $env:OFFICEHOURS_LLM_PROVIDER = "gemini"\n'
            '  $env:OFFICEHOURS_GEMINI_FREE_TIER_ACK = "true"\n'
            '  $env:GEMINI_API_KEY = "<your key>"\n'
            '  $env:GEMINI_MODEL = "gemini-3.5-flash-lite"\n'
            '  $env:OFFICEHOURS_CLUSTERING_BACKEND = "sentence-transformers"\n'
            f"  {POWERSHELL_WITH_CHECK}\n"
            f"  {POWERSHELL_RESUME}\n"
            f"  {POWERSHELL_RERUN_ERRORS}\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--with-check",
        action="store_true",
        help="MiniLM, both filters, live answer check. Requires --provider and that provider's API key.",
    )
    parser.add_argument(
        "--provider",
        choices=("gemini", "claude"),
        help="Answer-check provider. Overrides OFFICEHOURS_LLM_PROVIDER for this run.",
    )
    parser.add_argument(
        "--resume",
        help="Results JSON to continue. Keeps finished questions and reruns errors and questions that never ran.",
    )
    parser.add_argument(
        "--rerun-errors",
        help="Results JSON. Reruns only questions whose not-found came from an error (429, timeout, invalid JSON).",
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
    if args.resume and args.rerun_errors:
        print("Use either --resume or --rerun-errors.")
        return 2
    if (args.resume or args.rerun_errors) and not args.with_check:
        print("--resume and --rerun-errors require --with-check.")
        return 2
    if args.with_check:
        return run_with_check(
            None,
            provider=args.provider,
            resume=args.resume,
            rerun_errors=args.rerun_errors,
        )
    if args.fake_check:
        return run_with_check(_EchoClient())
    return run_baseline()


if __name__ == "__main__":
    raise SystemExit(main())
