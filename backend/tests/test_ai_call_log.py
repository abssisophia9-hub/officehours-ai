"""Structured ai_call logs omit student content and aggregate cleanly."""

from __future__ import annotations

import io
import json
import logging
import runpy
import sys
from pathlib import Path

from app.services import ai_call_log
from app.services.ai_call_log import log_ai_call


def test_log_ai_call_json_has_required_fields_no_content():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger = ai_call_log._LOGGER
    logger.addHandler(handler)
    try:
        log_ai_call(
            agent="study",
            tool="answer_check",
            status="ok",
            latency_ms=12.5,
            input_tokens=10,
            output_tokens=3,
            provider="gemini",
            model="gemini-test",
            extra={"question": "should never appear", "user_id": 99},
        )
    finally:
        logger.removeHandler(handler)

    payload = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert payload["event"] == "ai_call"
    assert payload["agent"] == "study"
    assert payload["tool"] == "answer_check"
    assert payload["status"] == "ok"
    assert payload["input_tokens"] == 10
    assert payload["output_tokens"] == 3
    assert "question" not in payload
    assert "user_id" not in payload
    blob = json.dumps(payload)
    assert "should never appear" not in blob


def test_summarize_ai_calls_script(tmp_path, capsys):
    log_path = tmp_path / "ai.jsonl"
    rows = [
        {
            "event": "ai_call",
            "agent": "pedagogy",
            "tool": "youtube_search_list",
            "status": "ok",
            "latency_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "quota_units": 1,
        },
        {
            "event": "ai_call",
            "agent": "study",
            "tool": "answer_check",
            "status": "ok",
            "latency_ms": 100,
            "input_tokens": 50,
            "output_tokens": 5,
            "quota_units": 0,
        },
    ]
    log_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    script = Path(__file__).resolve().parents[1] / "scripts" / "summarize_ai_calls.py"
    old = sys.argv
    try:
        sys.argv = ["summarize_ai_calls.py", str(log_path)]
        try:
            runpy.run_path(str(script), run_name="__main__")
        except SystemExit as exc:
            assert exc.code == 0
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "ai_call summary" in out
    assert "agent=pedagogy" in out
    assert "quota_units=1" in out
    assert "agent=study" in out
