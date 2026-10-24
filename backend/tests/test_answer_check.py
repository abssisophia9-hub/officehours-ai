"""Answer check between retrieval and the reply. No network and no API key."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")

import csv
import json
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.ai.claude_client import ANSWER_CHECK_SYSTEM, verify_course_answer
from app.ai.claude_client_legacy import _call_claude, _complete_claude
from app.database.session import Base, SessionLocal, engine
from app.eval.study_harness import (
    ANSWER_LABEL_COLUMNS,
    ANSWER_CHECK_PROMPT_VERSION,
    ANSWER_THRESHOLD,
    checked_result_filename,
    corpus_files,
    evaluate,
    evaluate_with_check,
    format_with_check,
    ingest_corpus,
    load_questions,
    load_retrieval_baseline,
    miss_source_for,
    newest_baseline_file,
    write_answer_label_csv,
)
from app.main import app
from app.models.knowledge import KnowledgeEntry
from app.services.kb_agent_service import (
    CHECK_MISS_ANSWER,
    WEAK_MATCH_CONFIDENCE,
    answer_from_knowledge_base,
)

REPO = Path(__file__).resolve().parents[2]
QUESTIONS = REPO / "docs" / "eval_questions" / "study_agent_questions.json"
MANIFEST = REPO / "backend" / "demo_data" / "eval" / "manifest.json"
DEMO_ROOT = REPO / "backend" / "demo_data"
RESULTS = REPO / "docs" / "eval_results"
NOW = datetime.now(timezone.utc)
SECRET = "sk-test-secret-do-not-log"


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def explode(request, timeout=0):
        raise AssertionError("network was called")

    monkeypatch.setattr("app.ai.claude_client_legacy.urllib.request.urlopen", explode)
    monkeypatch.setattr("app.ai.gemini_client.urllib.request.urlopen", explode)
    monkeypatch.setenv("OFFICEHOURS_LLM_ENABLED", "true")
    monkeypatch.setenv("OFFICEHOURS_LLM_RPM", "100000")
    from app.ai.agent_policy import reset_policy_state

    reset_policy_state()


def _entry(**overrides) -> KnowledgeEntry:
    fields = {
        "id": 11,
        "question_text": "Notes — part 1",
        "answer_draft": "The stack pop returns the top value.",
        "student_hint": "Check the top pointer.",
        "tags": "",
        "status": "approved",
        "source_filename": "notes.pdf",
        "page_number": 3,
        "chunk_index": 2,
        "course_id": 4242,
        "entry_kind": "course_material",
        "created_at": NOW,
        "updated_at": NOW,
    }
    fields.update(overrides)
    return KnowledgeEntry(**fields)


def _patch_search(monkeypatch, rows):
    monkeypatch.setattr(
        "app.services.kb_agent_service.search_approved_entries",
        lambda *args, **kwargs: rows,
    )


class ScriptedClient:
    def __init__(self, steps):
        self.steps = list(steps)
        self.calls = []

    def complete(self, *, system, user):
        self.calls.append({"system": system, "user": user})
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        text = step if isinstance(step, str) else json.dumps(step)
        return SimpleNamespace(
            text=text,
            model="fake-model",
            input_tokens=10,
            output_tokens=4,
            latency_ms=8.0,
        )


def _ask(monkeypatch, client, rows, records=None):
    _patch_search(monkeypatch, rows)
    return answer_from_knowledge_base(
        None,
        "What does stack pop return?",
        answer_checker=client,
        check_records=records,
    )


def _hit(similarity=0.80, **overrides):
    return (_entry(**overrides), similarity)


def test_answerable_with_a_verbatim_quote(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    quote = "The stack pop returns the top value."
    other = _entry(
        id=12,
        answer_draft="A queue removes from the front.",
        source_filename="other.pdf",
        page_number=4,
        chunk_index=1,
    )
    client = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 12,
                "answer": "A queue removes from the front.",
                "quote": "removes from the front.",
            }
        ]
    )
    records = []
    response = _ask(
        monkeypatch,
        client,
        [_hit(), (other, 0.70)],
        records,
    )
    assert len(client.calls) == 1
    sent = json.loads(client.calls[0]["user"])
    assert set(sent) == {"question", "chunks"}
    assert [chunk["chunk_id"] for chunk in sent["chunks"]] == [11, 12]
    assert "course_id" not in client.calls[0]["user"]
    assert "4242" not in client.calls[0]["user"]
    assert "DATA" in client.calls[0]["system"]
    assert ANSWER_CHECK_SYSTEM == client.calls[0]["system"]
    assert response.should_seek_help is False
    assert response.matched_count == 1
    assert response.sources[0].entry.id == 12
    assert response.sources[0].entry.source_filename == "other.pdf"
    assert "removes from the front." in response.answer
    assert "other.pdf, p. 4, chunk 1" in response.answer
    assert quote not in response.answer
    assert records[0]["outcome"] == "passed"
    assert records[0]["called"] is True
    assert records[0]["short_answer"] == "A queue removes from the front."
    assert records[0]["quote"] == "removes from the front."
    assert records[0]["citation"] == "other.pdf, p. 4, chunk 1"
    assert records[0]["input_tokens"] == 10
    assert records[0]["output_tokens"] == 4
    assert records[0]["model"] == "fake-model"
    assert records[0]["latency_ms"] == 8.0


def test_quote_missing_from_the_cited_chunk_is_rejected(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 11,
                "answer": "It returns the top value.",
                "quote": "this sentence is not in the chunk",
            }
        ]
    )
    response = _ask(monkeypatch, client, [_hit()])
    assert len(client.calls) == 1
    assert response.should_seek_help is True
    assert response.matched_count == 0
    assert response.sources == []
    assert response.answer == CHECK_MISS_ANSWER


def test_quote_from_a_different_chunk_is_rejected(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    other = _entry(id=12, answer_draft="A queue removes from the front.")
    client = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 11,
                "answer": "A queue removes from the front.",
                "quote": "A queue removes from the front.",
            }
        ]
    )
    response = _ask(monkeypatch, client, [_hit(), (other, 0.6)])
    assert len(client.calls) == 1
    assert response.answer == CHECK_MISS_ANSWER
    assert response.matched_count == 0


def test_invalid_json_fails_closed_without_a_retry(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(["this is not json", {"answerable": True}])
    records = []
    response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 1
    assert records[0]["outcome"] == "invalid_json"
    assert response.answer == CHECK_MISS_ANSWER
    assert response.should_seek_help is True


def test_string_true_is_invalid(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            {
                "answerable": "true",
                "supporting_chunk_id": 11,
                "answer": "The stack pop returns the top value.",
                "quote": "The stack pop returns the top value.",
            }
        ]
    )
    records = []
    response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 1
    assert records[0]["outcome"] == "invalid_json"
    assert response.matched_count == 0


def test_unknown_chunk_id_is_rejected(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 999999,
                "answer": "The stack pop returns the top value.",
                "quote": "The stack pop returns the top value.",
            }
        ]
    )
    records = []
    response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 1
    assert records[0]["outcome"] == "unknown_chunk"
    assert response.answer == CHECK_MISS_ANSWER


def test_api_error_fails_closed_after_one_retry(monkeypatch, caplog):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            urllib.error.URLError(SECRET),
            urllib.error.URLError(SECRET),
            {"answerable": True},
        ]
    )
    records = []
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 2
    assert records[0]["outcome"] == "api_error"
    assert records[0]["error_type"] == "URLError"
    assert response.answer == CHECK_MISS_ANSWER
    assert response.should_seek_help is True
    assert response.matched_count == 0
    assert SECRET not in caplog.text


def test_non_transport_error_is_not_retried(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient([RuntimeError("ANTHROPIC_API_KEY missing")])
    records = []
    response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 1
    assert records[0]["outcome"] == "api_error"
    assert records[0]["error_type"] == "RuntimeError"
    assert response.answer == CHECK_MISS_ANSWER


def test_timeout_then_valid_json_passes_on_the_retry(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            TimeoutError(),
            {
                "answerable": True,
                "supporting_chunk_id": 11,
                "answer": "It returns the top value.",
                "quote": "returns the top value.",
            },
        ]
    )
    response = _ask(monkeypatch, client, [_hit()])
    assert len(client.calls) == 2
    assert response.should_seek_help is False
    assert "returns the top value." in response.answer
    assert "notes.pdf, p. 3, chunk 2" in response.answer


def test_not_answerable_is_not_found(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            {
                "answerable": False,
                "supporting_chunk_id": None,
                "answer": None,
                "quote": None,
            }
        ]
    )
    records = []
    response = _ask(monkeypatch, client, [_hit()], records)
    assert len(client.calls) == 1
    assert records[0]["outcome"] == "not_answerable"
    assert response.answer == CHECK_MISS_ANSWER


def test_flag_off_matches_retrieval_and_does_not_call(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    rows = [_hit(), _hit(0.55, id=12, answer_draft="A queue removes from the front.")]
    client = ScriptedClient([])
    records = []
    response = _ask(monkeypatch, client, rows, records)
    assert client.calls == []
    assert records[0]["outcome"] == "flag_off"
    assert records[0]["called"] is False
    assert response.should_seek_help is False
    assert response.matched_count == 2
    assert response.answer.startswith("Based on professor-approved course knowledge")
    assert "The stack pop returns the top value." in response.answer
    assert "notes.pdf, p. 3, chunk 2" in response.answer


def test_demo_off_with_external_on_does_not_call(monkeypatch, caplog):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    client = ScriptedClient([])
    records = []
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        response = _ask(monkeypatch, client, [_hit()], records)
    assert client.calls == []
    assert records[0]["outcome"] == "demo_off"
    assert response.answer.startswith("Based on professor-approved course knowledge")
    assert "The stack pop returns the top value." in response.answer
    assert caplog.text.count("OFFICEHOURS_DEMO is off") == 1
    assert SECRET not in caplog.text


def test_score_below_cutoff_does_not_call(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient([])
    records = []
    response = _ask(monkeypatch, client, [_hit(0.4199)], records)
    assert client.calls == []
    assert records[0]["outcome"] == "below_cutoff"
    assert records[0]["called"] is False
    assert "quiet ask" in response.answer.lower()
    assert response.should_seek_help is True
    assert response.matched_count == 0


def test_score_at_cutoff_does_call(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    client = ScriptedClient(
        [
            {
                "answerable": True,
                "supporting_chunk_id": 11,
                "answer": "It returns the top value.",
                "quote": "returns the top value.",
            }
        ]
    )
    response = _ask(monkeypatch, client, [_hit(0.42)])
    assert len(client.calls) == 1
    assert response.should_seek_help is False


def test_only_three_chunks_are_sent(monkeypatch):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    rows = [
        _hit(0.9, id=1, answer_draft="alpha chunk text"),
        _hit(0.8, id=2, answer_draft="beta chunk text"),
        _hit(0.7, id=3, answer_draft="gamma chunk text"),
        _hit(0.6, id=4, answer_draft="delta chunk text"),
    ]
    client = ScriptedClient(
        [
            {
                "answerable": False,
                "supporting_chunk_id": None,
                "answer": None,
                "quote": None,
            }
        ]
    )
    _ask(monkeypatch, client, rows)
    sent = json.loads(client.calls[0]["user"])
    assert [chunk["chunk_id"] for chunk in sent["chunks"]] == [1, 2, 3]
    assert "delta chunk text" not in client.calls[0]["user"]


def test_direct_verify_refuses_when_demo_is_off(monkeypatch, caplog):
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "true")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "false")
    client = ScriptedClient([])
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        result = verify_course_answer(
            "What does stack pop return?",
            [{"chunk_id": 11, "file": "notes.pdf", "page": 3, "text": "alpha", "course_id": 4242}],
            client=client,
        )
    assert client.calls == []
    assert result.outcome == "demo_off"
    assert result.called is False


def test_complete_reads_model_from_the_environment_and_hides_the_key(monkeypatch, caplog):
    captured = {}

    class _Body:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(
                {
                    "model": "claude-test-model",
                    "content": [{"type": "text", "text": "{\"ok\": true}"}],
                    "usage": {"input_tokens": 3, "output_tokens": 4},
                }
            ).encode()

    def capture(request, timeout=0):
        captured["timeout"] = timeout
        captured["body"] = json.loads(request.data.decode())
        captured["key"] = request.get_header("X-api-key")
        return _Body()

    monkeypatch.setattr("app.ai.claude_client_legacy.urllib.request.urlopen", capture)
    monkeypatch.setenv("ANTHROPIC_API_KEY", SECRET)
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test-model")
    with caplog.at_level("DEBUG"):
        done = _complete_claude("system", "user", max_tokens=400, temperature=0, timeout=10)
    assert captured["body"]["model"] == "claude-test-model"
    assert captured["body"]["max_tokens"] == 400
    assert captured["body"]["temperature"] == 0
    assert captured["timeout"] == 10
    assert captured["key"] == SECRET
    assert done.input_tokens == 3
    assert done.output_tokens == 4
    assert done.text == "{\"ok\": true}"
    assert SECRET not in caplog.text

    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    legacy = {}

    def capture_legacy(request, timeout=0):
        legacy["timeout"] = timeout
        legacy["body"] = json.loads(request.data.decode())
        return _Body()

    monkeypatch.setattr("app.ai.claude_client_legacy.urllib.request.urlopen", capture_legacy)
    _call_claude("system", "user")
    assert legacy["body"]["model"] == "claude-haiku-5-5"
    assert legacy["body"]["max_tokens"] == 800
    assert "temperature" not in legacy["body"]
    assert legacy["timeout"] == 20


def _run_eval(args, extra_env):
    import subprocess
    import sys

    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = ""
    env["GEMINI_API_KEY"] = ""
    env["OFFICEHOURS_LLM_PROVIDER"] = ""
    env["OFFICEHOURS_GEMINI_FREE_TIER_ACK"] = ""
    env["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] = "true"
    env["OFFICEHOURS_DEMO"] = "true"
    env["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "run_study_eval.py"), *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_with_check_refuses_without_a_key():
    missing_provider = _run_eval(["--with-check"], {"GEMINI_API_KEY": SECRET})
    assert missing_provider.returncode == 2
    assert "OFFICEHOURS_LLM_PROVIDER must be gemini or claude" in missing_provider.stdout
    assert SECRET not in missing_provider.stdout
    assert SECRET not in missing_provider.stderr

    missing_gemini = _run_eval(
        ["--with-check", "--provider", "gemini"],
        {"OFFICEHOURS_GEMINI_FREE_TIER_ACK": "true", "GEMINI_API_KEY": ""},
    )
    assert missing_gemini.returncode == 2
    assert "GEMINI_API_KEY is not set" in missing_gemini.stdout
    assert SECRET not in missing_gemini.stdout

    missing_ack = _run_eval(
        ["--with-check", "--provider", "gemini"],
        {"GEMINI_API_KEY": SECRET, "OFFICEHOURS_GEMINI_FREE_TIER_ACK": "false"},
    )
    assert missing_ack.returncode == 2
    assert "OFFICEHOURS_GEMINI_FREE_TIER_ACK is not true" in missing_ack.stdout
    assert SECRET not in missing_ack.stdout
    assert SECRET not in missing_ack.stderr

    missing_claude = _run_eval(["--with-check", "--provider", "claude"], {})
    assert missing_claude.returncode == 2
    assert "ANTHROPIC_API_KEY is not set" in missing_claude.stdout
    assert SECRET not in missing_claude.stdout
    assert SECRET not in missing_claude.stderr


class _EchoClient:
    def __init__(self):
        self.calls = 0

    def complete(self, *, system, user):
        self.calls += 1
        payload = json.loads(user)
        chunk = payload["chunks"][0]
        if not chunk["text"]:
            body = {
                "answerable": False,
                "supporting_chunk_id": None,
                "answer": None,
                "quote": None,
            }
        else:
            body = {
                "answerable": True,
                "supporting_chunk_id": chunk["chunk_id"],
                "answer": "From the supplied chunk.",
                "quote": chunk["text"],
            }
        return SimpleNamespace(
            text=json.dumps(body),
            model="fake-echo",
            input_tokens=11,
            output_tokens=7,
            latency_ms=4.0,
        )


def test_harness_with_fake_client_reports_beside_the_baseline(monkeypatch):
    assert WEAK_MATCH_CONFIDENCE == 0.42
    assert ANSWER_THRESHOLD == 0.42
    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")
    monkeypatch.setenv("OFFICEHOURS_DEMO", "true")
    monkeypatch.setenv("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = corpus_files(manifest)
    ingested = ingest_corpus(TestClient(app), manifest, DEMO_ROOT)
    questions = load_questions(QUESTIONS)
    echo = _EchoClient()
    db = SessionLocal()
    try:
        retrieval = evaluate(db, ingested["course_a_id"], questions, files)
        report = evaluate_with_check(
            db,
            ingested["course_a_id"],
            questions,
            files,
            client=echo,
        )
    finally:
        db.close()
    assert os.environ["OFFICEHOURS_ALLOW_EXTERNAL_LLM"] == "false"
    both = retrieval["sections"]["agent_generated"]["modes"]["both_on"]
    retrieval_answered = sum(1 for row in both["questions"] if row["answered"])
    assert report["checker"] == "fake"
    assert report["sections"]["human_written"]["n"] == 0
    assert report["usage"]["calls"] == retrieval_answered == echo.calls
    assert report["usage"]["questions"] == 75
    checked = report["sections"]["agent_generated"]["counts"]
    for category, count in both["counts"].items():
        assert checked[category]["n"] == count["n"]
        assert checked[category]["correct"] == count["correct"]
        assert checked[category]["spurious_answer"] == count["spurious_answer"]
        assert checked[category]["wrong_source"] == count["wrong_source"]
        assert checked[category]["hidden_page_cited"] == count["hidden_page_cited"]
    assert report["usage"]["input_tokens"] == retrieval_answered * 11
    assert report["usage"]["output_tokens"] == retrieval_answered * 7
    assert report["usage"]["input_tokens_per_question"] == round(report["usage"]["input_tokens"] / 75, 2)
    assert report["usage"]["latency_ms_worst"] >= report["usage"]["latency_ms_median"]

    path = newest_baseline_file(RESULTS)
    assert path is not None
    baseline = load_retrieval_baseline(path)
    text = format_with_check(report, baseline, path.name)
    base_hard = baseline["backends"]["sentence-transformers"]["sections"]["agent_generated"]["modes"]["both_on"]["counts"]["hard_negative"]
    assert f"hard_negative spurious_answer baseline {base_hard['spurious_answer']}/{base_hard['n']}" in text
    assert "11/20" in text
    assert "human_written: 0 questions" in text
    assert "not merged with agent_generated" in text
    assert "fake" in text
    assert "$" not in text
    assert "not a live model" in text
    injection = [
        row
        for row in report["sections"]["agent_generated"]["questions"]
        if row["category"] == "injection"
    ]
    answered_n = sum(1 for row in injection if row["answered"])
    hidden_n = sum(1 for row in injection if row["hidden_page_cited"])
    assert (
        f"injection answered {answered_n}/{len(injection)}, "
        f"hidden_page_cited {hidden_n}/{len(injection)}"
    ) in text


def test_real_run_command_uses_the_windows_venv():
    source = (REPO / "scripts" / "run_study_eval.py").read_text(encoding="utf-8")
    command = r".\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini"
    assert command in source
    assert "python scripts/run_study_eval.py --with-check" not in source
    assert "--resume" in source
    assert "--rerun-errors" in source


def test_summary_counts_answered_injection_questions():
    usage = {
        "calls": 0,
        "latency_ms_median": 0,
        "latency_ms_worst": 0,
        "latency_ms_median_called": 0,
        "latency_ms_worst_called": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "input_tokens_per_question": 0,
        "output_tokens_per_question": 0,
    }
    report = {
        "checker": "fake",
        "embedding_backend": "lexical",
        "sections": {
            "agent_generated": {
                "n": 2,
                "counts": {
                    "injection": {
                        "n": 2,
                        "correct": 1,
                        "hidden_page_cited": 1,
                        "spurious_answer": 0,
                        "wrong_source": 0,
                    }
                },
                "questions": [
                    {"category": "injection", "answered": True, "hidden_page_cited": True},
                    {"category": "injection", "answered": False, "hidden_page_cited": False},
                ],
                "usage": usage,
            },
            "human_written": {"n": 0, "counts": {}, "questions": [], "usage": usage},
        },
    }
    text = format_with_check(report, None, "(none)")
    assert "injection answered 1/2, hidden_page_cited 1/2" in text
    assert "$" not in text


def test_label_csv_lists_only_answered_questions(tmp_path):
    report = {
        "sections": {
            "agent_generated": {
                "questions": [
                    {
                        "id": "q1",
                        "category": "in_document",
                        "question": "What does pop return?",
                        "answered": True,
                        "retrieved": {"citation": "notes.pdf, p. 3, chunk 2"},
                        "check": {
                            "short_answer": "It returns the top.",
                            "quote": "returns the top, then stops.\nNext line",
                            "citation": "notes.pdf, p. 3, chunk 2",
                        },
                    },
                    {
                        "id": "q2",
                        "category": "hard_negative",
                        "question": "What is the exam date?",
                        "answered": False,
                        "check": {"short_answer": "should not appear"},
                    },
                ]
            },
            "human_written": {"questions": []},
        }
    }
    path = tmp_path / "with_check_test.csv"
    write_answer_label_csv(report, path)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert list(rows[0]) == list(ANSWER_LABEL_COLUMNS)
    assert len(rows) == 1
    assert rows[0]["id"] == "q1"
    assert rows[0]["category"] == "in_document"
    assert rows[0]["question"] == "What does pop return?"
    assert rows[0]["answer"] == "It returns the top."
    assert rows[0]["quote"] == "returns the top, then stops.\nNext line"
    assert rows[0]["citation"] == "notes.pdf, p. 3, chunk 2"
    assert rows[0]["supported"] == ""
    assert rows[0]["unsupported"] == ""
    raw = path.read_text(encoding="utf-8-sig")
    assert "course_id" not in raw
    assert "email" not in raw.lower()
    assert "should not appear" not in raw


def _gemini_env(monkeypatch, *, ack="true", provider="gemini", allow="true", demo="true"):
    from app.ai.gemini_client import reset_throttle

    monkeypatch.setenv("OFFICEHOURS_ALLOW_EXTERNAL_LLM", allow)
    monkeypatch.setenv("OFFICEHOURS_DEMO", demo)
    if provider is None:
        monkeypatch.delenv("OFFICEHOURS_LLM_PROVIDER", raising=False)
    else:
        monkeypatch.setenv("OFFICEHOURS_LLM_PROVIDER", provider)
    monkeypatch.setenv("OFFICEHOURS_GEMINI_FREE_TIER_ACK", ack)
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    monkeypatch.setenv("OFFICEHOURS_LLM_RPM", "100000")
    reset_throttle()


def _gemini_body(answerable=True, chunk_id=11, answer="It returns the top value.", quote="returns the top value."):
    return {
        "modelVersion": "gemini-3.5-flash-lite",
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps(
                                {
                                    "answerable": answerable,
                                    "supporting_chunk_id": chunk_id,
                                    "answer": answer,
                                    "quote": quote,
                                }
                            )
                        }
                    ]
                }
            }
        ],
        "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 12},
    }


class _GeminiResponse:
    def __init__(self, payload):
        self._raw = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._raw


def _http_error(status, body):
    import email.message
    import io

    encoded = body if isinstance(body, bytes) else body.encode()
    return urllib.error.HTTPError(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent",
        status,
        "error",
        email.message.Message(),
        io.BytesIO(encoded),
    )


def _install_gemini_http(monkeypatch, steps, sleeps=None):
    calls = []

    def urlopen(request, timeout=0):
        calls.append({"request": request, "timeout": timeout})
        step = steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return _GeminiResponse(step)

    monkeypatch.setattr("app.ai.gemini_client.urllib.request.urlopen", urlopen)
    if sleeps is not None:
        monkeypatch.setattr("app.ai.gemini_client.time.sleep", lambda seconds: sleeps.append(seconds))
    return calls


def _assert_key_hidden(calls, caplog):
    assert calls
    request = calls[0]["request"]
    assert request.get_header("X-goog-api-key") == SECRET
    assert SECRET not in request.full_url
    assert SECRET not in caplog.text
    for call in calls:
        assert SECRET not in call["request"].full_url


def test_gemini_valid_reply_uses_json_schema_and_hides_the_key(monkeypatch, caplog):
    _gemini_env(monkeypatch)
    calls = _install_gemini_http(monkeypatch, [_gemini_body()])
    with caplog.at_level("DEBUG"):
        result = verify_course_answer(
            "What does stack pop return?",
            [{"chunk_id": 11, "file": "notes.pdf", "page": 3, "text": "The stack pop returns the top value."}],
        )
    assert result.outcome == "passed"
    assert result.quote == "returns the top value."
    assert result.model == "gemini-3.5-flash-lite"
    assert result.input_tokens == 20
    assert result.output_tokens == 12
    request = calls[0]["request"]
    body = json.loads(request.data.decode())
    assert calls[0]["timeout"] == 10
    assert body["generationConfig"]["temperature"] == 0
    assert body["generationConfig"]["maxOutputTokens"] == 400
    mime = body["generationConfig"]["responseFormat"]["text"]
    assert mime["mimeType"] == "APPLICATION_JSON"
    assert mime["schema"]["required"] == ["answerable", "supporting_chunk_id", "answer", "quote"]
    sent = json.loads(body["contents"][0]["parts"][0]["text"])
    assert set(sent) == {"question", "chunks"}
    assert "4242" not in request.data.decode()
    assert "GEMINI_API_KEY" not in request.full_url
    _assert_key_hidden(calls, caplog)


def test_gemini_invalid_json_fails_closed(monkeypatch, caplog):
    _gemini_env(monkeypatch)
    payload = _gemini_body()
    payload["candidates"][0]["content"]["parts"][0]["text"] = "not json"
    calls = _install_gemini_http(monkeypatch, [payload])
    with caplog.at_level("DEBUG"):
        response = _ask(monkeypatch, None, [_hit()])
    assert len(calls) == 1
    assert response.answer == CHECK_MISS_ANSWER
    assert SECRET not in caplog.text


def test_gemini_quote_not_in_the_chunk_fails_closed(monkeypatch, caplog):
    _gemini_env(monkeypatch)
    calls = _install_gemini_http(
        monkeypatch,
        [_gemini_body(quote="this sentence is not in the chunk")],
    )
    with caplog.at_level("DEBUG"):
        records = []
        response = _ask(monkeypatch, None, [_hit()], records)
    assert len(calls) == 1
    assert records[0]["outcome"] == "unfaithful"
    assert response.answer == CHECK_MISS_ANSWER
    assert SECRET not in caplog.text


def test_gemini_429_then_success(monkeypatch):
    _gemini_env(monkeypatch)
    sleeps = []
    calls = _install_gemini_http(
        monkeypatch,
        [_http_error(429, '{"error": {"code": 429, "message": "Too many requests"}}'), _gemini_body()],
        sleeps,
    )
    result = verify_course_answer(
        "What does stack pop return?",
        [{"chunk_id": 11, "file": "notes.pdf", "page": 3, "text": "The stack pop returns the top value."}],
    )
    assert result.outcome == "passed"
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_gemini_503_then_success(monkeypatch):
    _gemini_env(monkeypatch)
    sleeps = []
    calls = _install_gemini_http(
        monkeypatch,
        [_http_error(503, '{"error": {"code": 503, "message": "unavailable"}}'), _gemini_body()],
        sleeps,
    )
    result = verify_course_answer(
        "What does stack pop return?",
        [{"chunk_id": 11, "file": "notes.pdf", "page": 3, "text": "The stack pop returns the top value."}],
    )
    assert result.outcome == "passed"
    assert len(calls) == 2
    assert sleeps == [1.0]


def test_gemini_429_exhausted_fails_closed(monkeypatch, caplog):
    _gemini_env(monkeypatch)
    sleeps = []
    body = json.dumps({"error": {"code": 429, "message": "Too many requests", "detail": SECRET}})
    calls = _install_gemini_http(monkeypatch, [_http_error(429, body) for _ in range(3)], sleeps)
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        records = []
        response = _ask(monkeypatch, None, [_hit()], records)
    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]
    assert records[0]["outcome"] == "rate_limited"
    assert response.answer == CHECK_MISS_ANSWER
    assert "answer_check rate_limit_exhausted provider=gemini attempts=3" in caplog.text
    assert SECRET not in caplog.text


def test_gemini_daily_quota_is_not_retried(monkeypatch, caplog):
    _gemini_env(monkeypatch)
    sleeps = []
    body = json.dumps(
        {
            "error": {
                "code": 429,
                "message": "Quota exceeded",
                "details": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}],
            }
        }
    )
    calls = _install_gemini_http(monkeypatch, [_http_error(429, body)], sleeps)
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        records = []
        response = _ask(monkeypatch, None, [_hit()], records)
    assert len(calls) == 1
    assert sleeps == []
    assert records[0]["outcome"] == "daily_quota"
    assert response.answer == CHECK_MISS_ANSWER
    assert "answer_check daily_quota provider=gemini" in caplog.text
    assert SECRET not in caplog.text


def test_provider_unset_keeps_the_retrieval_answer(monkeypatch):
    _gemini_env(monkeypatch, provider=None)
    records = []
    response = _ask(monkeypatch, None, [_hit()], records)
    assert records[0]["outcome"] == "provider_off"
    assert records[0]["called"] is False
    assert response.answer.startswith("Based on professor-approved course knowledge")


def test_gemini_without_ack_keeps_the_retrieval_answer(monkeypatch, caplog):
    from app.ai import claude_client

    claude_client._ack_warned = False
    _gemini_env(monkeypatch, ack="false")
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        records = []
        response = _ask(monkeypatch, None, [_hit()], records)
    assert records[0]["outcome"] == "ack_off"
    assert records[0]["called"] is False
    assert response.answer.startswith("Based on professor-approved course knowledge")
    assert "OFFICEHOURS_GEMINI_FREE_TIER_ACK is not true" in caplog.text
    assert "synthetic demo data" in caplog.text
    assert SECRET not in caplog.text


def test_allow_off_does_not_call_gemini(monkeypatch):
    _gemini_env(monkeypatch, allow="false")
    records = []
    response = _ask(monkeypatch, None, [_hit()], records)
    assert records[0]["outcome"] == "flag_off"
    assert response.answer.startswith("Based on professor-approved course knowledge")


def test_demo_off_does_not_call_gemini(monkeypatch):
    _gemini_env(monkeypatch, demo="false")
    records = []
    response = _ask(monkeypatch, None, [_hit()], records)
    assert records[0]["outcome"] == "demo_off"
    assert response.answer.startswith("Based on professor-approved course knowledge")


def test_claude_provider_still_checks_without_the_gemini_ack(monkeypatch):
    _gemini_env(monkeypatch, provider="claude", ack="false")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def fake_complete(*args, **kwargs):
        return SimpleNamespace(
            text=json.dumps(
                {
                    "answerable": True,
                    "supporting_chunk_id": 11,
                    "answer": "It returns the top value.",
                    "quote": "returns the top value.",
                }
            ),
            model="claude-haiku-5-5",
            input_tokens=2,
            output_tokens=2,
            latency_ms=1.0,
        )

    monkeypatch.setattr("app.ai.claude_client_legacy._complete_claude", fake_complete)
    records = []
    response = _ask(monkeypatch, None, [_hit()], records)
    assert records[0]["outcome"] == "passed"
    assert records[0]["model"] == "claude-haiku-5-5"
    assert "returns the top value." in response.answer


def test_startup_warns_when_gemini_is_selected(monkeypatch, caplog):
    import app.ai.gemini_client as gemini_client

    gemini_client._free_tier_warned = False
    monkeypatch.setenv("OFFICEHOURS_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", SECRET)
    with caplog.at_level("WARNING", logger="officehours.answer_check"):
        with TestClient(app):
            pass
    assert "Google may use prompts to improve its products" in caplog.text
    assert "Only synthetic demo data may be sent" in caplog.text
    assert SECRET not in caplog.text


def test_throttle_waits_when_the_window_is_full(monkeypatch):
    from app.ai.gemini_client import _throttle, reset_throttle

    monkeypatch.setenv("OFFICEHOURS_LLM_RPM", "2")
    reset_throttle()
    clock = {"now": 1000.0}
    sleeps = []

    def monotonic():
        return clock["now"]

    def sleep(seconds):
        sleeps.append(seconds)
        clock["now"] += seconds

    monkeypatch.setattr("app.ai.gemini_client.time.monotonic", monotonic)
    monkeypatch.setattr("app.ai.gemini_client.time.sleep", sleep)
    _throttle()
    _throttle()
    _throttle()
    assert sleeps
    assert sleeps[0] == pytest.approx(60.0)
    reset_throttle()


def test_result_filename_includes_provider_and_model():
    assert (
        checked_result_filename("gemini", "gemini-3.5-flash-lite", "20261024T160000Z")
        == "with_check_gemini_gemini-3.5-flash-lite_20261024T160000Z.json"
    )


def test_miss_source_splits_model_refusal_from_errors():
    assert miss_source_for({"outcome": "not_answerable"}) == "model"
    assert miss_source_for({"outcome": "invalid_json"}) == "error"
    assert miss_source_for({"outcome": "api_error"}) == "error"
    assert miss_source_for({"outcome": "rate_limited"}) == "error"
    assert miss_source_for({"outcome": "daily_quota"}) == "error"
    assert miss_source_for({"outcome": "below_cutoff"}) == "cutoff"
    assert miss_source_for({"outcome": "passed"}) is None
    assert ANSWER_CHECK_PROMPT_VERSION == "study-answer-check-v1"


def _mini_row(qid, question):
    return {
        "id": qid,
        "category": "in_document",
        "question": question,
        "expected": "not_found",
        "expected_source": None,
        "author": "agent_generated",
    }


def _mini_questions(*rows):
    return {"agent_generated": list(rows), "human_written": []}


def _stored_detail(qid, outcome):
    return {
        "id": qid,
        "category": "in_document",
        "question": qid,
        "expected": "not_found",
        "expected_source": None,
        "author": "agent_generated",
        "correct": True,
        "answered": outcome == "passed",
        "hidden_page_cited": False,
        "spurious_answer": False,
        "wrong_source": False,
        "cited_page_kind": "none",
        "retrieved": None,
        "agent_confidence": 0.5,
        "blended_score": 0.0,
        "blended_source": None,
        "blended_file": None,
        "blended_page": None,
        "blended_matches_expected": False,
        "blended_page_kind": "none",
        "check": {
            "called": outcome != "below_cutoff",
            "outcome": outcome,
            "model": "gemini-3.5-flash-lite",
            "input_tokens": 1,
            "output_tokens": 1,
            "latency_ms": 1.0,
            "error_type": None,
        },
    }


def test_resume_keeps_finished_questions_and_reruns_errors(monkeypatch):
    called = []
    outcomes = ["invalid_json", "passed"]

    def fake_answer(db, question, **kwargs):
        called.append(question)
        outcome = outcomes.pop(0)
        kwargs["check_records"].append(
            {
                "called": True,
                "outcome": outcome,
                "model": "gemini-3.5-flash-lite",
                "input_tokens": 4,
                "output_tokens": 3,
                "latency_ms": 2.0,
                "error_type": "invalid_json" if outcome == "invalid_json" else None,
            }
        )
        return SimpleNamespace(
            should_seek_help=True,
            matched_count=0,
            sources=[],
            confidence=0.2,
        )

    monkeypatch.setattr("app.eval.study_harness.answer_from_knowledge_base", fake_answer)
    monkeypatch.setattr("app.eval.study_harness.best_blended_hit", lambda *args, **kwargs: None)
    prior = {
        "sections": {
            "agent_generated": {
                "questions": [
                    _stored_detail("q1", "passed"),
                    _stored_detail("q2", "invalid_json"),
                    _stored_detail("q3", "not_answerable"),
                ]
            },
            "human_written": {"questions": []},
        }
    }
    questions = _mini_questions(
        _mini_row("q1", "kept success"),
        _mini_row("q2", "rerun error"),
        _mini_row("q3", "kept refusal"),
        _mini_row("q4", "never ran"),
    )
    files = {"pending_a": set(), "approved_b": set(), "approved_a": set()}
    saved = os.environ.get("OFFICEHOURS_ALLOW_EXTERNAL_LLM")
    report = evaluate_with_check(
        None,
        1,
        questions,
        files,
        client=object(),
        provider="gemini",
        prior=prior,
    )
    assert called == ["rerun error", "never ran"]
    assert [row["id"] for row in report["sections"]["agent_generated"]["questions"]] == [
        "q1",
        "q2",
        "q3",
        "q4",
    ]
    by_id = {row["id"]: row for row in report["sections"]["agent_generated"]["questions"]}
    assert by_id["q1"]["miss_source"] is None
    assert by_id["q2"]["miss_source"] == "error"
    assert by_id["q3"]["miss_source"] == "model"
    assert by_id["q2"]["prompt_version"] == ANSWER_CHECK_PROMPT_VERSION
    assert by_id["q3"]["model"] == "gemini-3.5-flash-lite"
    assert os.environ.get("OFFICEHOURS_ALLOW_EXTERNAL_LLM") == saved

    outcomes.append("passed")
    called.clear()
    rerun = evaluate_with_check(
        None,
        1,
        questions,
        files,
        client=object(),
        prior=prior,
        rerun_errors_only=True,
    )
    assert called == ["rerun error"]
    assert [row["id"] for row in rerun["sections"]["agent_generated"]["questions"]] == ["q1", "q2", "q3"]


def test_quota_stop_keeps_finished_questions(monkeypatch):
    called = []
    outcomes = ["passed", "daily_quota", "passed"]

    def fake_answer(db, question, **kwargs):
        called.append(question)
        outcome = outcomes.pop(0)
        kwargs["check_records"].append(
            {
                "called": True,
                "outcome": outcome,
                "model": "gemini-3.5-flash-lite",
                "input_tokens": 1,
                "output_tokens": 1,
                "latency_ms": 1.0,
                "error_type": "daily_quota" if outcome == "daily_quota" else None,
            }
        )
        return SimpleNamespace(should_seek_help=True, matched_count=0, sources=[], confidence=0.2)

    monkeypatch.setattr("app.eval.study_harness.answer_from_knowledge_base", fake_answer)
    monkeypatch.setattr("app.eval.study_harness.best_blended_hit", lambda *args, **kwargs: None)
    snapshots = []
    questions = _mini_questions(
        _mini_row("q1", "first"),
        _mini_row("q2", "quota"),
        _mini_row("q3", "after"),
    )
    files = {"pending_a": set(), "approved_b": set(), "approved_a": set()}
    report = evaluate_with_check(
        None,
        1,
        questions,
        files,
        client=object(),
        provider="gemini",
        on_progress=snapshots.append,
    )
    assert called == ["first", "quota"]
    assert report["stopped"] == "daily_quota"
    assert [row["id"] for row in report["sections"]["agent_generated"]["questions"]] == ["q1", "q2"]
    assert snapshots[-1]["stopped"] == "daily_quota"
    assert report["prompt_version"] == ANSWER_CHECK_PROMPT_VERSION
    text = format_with_check(report, None, "(none)")
    assert "not_found model 0 error 1" in text
    assert "Stopped on daily_quota" in text
    assert "$" not in text
