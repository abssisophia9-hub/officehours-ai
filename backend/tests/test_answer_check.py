"""Answer check between retrieval and the reply. No network and no API key."""

import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("OFFICEHOURS_CLUSTERING_BACKEND", "lexical")
os.environ.setdefault("OFFICEHOURS_DEMO", "true")
os.environ.setdefault("OFFICEHOURS_ALLOW_EXTERNAL_LLM", "false")

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
    ANSWER_THRESHOLD,
    corpus_files,
    evaluate,
    evaluate_with_check,
    format_with_check,
    ingest_corpus,
    load_questions,
    load_retrieval_baseline,
    newest_baseline_file,
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


def test_with_check_refuses_without_a_key():
    import subprocess
    import sys

    env = os.environ.copy()
    env["ANTHROPIC_API_KEY"] = ""
    env["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "run_study_eval.py"), "--with-check"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "ANTHROPIC_API_KEY is not set" in result.stdout
    assert SECRET not in result.stdout
    assert SECRET not in result.stderr


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
