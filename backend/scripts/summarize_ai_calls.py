#!/usr/bin/env python3
"""Summarize structured ai_call JSON lines (stdin or file).

Expects lines from officehours.ai_call / gemini / youtube quota logs.
Never prints student content — only aggregates counts, latency, tokens, quota.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def _percentile(sorted_vals: list[float], p: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    idx = min(len(sorted_vals) - 1, max(0, int(round((p / 100.0) * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "path",
        nargs="?",
        help="Log file of JSON lines (default: stdin)",
    )
    args = parser.parse_args()
    if args.path:
        lines = Path(args.path).read_text(encoding="utf-8").splitlines()
    else:
        lines = sys.stdin.read().splitlines()

    by_key: dict[tuple[str, str], dict] = defaultdict(
        lambda: {
            "n": 0,
            "ok": 0,
            "error": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "quota_units": 0,
            "latencies": [],
        }
    )
    skipped = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            skipped += 1
            continue
        if row.get("event") != "ai_call":
            skipped += 1
            continue
        key = (str(row.get("agent") or "?"), str(row.get("tool") or "?"))
        bucket = by_key[key]
        bucket["n"] += 1
        status = str(row.get("status") or "")
        if status == "ok":
            bucket["ok"] += 1
        else:
            bucket["error"] += 1
        bucket["input_tokens"] += int(row.get("input_tokens") or 0)
        bucket["output_tokens"] += int(row.get("output_tokens") or 0)
        bucket["quota_units"] += int(row.get("quota_units") or 0)
        try:
            bucket["latencies"].append(float(row.get("latency_ms") or 0.0))
        except (TypeError, ValueError):
            pass

    print("ai_call summary")
    print(f"events={sum(b['n'] for b in by_key.values())} skipped_lines={skipped}")
    for (agent, tool), bucket in sorted(by_key.items()):
        lats = sorted(bucket["latencies"])
        p50 = _percentile(lats, 50)
        p95 = _percentile(lats, 95)
        mx = lats[-1] if lats else None
        print(
            f"agent={agent} tool={tool} n={bucket['n']} ok={bucket['ok']} "
            f"error={bucket['error']} input_tokens={bucket['input_tokens']} "
            f"output_tokens={bucket['output_tokens']} quota_units={bucket['quota_units']} "
            f"latency_ms_p50={p50} p95={p95} max={mx}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
