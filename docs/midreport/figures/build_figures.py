#!/usr/bin/env python3
"""Build the mid-report figures from the saved eval files. Standard library only.

    backend/venv/bin/python docs/midreport/figures/build_figures.py

matplotlib is not installed in this environment. The charts are SVG.
Wilson intervals use the 95% score interval. Counts stay the labels.
"""

from __future__ import annotations

import html
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASELINE = ROOT / "docs" / "eval_results" / "baseline_retrieval_only_20261010T180847Z.json"
CHECK = ROOT / "docs" / "eval_results" / "with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json"
Z95 = 1.959963984540054

CATEGORIES = (
    "in_document",
    "hard_negative",
    "unapproved_only",
    "other_course_only",
    "injection",
)


def wilson(correct: int, n: int) -> tuple[float, float]:
    if n <= 0:
        raise ValueError("wilson requires n > 0")
    phat = correct / n
    z2 = Z95 * Z95
    den = 1 + z2 / n
    center = phat + z2 / (2 * n)
    margin = Z95 * math.sqrt(phat * (1 - phat) / n + z2 / (4 * n * n))
    return max(0.0, (center - margin) / den), min(1.0, (center + margin) / den)


def _header(title: str, source: str, width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>text{font-family:Georgia,serif;fill:#1c1917} .small{font-size:12px} .title{font-size:18px}</style>",
        "<rect width=\"100%\" height=\"100%\" fill=\"#faf7f2\"/>",
        f'<text class="title" x="24" y="32">{html.escape(title)}</text>',
        f'<text class="small" x="24" y="52">{html.escape(source)}</text>',
    ]


def write_architecture() -> None:
    source = "Read from backend/app/ai/agent_policy.py, kb_agent_service.py, and gemini_client.py. Not measured."
    lines = _header("Study-agent architecture", source, 880, 460)
    boxes = [
        (40, 80, 250, 70, "Professor upload", "Stamp approved or rejected"),
        (40, 180, 250, 70, "Approved course chunks", "course_id, file, page, text"),
        (340, 80, 250, 70, "Student question", "POST /agent/ask"),
        (340, 180, 250, 90, "run_study_agent", "Local search, then one gate"),
        (640, 80, 200, 70, "Search", "Include threshold 0.35"),
        (640, 180, 200, 90, "verify_course_answer", "Gemini or Claude, at most once"),
        (340, 320, 250, 80, "API answer", "Checked, miss, staff, busy, or draft"),
        (640, 320, 200, 80, "Study Agent page", "Misses share one sentence"),
    ]
    lines.append('<g stroke="#44403c" stroke-width="1.2" fill="#fff">')
    for x, y, w, h, _title, _body in boxes:
        lines.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8"/>')
    lines.append("</g>")
    for x, y, _w, _h, title, body in boxes:
        lines.append(f'<text x="{x + 14}" y="{y + 28}" font-size="15">{html.escape(title)}</text>')
        lines.append(f'<text class="small" x="{x + 14}" y="{y + 50}">{html.escape(body)}</text>')
    lines.append("</svg>")
    (OUT / "architecture.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pipeline() -> None:
    source = "Order in run_study_agent. Defaults printed with the policy env vars unset."
    steps = [
        "1. Question longer than 2000 and kill switch on: busy, no search",
        "2. search_approved_entries (include threshold 0.35, course material only)",
        "3. No hit or top score below 0.42: staff form, no call",
        "4. Kill switch off: retrieval draft, no call",
        "5. Flag, demo, provider, or Gemini ack missing: retrieval draft, no call",
        "6. Breaker open: busy",
        "7. Global calls, global tokens, a window, or the input estimate: busy",
        "8. Cache hit: stored pass or stored refusal, no call",
        "9. One verify_course_answer (a dropped connection is retried once inside it)",
        "10. Pass within 600 characters: checked answer. Anything else: check miss",
    ]
    lines = _header("Orchestration pipeline", source, 820, 80 + 36 * len(steps))
    y = 84
    for step in steps:
        lines.append(f'<text class="small" x="32" y="{y}">{html.escape(step)}</text>')
        y += 36
    lines.append("</svg>")
    (OUT / "pipeline.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outcomes() -> None:
    source = "API strings from agent_policy.py and kb_agent_service.py. Page sentence from StudentAgentPage.jsx."
    lines = _header("Outcome states", source, 860, 420)
    states = [
        (40, 90, "passed", "Checked answer. Quote not shown."),
        (300, 90, "not_answerable", "Check miss. Model refused."),
        (560, 90, "failed closed", "Check miss. No retrieval fallback."),
        (40, 220, "below_cutoff", "Staff form. No model call."),
        (300, 220, "quota or busy", "Busy text. No retrieval fallback."),
        (560, 220, "guard or kill switch", "Retrieval draft. No model call."),
        (220, 330, "Study Agent page", "seek-help or matched_count 0 becomes one sentence."),
    ]
    lines.append('<g stroke="#44403c" fill="#fff">')
    for x, y, _title, _body in states:
        lines.append(f'<rect x="{x}" y="{y}" width="240" height="70" rx="8"/>')
    lines.append("</g>")
    for x, y, title, body in states:
        lines.append(f'<text x="{x + 12}" y="{y + 28}" font-size="15">{html.escape(title)}</text>')
        lines.append(f'<text class="small" x="{x + 12}" y="{y + 50}">{html.escape(body)}</text>')
    lines.append("</svg>")
    (OUT / "outcomes.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counts(blob: dict) -> dict[str, tuple[int, int]]:
    out = {}
    for name in CATEGORIES:
        cell = blob[name]
        out[name] = (int(cell["correct"]), int(cell["n"]))
    return out


def write_comparison(retrieval: dict[str, tuple[int, int]], checked: dict[str, tuple[int, int]]) -> None:
    source = (
        "Built from baseline_retrieval_only_20261010T180847Z.json "
        "(sentence-transformers, both_on) and "
        "with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json. "
        "Whiskers are 95% Wilson intervals on the correct/n rate."
    )
    width, height = 880, 460
    lines = _header("Retrieval-only versus with-check", source, width, height)
    left, right, top, bottom = 70, 840, 80, 380
    plot_h = bottom - top
    lines.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#44403c"/>')
    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#44403c"/>')
    slot = (right - left) / len(CATEGORIES)
    for index, name in enumerate(CATEGORIES):
        rk, rn = retrieval[name]
        ck, cn = checked[name]
        for offset, (correct, n, color) in enumerate(((rk, rn, "#b45309"), (ck, cn, "#1d4ed8"))):
            rate = correct / n
            lo, hi = wilson(correct, n)
            x = left + index * slot + 28 + offset * 36
            y = bottom - rate * plot_h
            h = rate * plot_h
            lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="28" height="{h:.1f}" fill="{color}"/>')
            y_lo = bottom - lo * plot_h
            y_hi = bottom - hi * plot_h
            lines.append(
                f'<line x1="{x + 14:.1f}" y1="{y_hi:.1f}" x2="{x + 14:.1f}" y2="{y_lo:.1f}" stroke="#111827"/>'
            )
            lines.append(f'<text class="small" x="{x - 4:.1f}" y="{y - 6:.1f}">{correct}/{n}</text>')
        lines.append(
            f'<text class="small" x="{left + index * slot + 16:.1f}" y="{bottom + 22}">{html.escape(name)}</text>'
        )
    lines.append('<rect x="70" y="410" width="14" height="14" fill="#b45309"/>')
    lines.append('<text class="small" x="90" y="422">Retrieval-only correct/n</text>')
    lines.append('<rect x="280" y="410" width="14" height="14" fill="#1d4ed8"/>')
    lines.append('<text class="small" x="300" y="422">With-check correct/n</text>')
    lines.append("</svg>")
    (OUT / "retrieval_vs_check.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_sweep(points: list[dict]) -> None:
    source = (
        "Built from baseline_retrieval_only_20261010T180847Z.json, "
        "backends.sentence-transformers.sections.agent_generated.modes.both_on.threshold_sweep. "
        "The production cutoff 0.42 is marked and was not changed."
    )
    width, height = 880, 480
    lines = _header("Threshold sweep, retrieval only", source, width, height)
    left, right, top, bottom = 70, 820, 80, 390
    lines.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="#44403c"/>')
    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" stroke="#44403c"/>')
    xs = [float(point["threshold"]) for point in points]
    xmin, xmax = min(xs), max(xs)

    def x_of(value: float) -> float:
        return left + (value - xmin) / (xmax - xmin) * (right - left)

    def y_of(value: float) -> float:
        return bottom - value / 55 * (bottom - top)

    series = (
        ("in_document_correct_citation", "#1d4ed8"),
        ("hard_negative_answered", "#b45309"),
        ("spurious_answer", "#7f1d1d"),
    )
    for key, color in series:
        coords = " ".join(f"{x_of(float(point['threshold'])):.1f},{y_of(float(point[key])):.1f}" for point in points)
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{coords}"/>')
    mark = x_of(0.42)
    lines.append(f'<line x1="{mark:.1f}" y1="{top}" x2="{mark:.1f}" y2="{bottom}" stroke="#44403c" stroke-dasharray="4 4"/>')
    lines.append(f'<text class="small" x="{mark + 6:.1f}" y="{top + 14}">0.42</text>')
    lines.append('<text class="small" x="70" y="430" fill="#1d4ed8">in-document correct citation</text>')
    lines.append('<text class="small" x="320" y="430" fill="#b45309">hard-negative answered</text>')
    lines.append('<text class="small" x="560" y="430" fill="#7f1d1d">spurious answers</text>')
    lines.append("</svg>")
    (OUT / "threshold_sweep.svg").write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_intervals(retrieval: dict[str, tuple[int, int]], checked: dict[str, tuple[int, int]]) -> None:
    print("wilson95 from the saved counts")
    for label, table in (("retrieval", retrieval), ("with_check", checked)):
        for name in CATEGORIES:
            correct, n = table[name]
            lo, hi = wilson(correct, n)
            print(f"{label} {name} {correct}/{n} {lo:.4f} {hi:.4f}")
    correct = sum(checked[name][0] for name in CATEGORIES)
    n = sum(checked[name][1] for name in CATEGORIES)
    lo, hi = wilson(correct, n)
    print(f"with_check overall {correct}/{n} {lo:.4f} {hi:.4f}")


def main() -> int:
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    checked = json.loads(CHECK.read_text(encoding="utf-8"))
    retrieval = _counts(
        baseline["backends"]["sentence-transformers"]["sections"]["agent_generated"]["modes"]["both_on"]["counts"]
    )
    checked_counts = _counts(checked["sections"]["agent_generated"]["counts"])
    sweep = baseline["backends"]["sentence-transformers"]["sections"]["agent_generated"]["modes"]["both_on"][
        "threshold_sweep"
    ]
    write_architecture()
    write_pipeline()
    write_outcomes()
    write_comparison(retrieval, checked_counts)
    write_sweep(sweep)
    print_intervals(retrieval, checked_counts)
    print(f"wrote figures under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
