"""The orchestration demo script finishes offline and covers the closed outcomes."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "demo_orchestration.py"

EXPECTED = [
    ("answered_verified_quote", "passed", "1", "-"),
    ("cache_hit", "cache_hit", "0", "-"),
    ("refused_by_model", "not_answerable", "1", "-"),
    ("below_0.42_cutoff", "below_cutoff", "0", "-"),
    ("question_length", "quota", "0", "question_length"),
    ("user_per_minute", "quota", "0", "user_per_minute"),
    ("user_per_day", "quota", "0", "user_per_day"),
    ("course_per_day", "quota", "0", "course_per_day"),
    ("global_calls", "quota", "0", "global_calls"),
    ("global_tokens", "quota", "0", "global_tokens"),
    ("input_tokens", "quota", "0", "input_tokens"),
    ("provider_error", "api_error", "1", "RuntimeError"),
    ("breaker_open", "busy", "0", "circuit_breaker"),
    ("timeout", "api_error", "2", "TimeoutError"),
    ("invalid_json", "invalid_json", "1", "JSONDecodeError"),
    ("quote_not_in_chunk", "unfaithful", "1", "unfaithful"),
    ("unknown_chunk_id", "unknown_chunk", "1", "unknown_chunk"),
    ("answer_too_long", "answer_too_long", "1", "answer_length"),
    ("kill_switch_off", "disabled", "0", "kill_switch"),
    ("external_flag_off", "flag_off", "0", "flag_off"),
    ("demo_mode_off", "demo_off", "0", "demo_off"),
    ("provider_off", "provider_off", "0", "provider_off"),
    ("free_tier_ack_off", "ack_off", "0", "ack_off"),
]


def test_demo_orchestration_script():
    env = os.environ.copy()
    for key in ("GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"):
        env.pop(key, None)
    env["DATABASE_URL"] = "sqlite:///:memory:"
    env["OFFICEHOURS_CLUSTERING_BACKEND"] = "lexical"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert "network was called" not in proc.stdout
    assert "fake_client network_blocked" in proc.stdout
    lines = [
        line.split(" | ")
        for line in proc.stdout.splitlines()
        if " | " in line and not line.startswith("scenario ")
    ]
    assert len(lines) == len(EXPECTED)
    for got, expected in zip(lines, EXPECTED):
        assert tuple(got[:4]) == expected
        assert float(got[4]) >= 0.0
