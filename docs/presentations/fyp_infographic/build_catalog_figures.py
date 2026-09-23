#!/usr/bin/env python3
"""Official SSE dashed-cell figures. No port numbers. Employer-first labels."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyBboxPatch, Rectangle
from PIL import Image
import qrcode

HERE = Path(__file__).resolve().parent
FIGS = HERE / "figures"
ROOT = HERE.parents[2]
REPORTS = ROOT / "reports" / "final_report"
REPO = "https://github.com/abssisophia9-hub/officehours-ai"
DPI = 220

# Official cell content sizes (must stay inside the dashed boxes).
SLOT_IN = {
    "gap": (6.00, 0.92),
    "arch": (6.00, 2.28),
    "road": (6.00, 0.52),
    "pipe": (6.00, 2.10),
    "eval": (6.00, 2.12),
}

INK = "#1B1F1E"
MUTED = "#3E4946"
GREEN = "#006633"
GREEN_SOFT = "#E5F2EC"
SLATE = "#5C6764"
HAIR = "#D5DBD8"
PAPER = "#FFFFFF"
AMBER = "#9A3412"
TEAL = "#0F766E"


def _fonts() -> None:
    for name in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-Bold.ttf"):
        font_manager.fontManager.addfont(f"/usr/share/fonts/truetype/macos/{name}")
    plt.rcParams.update(
        {
            "font.family": "Inter",
            "font.size": 8,
            "text.color": INK,
            "figure.facecolor": PAPER,
            "savefig.facecolor": PAPER,
            "axes.facecolor": PAPER,
        }
    )


def _save(fig: plt.Figure, name: str, inches: tuple[float, float]) -> Path:
    FIGS.mkdir(parents=True, exist_ok=True)
    path = FIGS / name
    fig.savefig(path, dpi=DPI)
    plt.close(fig)
    im = Image.open(path)
    expect = (round(inches[0] * DPI), round(inches[1] * DPI))
    if abs(im.size[0] - expect[0]) > 2 or abs(im.size[1] - expect[1]) > 2:
        raise SystemExit(f"{name} is {im.size}, expected {expect}")
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
            "lw": 0.9,
            "mutation_scale": 8,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=3,
    )


def _box(ax, x, y, w, h, title, sub="", *, face=PAPER, edge=INK, lw=0.9, title_pt=8.0, sub_pt=6.2, tc=INK, sc=MUTED):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.01,rounding_size=0.04",
            facecolor=face,
            edgecolor=edge,
            linewidth=lw,
            zorder=2,
        )
    )
    cx = x + w / 2
    if sub:
        ax.text(cx, y + h * 0.64, title, ha="center", va="center", fontsize=title_pt, fontweight="bold", color=tc, zorder=4)
        ax.text(cx, y + h * 0.30, sub, ha="center", va="center", fontsize=sub_pt, color=sc, zorder=4)
    else:
        ax.text(cx, y + h / 2, title, ha="center", va="center", fontsize=title_pt, fontweight="bold", color=tc, zorder=4)


def slot_gap() -> Path:
    w, h = SLOT_IN["gap"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes((0.20, 0.10, 0.78, 0.72))
    rows = ["Private ask", "Routes to a TA", "Professor stamp", "AI quotes only stamps"]
    cols = ["Inbox / email", "Piazza / Ed", "Campus chatbot", "OfficeHours"]
    data = [
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
        [0, 0, 0, 1],
    ]
    ax.imshow(data, cmap=ListedColormap(["#F3F6F4", GREEN]), vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(cols)), cols, fontsize=7.4)
    ax.set_yticks(range(len(rows)), rows, fontsize=7.4)
    ax.tick_params(length=0, pad=2)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([x - 0.5 for x in range(len(cols) + 1)], minor=True)
    ax.set_yticks([y - 0.5 for y in range(len(rows) + 1)], minor=True)
    ax.grid(which="minor", color="white", linestyle="-", linewidth=2)
    ax.tick_params(which="minor", length=0)
    for i, row in enumerate(data):
        for j, val in enumerate(row):
            ax.text(j, i, "yes" if val else "—", ha="center", va="center", fontsize=8, color="white" if val else SLATE, fontweight="medium")
    fig.text(0.02, 0.90, "Who already does the job  ·  green = present  ·  not a measured score", fontsize=8.2, fontweight="bold", color=INK)
    return _save(fig, "SLOT_gap.png", SLOT_IN["gap"])


def slot_architecture() -> Path:
    fig, ax = _blank("arch")
    w, h = SLOT_IN["arch"]
    ax.text(0.10, h - 0.16, "One product. Three seats. Canvas is the campus door.", fontsize=9.2, fontweight="bold", color=INK, va="center")

    top_y, top_h = 1.28, 0.78
    side, gap = 0.10, 0.14
    top_w = (w - 2 * side - 2 * gap) / 3
    xs = [side + i * (top_w + gap) for i in range(3)]
    _box(ax, xs[0], top_y, top_w, top_h, "One web app", "Student  ·  TA  ·  Professor", title_pt=8.4, sub_pt=6.4)
    _box(ax, xs[1], top_y, top_w, top_h, "Campus API", "Queue  ·  roles  ·  stamps", face=GREEN_SOFT, title_pt=8.4, sub_pt=6.4)
    _box(ax, xs[2], top_y, top_w, top_h, "Canvas", "Login  ·  course  ·  modules", face="#F7F7F5", edge=SLATE, title_pt=8.4, sub_pt=6.4)
    mid_y = top_y + top_h / 2
    _arrow(ax, xs[0] + top_w, mid_y, xs[1], mid_y)
    _arrow(ax, xs[1] + top_w, mid_y, xs[2], mid_y)

    bot_y, bot_h = 0.10, 0.92
    bot_gap = 0.08
    bot_w = (w - 2 * side - 4 * bot_gap) / 5
    bxs = [side + i * (bot_w + bot_gap) for i in range(5)]
    parts = [
        ("Ask Triage", "label + TA + hint"),
        ("Help Coach", "draft on TA screen"),
        ("Stamp", "professor gate"),
        ("Study Agent", "quote or refuse"),
        ("Rooms", "named classmates"),
    ]
    for i, (title, sub) in enumerate(parts):
        _box(ax, bxs[i], bot_y, bot_w, bot_h, title, sub, face=GREEN_SOFT if i < 3 else PAPER, edge=GREEN if i < 3 else INK, title_pt=7.2, sub_pt=5.8)
        if i < 4:
            _arrow(ax, bxs[i] + bot_w, bot_y + bot_h / 2, bxs[i + 1], bot_y + bot_h / 2)
    _arrow(ax, xs[1] + top_w / 2, top_y, xs[1] + top_w / 2, bot_y + bot_h + 0.04)
    return _save(fig, "SLOT_architecture.png", SLOT_IN["arch"])


def slot_pipeline() -> Path:
    fig, ax = _blank("pipe")
    w, h = SLOT_IN["pipe"]
    ax.text(0.10, h - 0.16, "The loop a recruiter can walk in ten seconds", fontsize=9.2, fontweight="bold", va="center")
    steps = [
        (GREEN, "1  Quiet ask", "Name hidden.\nTicket tracked."),
        (TEAL, "2  Ask Triage", "Category, TA,\ncopied hint."),
        ("#B45309", "3  Help Coach", "Draft stays on\nthe TA screen."),
        (AMBER, "4  Stamp", "Professor marks\nquotable text."),
        (GREEN, "5  Study Agent", "Quote the stamp\nor refuse."),
    ]
    margin, gap = 0.10, 0.10
    bw = (w - 2 * margin - gap * 4) / 5
    by, bh = 0.18, 1.52
    for i, (color, title, body) in enumerate(steps):
        x = margin + i * (bw + gap)
        _box(ax, x, by, bw, bh, "", face=color, edge=color)
        ax.text(x + 0.08, by + bh - 0.22, title, fontsize=7.6, fontweight="bold", color="white", va="center", zorder=4)
        ax.text(x + 0.08, by + 0.62, body, fontsize=6.6, color="white", va="center", zorder=4, linespacing=1.25)
        if i < 4:
            _arrow(ax, x + bw, by + bh / 2, x + bw + gap, by + bh / 2)
    return _save(fig, "SLOT_pipeline.png", SLOT_IN["pipe"])


def slot_roadmap() -> Path:
    w, h = SLOT_IN["road"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes((0.03, 0.22, 0.94, 0.70))
    events = [
        (0.55, "1  Roles", True),
        (1.70, "2  Stamp gate", True),
        (2.85, "3  Rooms + demo", True),
        (4.05, "4  Live Canvas", False),
        (5.20, "5  Hosted DB", False),
    ]
    ax.axvspan(3.45, 5.70, color="#F4F6F5", zorder=0)
    ax.plot([0.30, 5.50], [0, 0], color=INK, lw=1.0, zorder=1)
    for x, label, done in events:
        ax.plot([x], [0], marker="o", ms=6, color=GREEN if done else PAPER, markeredgecolor=GREEN, markeredgewidth=1.2, zorder=3)
        ax.text(x, 0.62, label, ha="center", va="bottom", fontsize=7.0, fontweight="bold", color=INK)
    ax.set_xlim(0.10, 5.80)
    ax.set_ylim(-1.2, 1.45)
    ax.set_yticks([])
    ax.set_xticks([0.55, 3.15, 5.20])
    ax.set_xticklabels(["built", "waits on IT", "deadline"], fontsize=6.4, color=MUTED)
    ax.tick_params(axis="x", length=0, pad=1)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return _save(fig, "SLOT_roadmap.png", SLOT_IN["road"])


def slot_evaluation() -> Path:
    clf = json.loads((REPORTS / "classifier_evaluation.json").read_text())
    matcher = json.loads((REPORTS / "matcher_evaluation.json").read_text())
    gold = json.loads((REPORTS / "gold_label_evaluation.json").read_text())
    w, h = SLOT_IN["eval"]
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    fig.text(0.03, 0.93, "Laboratory checks  ·  not a live AUI section", fontsize=9.0, fontweight="bold", va="center")
    ax = fig.add_axes((0.10, 0.22, 0.84, 0.62))
    labels = ["Analyzer\nCV", "Matcher\nsilver", "Analyzer\ngold", "Matcher\ngold"]
    acc = [clf["accuracy"] * 100, matcher["metrics"]["accuracy"] * 100, gold["analyzer"]["accuracy"] * 100, gold["matcher"]["accuracy"] * 100]
    f1 = [clf["macro_f1"] * 100, matcher["metrics"]["macro_f1"] * 100, gold["analyzer"]["macro_f1"] * 100, gold["matcher"]["macro_f1"] * 100]
    x = np.arange(len(labels))
    width = 0.36
    ax.bar(x - width / 2, acc, width, color=[GREEN, GREEN, SLATE, SLATE], label="Accuracy")
    ax.bar(x + width / 2, f1, width, color=[TEAL, TEAL, "#B45309", "#B45309"], label="Macro-F1")
    ax.set_xticks(x, labels, fontsize=7.4)
    ax.set_ylim(0, 110)
    ax.set_ylabel("%", fontsize=7.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    ax.tick_params(axis="y", labelsize=7)
    fig.text(
        0.03,
        0.05,
        f"Green = development holdout (Analyzer n={clf['dataset_size']}, Matcher n={matcher['metrics']['n']}).  "
        f"Gray-gold = curated gold n={gold['analyzer']['n']}, not campus TA labels.",
        fontsize=6.2,
        color=MUTED,
    )
    return _save(fig, "SLOT_evaluation.png", SLOT_IN["eval"])


def fig_qr() -> Path:
    FIGS.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=14, border=2)
    qr.add_data(REPO)
    qr.make(fit=True)
    img = qr.make_image(fill_color=GREEN, back_color=PAPER).convert("RGB")
    path = FIGS / "qr.png"
    img.save(path)
    return path


def build_all() -> dict[str, Path]:
    _fonts()
    paths = {
        "gap": slot_gap(),
        "arch": slot_architecture(),
        "road": slot_roadmap(),
        "pipe": slot_pipeline(),
        "eval": slot_evaluation(),
        "qr": fig_qr(),
    }
    for key, path in paths.items():
        im = Image.open(path)
        extra = f"  ({SLOT_IN[key][0]:.2f}in x {SLOT_IN[key][1]:.2f}in)" if key in SLOT_IN else ""
        print(f"{path.name:24} {im.size[0]}×{im.size[1]}{extra}")
    return paths


if __name__ == "__main__":
    build_all()
