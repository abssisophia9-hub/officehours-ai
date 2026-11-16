#!/usr/bin/env python3
"""Publication-style figures for the SSE poster slots.

Drawn with matplotlib to the official dashed-cell content size.
Charts use the repo's own evaluation JSON. They are labeled as
curated / silver checks, not a campus trial.

Official cells (hRule=exact) and the inches we embed:
  OPTIONAL VISUAL                      cell 1.15in   figure 1.05in
  PROPOSED DESIGN FIGURE               cell 2.55in   figure 2.20in
  PLANNED WORK / REQUIREMENTS VISUAL   cell 0.70in   figure 0.62in
  PROPOSED PROCESS / PIPELINE          cell 2.29in   figure 2.00in
  PLANNED EVALUATION FRAMEWORK         cell 2.33in   figure 2.05in
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent / "poster_figures"
ROOT = HERE.parents[2]
REPORTS = ROOT / "reports" / "final_report"
DPI = 220

# Stay inside the dashed cell's content box (cell height minus 0.125in
# padding, width minus 0.14in). Taller images paint over the section text.
# Width must stay under the two-column cell. A wider PNG is clipped on the
# right even when the Word extent is smaller, because the image keeps its
# own aspect ratio.
SLOT_IN = {
    "gap": (6.00, 0.92),
    "arch": (6.00, 2.28),
    "road": (6.00, 0.52),
    "pipe": (6.00, 2.10),
    "eval": (6.00, 2.12),
}

INK = "#1B1F1E"
MUTED = "#3E4946"
GREEN = "#0B6E4F"
GREEN_SOFT = "#E5F2EC"
SLATE = "#5C6764"
RULE = "#1B1F1E"
HAIR = "#D5DBD8"
PAPER = "#FFFFFF"


def _fonts() -> None:
    for name in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-Bold.ttf"):
        font_manager.fontManager.addfont(f"/usr/share/fonts/truetype/macos/{name}")
    plt.rcParams.update(
        {
            "font.family": "Inter",
            "font.size": 8,
            "text.color": INK,
            "axes.labelcolor": INK,
            "axes.edgecolor": RULE,
            "axes.linewidth": 0.6,
            "xtick.color": INK,
            "ytick.color": INK,
            "xtick.major.width": 0.6,
            "ytick.major.width": 0.6,
            "figure.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "axes.facecolor": PAPER,
        }
    )


def _save(fig: plt.Figure, name: str, inches: tuple[float, float]) -> Path:
    HERE.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    path = HERE / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    im = Image.open(path)
    expect = (round(inches[0] * DPI), round(inches[1] * DPI))
    if abs(im.size[0] - expect[0]) > 2 or abs(im.size[1] - expect[1]) > 2:
        raise SystemExit(f"{name} is {im.size}, expected {expect}")
    im.save(FIGS / name, "PNG")
    return path


def _blank(key: str) -> tuple[plt.Figure, plt.Axes]:
    w, h = SLOT_IN[key]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.axis("off")
    return fig, ax


def _arrow(ax, x0, y0, x1, y1):
    ax.annotate(
        "",
        xy=(x1, y1),
        xytext=(x0, y0),
        arrowprops={
            "arrowstyle": "-|>",
            "color": INK,
            "lw": 0.8,
            "mutation_scale": 7,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=3,
    )


def _box(ax, x, y, w, h, title, sub="", *, face=PAPER, edge=INK, lw=0.8, title_pt=8.0, sub_pt=6.4):
    ax.add_patch(
        Rectangle((x, y), w, h, facecolor=face, edgecolor=edge, linewidth=lw, joinstyle="miter", zorder=2)
    )
    cx = x + w / 2
    if sub:
        ax.text(cx, y + h * 0.62, title, ha="center", va="center", fontsize=title_pt, fontweight="bold", color=INK, zorder=4)
        ax.text(cx, y + h * 0.30, sub, ha="center", va="center", fontsize=sub_pt, color=MUTED, zorder=4)
    else:
        ax.text(cx, y + h / 2, title, ha="center", va="center", fontsize=title_pt, fontweight="bold", color=INK, zorder=4)


def slot_gap() -> Path:
    """OPTIONAL VISUAL — capability gap as a presence matrix, not a score."""
    w, h = SLOT_IN["gap"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes((0.22, 0.10, 0.76, 0.74))
    rows = ["Local triage model", "Dual-TA matcher", "Stamp before AI quote", "Quiet ask to staff"]
    cols = ["LMS inbox", "Piazza / Ed", "Open chatbot", "OfficeHours"]
    data = [
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ]
    ax.imshow(data, cmap=ListedColormap(["#F4F6F5", GREEN]), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(cols)), cols, fontsize=7.5)
    ax.set_yticks(range(len(rows)), rows, fontsize=7.5)
    ax.tick_params(length=0, pad=2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(len(cols) + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(len(rows) + 1)], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2)
    ax.tick_params(which="minor", length=0)
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            ax.text(
                j,
                i,
                "yes" if val else "—",
                ha="center",
                va="center",
                fontsize=8,
                color="white" if val else SLATE,
                fontweight="medium",
            )
    fig.text(0.02, 0.90, "Gap map  ·  capability present or absent  ·  not a measured score", fontsize=8.5, fontweight="bold", color=INK)
    return _save(fig, "SLOT_gap.png", SLOT_IN["gap"])


def slot_architecture() -> Path:
    """PROPOSED DESIGN FIGURE — C4-style container diagram."""
    fig, ax = _blank("arch")
    w, h = SLOT_IN["arch"]
    ax.text(0.08, h - 0.16, "Containers  ·  one app, local models, Canvas as the external system", fontsize=9, fontweight="bold", color=INK, va="center")

    top_y, top_h = 1.32, 0.74
    side, gap = 0.08, 0.16
    top_w = (w - 2 * side - 2 * gap) / 3
    xs = [side + i * (top_w + gap) for i in range(3)]
    _box(ax, xs[0], top_y, top_w, top_h, "officehours-app", "React  ·  :5180  ·  3 roles", title_pt=8, sub_pt=6.2)
    _box(ax, xs[1], top_y, top_w, top_h, "FastAPI", "REST · SQL  ·  SQLite → Postgres", face=GREEN_SOFT, title_pt=8, sub_pt=6.0)
    _box(ax, xs[2], top_y, top_w, top_h, "Canvas LMS", "LTI 1.3  ·  external", face="#F7F7F5", edge=SLATE, title_pt=8, sub_pt=6.2)
    mid_y = top_y + top_h / 2
    _arrow(ax, xs[0] + top_w, mid_y, xs[1], mid_y)
    _arrow(ax, xs[1] + top_w, mid_y, xs[2], mid_y)
    # Ask Triage boundary behind the first three components.
    bot_y, bot_h = 0.08, 0.98
    bot_gap = 0.08
    bot_w = (w - 2 * side - 4 * bot_gap) / 5
    bxs = [side + i * (bot_w + bot_gap) for i in range(5)]
    ax.add_patch(
        FancyBboxPatch(
            (bxs[0] - 0.06, bot_y - 0.05),
            3 * bot_w + 2 * bot_gap + 0.12,
            bot_h + 0.10,
            boxstyle="square,pad=0",
            facecolor="#F7FBFA",
            edgecolor=GREEN,
            linewidth=0.7,
            linestyle=(0, (2.2, 1.4)),
            zorder=1,
        )
    )
    ax.text(bxs[0] - 0.02, bot_y + bot_h + 0.02, "Ask Triage · local", fontsize=6.2, color=GREEN, fontweight="bold", va="bottom")
    components = [
        ("Analyzer", "MiniLM + LogReg"),
        ("Matcher", "TA + queue blend"),
        ("Synthesizer", "approved-KB RAG"),
        ("Stamp", "professor gate"),
        ("Study Agent", "stamped KB only"),
    ]
    for i, (title, sub) in enumerate(components):
        face = GREEN_SOFT if i < 3 else PAPER
        edge = GREEN if i < 3 else INK
        _box(ax, bxs[i], bot_y, bot_w, bot_h, title, sub, face=face, edge=edge, title_pt=7.4, sub_pt=5.8)
        if i < len(components) - 1:
            _arrow(ax, bxs[i] + bot_w, bot_y + bot_h / 2, bxs[i + 1], bot_y + bot_h / 2)
    # Drop from the API into Ask Triage.
    _arrow(ax, xs[1] + top_w / 2, top_y, xs[1] + top_w / 2, bot_y + bot_h + 0.06)
    return _save(fig, "SLOT_architecture.png", SLOT_IN["arch"])


def slot_pipeline() -> Path:
    """PROPOSED PROCESS / PIPELINE — methods flowchart with stage brackets."""
    fig, ax = _blank("pipe")
    w, h = SLOT_IN["pipe"]
    ax.text(0.08, h - 0.16, "Ask path  ·  input, local triage, human gate, student-facing output", fontsize=9, fontweight="bold", va="center")

    steps = [
        ("1  Ask", "Quiet or named", "INPUT"),
        ("2  Analyzer", "MiniLM + LogReg", "PROCESS"),
        ("3  Matcher", "dual-TA + wait", "PROCESS"),
        ("4  Synthesizer", "approved-KB RAG", "PROCESS"),
        ("5  TA + stamp", "Help Coach · KB", "OUTPUT"),
        ("6  Study Agent", "stamped quotes", "OUTPUT"),
    ]
    margin, arrow_g = 0.08, 0.12
    bw = (w - 2 * margin - arrow_g * (len(steps) - 1)) / len(steps)
    by, bh = 0.22, 1.42
    xs = [margin + i * (bw + arrow_g) for i in range(len(steps))]
    bands = [("INPUT", 0, 1, "#F4F6F5"), ("PROCESS", 1, 4, GREEN_SOFT), ("OUTPUT", 4, 6, "#F7F7F5")]
    for label, a, b, face in bands:
        x0, x1 = xs[a], xs[b - 1] + bw
        ax.add_patch(Rectangle((x0, h - 0.48), x1 - x0, 0.22, facecolor=face, edgecolor=HAIR, linewidth=0.6, zorder=1))
        ax.text((x0 + x1) / 2, h - 0.37, label, ha="center", va="center", fontsize=7, fontweight="bold", color=INK)
    for i, (title, sub, _band) in enumerate(steps):
        _box(ax, xs[i], by, bw, bh, title, sub, title_pt=7.2, sub_pt=6.0)
        if i < len(steps) - 1:
            _arrow(ax, xs[i] + bw, by + bh / 2, xs[i + 1], by + bh / 2)
    ax.text(0.08, 0.10, "External LLM stays off. Study Agent quotes nothing the professor has not stamped.", fontsize=6.4, color=MUTED, va="center")
    return _save(fig, "SLOT_pipeline.png", SLOT_IN["pipe"])


def slot_roadmap() -> Path:
    """PLANNED WORK — milestone stem plot. The cell is 0.70in, so one axis, not five tiny rows."""
    w, h = SLOT_IN["road"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes((0.03, 0.28, 0.96, 0.66))
    events = [
        (0.6, "1  Roles + auth", True),
        (1.8, "2  TA / KB gate", True),
        (3.0, "3  Rooms + demo", True),
        (4.2, "4  LTI live", False),
        (5.2, "5  Postgres", False),
    ]
    ax.axvspan(3.5, 5.7, color="#F4F6F5", zorder=0)
    ax.plot([0.35, 5.55], [0, 0], color=INK, lw=0.9, zorder=1)
    for x, label, done in events:
        ax.plot([x], [0], marker="o", ms=5.5, color=GREEN if done else PAPER, markeredgecolor=GREEN, markeredgewidth=1.1, zorder=3)
        ax.text(x, 0.55, label, ha="center", va="bottom", fontsize=7.2, fontweight="bold", color=INK)
    ax.set_xlim(0.15, 5.85)
    ax.set_ylim(-1.15, 1.35)
    ax.set_yticks([])
    ax.set_xticks([0.6, 3.2, 5.3])
    ax.set_xticklabels(["Sep 2026", "campus IT", "deadline"], fontsize=6.5, color=MUTED)
    ax.tick_params(axis="x", length=0, pad=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("filled = demo built     open = waits on IT        sequence, not a week schedule", fontsize=6.2, color=MUTED, labelpad=1)
    return _save(fig, "SLOT_roadmap.png", SLOT_IN["road"])


def _load_metrics() -> tuple[dict, dict, list[tuple[str, float]]]:
    clf = json.loads((REPORTS / "classifier_evaluation.json").read_text())
    matcher = json.loads((REPORTS / "matcher_evaluation.json").read_text())
    gold = json.loads((REPORTS / "gold_label_evaluation.json").read_text())
    short = {
        "academic_integrity": "integrity",
        "accessibility_accommodation": "access need",
        "conceptual_question": "concept",
        "emotional_stress": "stress",
        "exam_logistics": "exam logistics",
        "grading_dispute": "grading",
        "office_hours_access": "office access",
        "project_submission": "submission",
        "retake_request": "retake",
        "uncategorized": "other",
    }
    per_class = []
    for label, row in clf["classification_report"].items():
        if label in short and isinstance(row, dict) and "f1-score" in row:
            per_class.append((short[label], float(row["f1-score"])))
    per_class.sort(key=lambda item: item[1])
    summary = {
        "analyzer_cv_acc": float(clf["accuracy"]),
        "analyzer_cv_f1": float(clf["macro_f1"]),
        "analyzer_n": int(clf["dataset_size"]),
        "matcher_hold_acc": float(matcher["metrics"]["accuracy"]),
        "matcher_hold_n": int(matcher["metrics"]["n"]),
        "analyzer_gold_acc": float(gold["analyzer"]["accuracy"]),
        "matcher_gold_acc": float(gold["matcher"]["accuracy"]),
        "gold_n": int(gold["analyzer"]["n"]),
    }
    return summary, matcher, per_class


def slot_evaluation() -> Path:
    """PLANNED EVALUATION — real curated checks, plotted, with the caveat on the figure."""
    summary, _matcher, per_class = _load_metrics()
    w, h = SLOT_IN["eval"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    fig.text(0.02, 0.93, "Preliminary checks  ·  curated labels, not a campus trial", fontsize=9, fontweight="bold", va="center")

    ax = fig.add_axes((0.07, 0.22, 0.36, 0.62))
    import numpy as np

    labels = ["Analyzer", "Matcher"]
    holdout = [summary["analyzer_cv_acc"] * 100, summary["matcher_hold_acc"] * 100]
    gold = [summary["analyzer_gold_acc"] * 100, summary["matcher_gold_acc"] * 100]
    x = np.arange(len(labels))
    width = 0.34
    b1 = ax.bar(x - width / 2, holdout, width, color=GREEN, zorder=2)
    b2 = ax.bar(x + width / 2, gold, width, color="#B7C4BE", edgecolor=GREEN, linewidth=0.6, zorder=2)
    ax.set_ylabel("Accuracy (%)", fontsize=7)
    ax.set_xticks(x, labels, fontsize=8)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(axis="y", labelsize=6.5, length=2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.grid(True, color=HAIR, lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    for bars in (b1, b2):
        for bar in bars:
            val = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2, val + 1.5, f"{val:.0f}", ha="center", va="bottom", fontsize=6.5, color=INK)
    ax.set_title("Accuracy", fontsize=8, loc="left", pad=2, color=INK)

    ax2 = fig.add_axes((0.55, 0.18, 0.43, 0.66))
    names = [n for n, _ in per_class]
    scores = [s * 100 for _, s in per_class]
    ax2.barh(names, scores, color=GREEN, height=0.72, zorder=2)
    ax2.axvline(summary["analyzer_cv_f1"] * 100, color=SLATE, lw=0.7, ls=(0, (2, 1.5)), zorder=3)
    ax2.set_xlim(0, 100)
    ax2.set_xlabel("F1 (%)", fontsize=7)
    ax2.tick_params(axis="y", labelsize=6.4, length=0)
    ax2.tick_params(axis="x", labelsize=6.5, length=2)
    ax2.set_xticks([0, 50, 100])
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.xaxis.grid(True, color=HAIR, lw=0.5, zorder=0)
    ax2.set_axisbelow(True)
    ax2.set_title("Analyzer CV  ·  per-class F1", fontsize=8, loc="left", pad=2)

    fig.text(
        0.02,
        0.045,
        f"Green = dev holdout (Analyzer CV n={summary['analyzer_n']}, Matcher silver n={summary['matcher_hold_n']}).  "
        f"Gray = curated gold n={summary['gold_n']}, not campus TA labels.  "
        f"Dashed line = macro-F1 {summary['analyzer_cv_f1']*100:.0f}%.",
        fontsize=6.0,
        color=MUTED,
    )
    return _save(fig, "SLOT_evaluation.png", SLOT_IN["eval"])


def build_all() -> dict[str, Path]:
    _fonts()
    paths = {
        "gap": slot_gap(),
        "arch": slot_architecture(),
        "road": slot_roadmap(),
        "pipe": slot_pipeline(),
        "eval": slot_evaluation(),
    }
    for key, path in paths.items():
        im = Image.open(path)
        wi, hi = SLOT_IN[key]
        print(f"{path.name:24} {im.size}  ({wi:.2f}in x {hi:.2f}in @ {DPI}dpi)")
    return paths


if __name__ == "__main__":
    build_all()
