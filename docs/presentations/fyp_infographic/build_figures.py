#!/usr/bin/env python3
"""Figures for the 24×36 OfficeHours AI infographic poster."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib import font_manager
from PIL import Image
import qrcode

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
REPO = "https://github.com/abssisophia9-hub/officehours-ai"

FOREST = "#07552F"
INK = "#1C1917"
CREAM = "#F6F3EC"
SAGE = "#D7E8DC"
AMBER = "#9A3412"
TEAL = "#0F766E"
GOLD = "#B45309"
WHITE = "#FFFFFF"
MUTED = "#57534E"
PALE = "#E8F2EB"

INTER = Path("/usr/share/fonts/truetype/macos")
for name in ("Inter-Regular.ttf", "Inter-Medium.ttf", "Inter-SemiBold.ttf", "Inter-Bold.ttf"):
    font_manager.fontManager.addfont(str(INTER / name))
plt.rcParams.update({"font.family": "Inter", "text.color": INK})


def _save(fig: plt.Figure, name: str, pad: float = 0.04) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    fig.savefig(path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor(), pad_inches=pad)
    plt.close(fig)
    return path


def _card(ax, x, y, w, h, fc=WHITE, ec=FOREST, lw=1.8):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.12",
            facecolor=fc,
            edgecolor=ec,
            linewidth=lw,
        )
    )


def fig_problem() -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(15.4, 6.1), gridspec_kw={"wspace": 0.10})
    fig.patch.set_facecolor(WHITE)

    ax = axes[0]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Staff  ·  same stuck point, five channels", loc="left", fontsize=18, fontweight="bold", color=FOREST, pad=6)
    labels = [
        "Email — red-black rotations?",
        "Canvas inbox — rotations?",
        "Walk-in — rotations again",
        "Forum — still rotations",
        "After hours — same stuck point",
    ]
    for i, label in enumerate(labels):
        y = 8.15 - i * 1.52
        _card(ax, 0.35, y, 9.3, 1.28, fc=PALE if i % 2 == 0 else WHITE)
        ax.text(0.7, y + 0.64, f"{i+1}", fontsize=16, fontweight="bold", color=FOREST, va="center")
        ax.text(1.35, y + 0.64, label, fontsize=15, va="center", color=INK)

    ax = axes[1]
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    ax.set_title("Students  ·  how much a name is required", loc="left", fontsize=18, fontweight="bold", color=AMBER, pad=6)
    channels = [
        ("Named office hours", 0.94, AMBER),
        ("Public forum", 0.80, AMBER),
        ("Direct email", 0.66, GOLD),
        ("Quiet receipt  ·  this product", 0.18, FOREST),
    ]
    for i, (label, barrier, color) in enumerate(channels):
        y = 7.55 - i * 1.75
        ax.text(0.35, y + 1.05, label, fontsize=15, color=INK, fontweight="medium")
        _card(ax, 0.35, y, 9.3, 0.72, fc=SAGE, ec="none", lw=0)
        ax.add_patch(
            mpatches.FancyBboxPatch(
                (0.35, y),
                9.3 * barrier,
                0.72,
                boxstyle="round,pad=0.02,rounding_size=0.10",
                facecolor=color,
                edgecolor="none",
            )
        )
        ax.text(0.55, y + 0.36, f"{int(barrier*100)}%", fontsize=13, color=WHITE, va="center", fontweight="bold")
    ax.text(0.35, 0.35, "Shorter bar = less social exposure to ask for help.", fontsize=13, color=MUTED)
    return _save(fig, "problem.png")


def fig_architecture() -> Path:
    fig, ax = plt.subplots(figsize=(21.2, 8.4))
    ax.set_xlim(0, 21.2)
    ax.set_ylim(0, 8.4)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)

    layers = [
        (7.05, FOREST, WHITE, "Browser  ·  one React app :5180", "One login. Role is per course. Student, TA, and professor share the same URL."),
        (5.35, TEAL, WHITE, "API  ·  one FastAPI process :8000", "REST commands. WebSocket /ws for the live queue. SQLite in demo; Postgres when hosted."),
        (3.65, GOLD, WHITE, "Campus door  ·  Canvas LTI 1.3 + REST", "Launch carries course and role. Sync writes pending notes. IT still owes the live key and token."),
        (1.95, INK, WHITE, "Local tools  ·  not a hosted chatbot", "MiniLM vector → logistic .joblib class → cosine nearest note → fixed tables for wait and planner cards."),
    ]
    for y, fc, tc, title, body in layers:
        _card(ax, 0.2, y, 12.55, 1.55, fc=fc, ec=fc)
        ax.text(0.5, y + 1.05, title, fontsize=17, fontweight="bold", color=tc)
        ax.text(0.5, y + 0.45, body, fontsize=13.5, color=tc)

    modules = [
        (0.20, "Ask Triage", "Analyzer labels.\nMatcher names a TA.\nSynthesizer copies a hint.\nCluster if cosine ≥ 0.72."),
        (3.35, "Staff AI", "Help Coach on the TA screen.\nPlanner cards: group / FAQ / 1:1.\nProfessor stamp is the gate.\nStaff can override any label."),
        (6.50, "Student AI", "Study Agent quotes stamps only.\nRefuse below similarity 0.42.\nQuiet ask hides the name.\nRooms stay named classmates."),
        (9.65, "Out of the loop", "No campus ChatGPT.\nNo auto-publish FAQ.\nNo portal scrape.\nNo NFC kiosk."),
    ]
    for x, title, body in modules:
        _card(ax, x, 0.15, 3.0, 1.65, fc=PALE)
        ax.text(x + 0.16, 1.42, title, fontsize=14, fontweight="bold", color=FOREST)
        ax.text(x + 0.16, 0.95, body, fontsize=11.5, color=INK, va="top", linespacing=1.28)

    # right column: three seats
    _card(ax, 13.05, 0.15, 7.9, 8.05, fc=PALE, ec=FOREST)
    ax.text(13.35, 7.65, "Three seats, one desk", fontsize=18, fontweight="bold", color=FOREST)
    seats = [
        ("Student", "Quiet ask · Rooms · Study Agent", "Files a ticket. May hide a name. Reads only stamped answers."),
        ("TA", "Desk · claim · Help Coach", "Sees the triage. Drafts stay on this screen. Replies or books a group."),
        ("Professor", "Clusters · stamp · Canvas", "Approves the only text an agent may quote. Syncs the module list."),
    ]
    for i, (who, tools, body) in enumerate(seats):
        y = 5.35 - i * 2.35
        _card(ax, 13.35, y, 7.3, 2.15, fc=WHITE)
        ax.add_patch(mpatches.Circle((13.85, y + 1.55), 0.28, facecolor=FOREST, edgecolor="none"))
        ax.text(13.85, y + 1.55, str(i + 1), ha="center", va="center", color=WHITE, fontsize=14, fontweight="bold")
        ax.text(14.35, y + 1.55, who, fontsize=18, fontweight="bold", color=FOREST, va="center")
        ax.text(14.35, y + 1.08, tools, fontsize=13, color=TEAL, va="center")
        ax.text(13.55, y + 0.35, body, fontsize=13, color=INK)
    return _save(fig, "architecture.png")


def fig_loop() -> Path:
    fig, ax = plt.subplots(figsize=(21.2, 4.05))
    ax.set_xlim(0, 21.2)
    ax.set_ylim(0, 4.05)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)
    steps = [
        (FOREST, "1  Quiet ask", "Identity stripped\non the status page."),
        (TEAL, "2  Ask Triage", "Category, TA,\ncopied past hint."),
        (GOLD, "3  Help Coach", "Draft never leaves\nthe TA screen."),
        (AMBER, "4  Stamp", "Professor marks the\nonly quotable text."),
        (FOREST, "5  Study Agent", "Quote the stamp\nor refuse < 0.42."),
    ]
    w, h = 3.55, 3.35
    x0 = 0.25
    for i, (color, title, body) in enumerate(steps):
        x = x0 + i * 4.2
        _card(ax, x, 0.28, w, h, fc=color, ec=color)
        ax.text(x + 0.22, 2.85, title, fontsize=17, fontweight="bold", color=WHITE)
        ax.text(x + 0.22, 1.55, body, fontsize=15, color=WHITE, linespacing=1.4)
        if i < 4:
            ax.annotate(
                "",
                xy=(x + w + 0.48, 1.95),
                xytext=(x + w + 0.08, 1.95),
                arrowprops=dict(arrowstyle="->", color=FOREST, lw=2.4),
            )
    return _save(fig, "loop.png")


def fig_eval() -> Path:
    fig, ax = plt.subplots(figsize=(13.6, 6.2))
    fig.patch.set_facecolor(WHITE)
    ax.set_facecolor(WHITE)
    labels = ["Analyzer\nCV  n=156", "Matcher\nsilver  n=32", "Analyzer\ngold  n=80", "Matcher\ngold  n=80"]
    acc = [84.6, 87.5, 75.0, 79.0]
    f1 = [84.6, 76.3, 66.2, 77.7]
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, acc, w, color=[FOREST, FOREST, MUTED, MUTED], label="Accuracy  %")
    ax.bar(x + w / 2, f1, w, color=[TEAL, TEAL, GOLD, GOLD], label="Macro-F1  %")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=13)
    ax.set_ylim(0, 112)
    ax.set_ylabel("%", fontsize=13)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="y", labelsize=12)
    ax.legend(frameon=False, fontsize=12, loc="upper right")
    ax.set_title("Laboratory scores  ·  not live AUI section quality", fontsize=16, fontweight="bold", color=FOREST, loc="left", pad=8)
    for i, (a, f) in enumerate(zip(acc, f1)):
        ax.text(i - w / 2, a + 1.6, f"{a:.1f}", ha="center", fontsize=11, color=INK)
        ax.text(i + w / 2, f + 1.6, f"{f:.1f}", ha="center", fontsize=11, color=INK)
    ax.text(
        0.0,
        -0.26,
        "Green = development CV / silver.  Gray-gold = curated gold n=80.  Do not cite as campus human_gold.",
        transform=ax.transAxes,
        fontsize=12,
        color=MUTED,
    )
    fig.tight_layout()
    return _save(fig, "eval.png")


def fig_kpis() -> Path:
    fig, ax = plt.subplots(figsize=(21.2, 2.15))
    ax.set_xlim(0, 21.2)
    ax.set_ylim(0, 2.15)
    ax.axis("off")
    fig.patch.set_facecolor(WHITE)
    kpis = [
        ("84.6%", "Analyzer accuracy", "5-fold CV  ·  n=156"),
        ("75%", "Analyzer on gold", "curated  ·  n=80"),
        ("≥ 0.72", "Cluster threshold", "MiniLM cosine"),
        ("< 0.42", "Study Agent refuse", "no weak quote"),
    ]
    for i, (n, title, sub) in enumerate(kpis):
        x = 0.2 + i * 5.25
        _card(ax, x, 0.12, 5.0, 1.9, fc=PALE)
        ax.text(x + 0.22, 1.28, n, fontsize=32, fontweight="bold", color=FOREST)
        ax.text(x + 0.22, 0.72, title, fontsize=15, fontweight="bold", color=INK)
        ax.text(x + 0.22, 0.36, sub, fontsize=13, color=MUTED)
    return _save(fig, "kpis.png")


def fig_qr() -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=16, border=2)
    qr.add_data(REPO)
    qr.make(fit=True)
    img = qr.make_image(fill_color=FOREST, back_color=WHITE).convert("RGB")
    path = OUT / "qr.png"
    img.save(path)
    return path


def main() -> None:
    paths = [fig_problem(), fig_architecture(), fig_loop(), fig_eval(), fig_kpis(), fig_qr()]
    for p in paths:
        im = Image.open(p)
        print(f"{p.name:18} {im.size[0]}×{im.size[1]}")


if __name__ == "__main__":
    main()
