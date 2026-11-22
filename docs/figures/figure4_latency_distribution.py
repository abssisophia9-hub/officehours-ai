"""Quote-check latency for the saved Gemini run.

Reads the 42 calls with check.called true in
docs/eval_results/with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json.
The usage block stores the median (857.98 ms) and the worst call (5,413.82 ms).
It does not store a 95th percentile. This script computes that percentile from
the same 42 latencies (linear method) and draws it with the median and the maximum.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "docs/eval_results/with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json"
OUT = Path(__file__).resolve().parent / "figure4_latency_distribution.png"

SLA_MS = 3000.0


def linear_percentile(values: list[float], percent: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percent / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def main() -> None:
    data = json.loads(RUN.read_text())
    questions = data["sections"]["agent_generated"]["questions"]
    called = [q["check"]["latency_ms"] for q in questions if q["check"].get("called")]
    if len(called) != 42:
        raise SystemExit(f"expected 42 called latencies, found {len(called)}")
    median = data["usage"]["latency_ms_median_called"]
    worst = data["usage"]["latency_ms_worst_called"]
    p95 = linear_percentile(called, 95)
    labels = [
        f"Median\n{median:,.2f} ms",
        f"95th percentile\n{p95:,.2f} ms",
        f"Maximum\n{worst:,.2f} ms",
    ]
    values = [median, p95, worst]

    fig, ax = plt.subplots(figsize=(8.4, 3.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    positions = [2, 1, 0]
    ax.barh(positions, values, color=["#4C4C4C", "#7A7A7A", "#B0B0B0"], height=0.62, zorder=2)
    ax.axvline(SLA_MS, color="#000000", linestyle="--", linewidth=1.1, zorder=3)
    ax.text(
        SLA_MS + 80,
        2.45,
        "3,000 ms median target",
        color="#000000",
        fontsize=9,
        va="bottom",
    )
    ax.set_yticks(positions, labels, fontsize=10)
    ax.set_xlabel("Latency (ms)", fontsize=10, color="#000000")
    ax.set_xlim(0, 6200)
    ax.set_title(
        "Quote-check-only latency, 42 calls\n"
        "gemini-3.5-flash-lite, 25 October 2026",
        fontsize=12,
        color="#000000",
        loc="left",
        pad=10,
    )
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.spines["left"].set_color("#000000")
    ax.spines["bottom"].set_color("#000000")
    ax.tick_params(colors="#000000")
    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")
    print(f"n={len(called)} median={median} p95={p95:.2f} max={worst}")


if __name__ == "__main__":
    main()
