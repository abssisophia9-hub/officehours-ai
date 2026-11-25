"""Cumulative added lines for Cursor Agent and manual commits.

Reads git log --numstat on HEAD for backend/app/ai/, backend/tests/,
scripts/, and frontend/officehours-app/. Manual merges SOPHIA, Sophia,
and abssisophia9-hub. cursor[bot] is excluded. Binary numstat rows are
skipped. The endpoints are the Table 11 totals: 56,395 and 3,658.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "figure6_collaboration_timeline.png"
PATHS = [
    "backend/app/ai",
    "backend/tests",
    "scripts",
    "frontend/officehours-app",
]
MANUAL_AUTHORS = {"SOPHIA", "Sophia", "abssisophia9-hub"}
NAVY = "#1B365D"
TEAL = "#008080"
AGENT_TOTAL = 56395
MANUAL_TOTAL = 3658


def commits():
    log = subprocess.check_output(
        [
            "git",
            "log",
            "--reverse",
            "--pretty=format:---%n%H%x09%aI%x09%an",
            "--numstat",
            "--",
            *PATHS,
        ],
        cwd=ROOT,
        text=True,
    )
    rows = []
    for block in log.split("---\n"):
        block = block.strip("\n")
        if not block.strip():
            continue
        lines = block.splitlines()
        sha, when, author = lines[0].split("\t")
        added = 0
        for line in lines[1:]:
            parts = line.split("\t")
            if len(parts) < 3 or not parts[0].isdigit():
                continue
            added += int(parts[0])
        moment = datetime.fromisoformat(when).astimezone(timezone.utc)
        rows.append((moment, author, added, sha))
    rows.sort(key=lambda row: (row[0], row[3]))
    return rows


def cumulative(rows):
    agent = manual = 0
    dates, agent_line, manual_line, manual_marks = [], [], [], []
    for moment, author, added, _sha in rows:
        if author == "cursor[bot]":
            continue
        if author == "Cursor Agent":
            agent += added
            manual_commit = False
        elif author in MANUAL_AUTHORS:
            manual += added
            manual_commit = True
        else:
            continue
        dates.append(moment)
        agent_line.append(agent)
        manual_line.append(manual)
        manual_marks.append(manual_commit)
    return dates, agent_line, manual_line, manual_marks


def main() -> None:
    dates, agent_line, manual_line, manual_marks = cumulative(commits())
    if not dates or agent_line[-1] != AGENT_TOTAL or manual_line[-1] != MANUAL_TOTAL:
        raise SystemExit(
            f"endpoints {agent_line[-1] if agent_line else None} and "
            f"{manual_line[-1] if manual_line else None} "
            f"do not match {AGENT_TOTAL} and {MANUAL_TOTAL}"
        )

    fig, ax = plt.subplots(figsize=(8.8, 4.8), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax2 = ax.twinx()

    ax.plot(dates, agent_line, color=NAVY, linewidth=2.2, solid_capstyle="round", zorder=3)
    mark_at = [index for index, marked in enumerate(manual_marks) if marked]
    ax2.plot(
        dates,
        manual_line,
        color=TEAL,
        linewidth=2.2,
        marker="o",
        markersize=4,
        markevery=mark_at,
        zorder=4,
    )

    span = dates[-1] - dates[0]
    ax.set_xlim(dates[0], dates[-1] + span * 0.16)
    ax.set_ylim(0, AGENT_TOTAL * 1.12)
    ax2.set_ylim(0, MANUAL_TOTAL * 1.18)

    ax.annotate(
        "56,395 lines",
        xy=(dates[-1], agent_line[-1]),
        xytext=(8, 0),
        textcoords="offset points",
        color=NAVY,
        fontsize=9,
        va="center",
        ha="left",
        annotation_clip=False,
    )
    ax2.annotate(
        "3,658 lines",
        xy=(dates[-1], manual_line[-1]),
        xytext=(8, -12),
        textcoords="offset points",
        color=TEAL,
        fontsize=9,
        va="top",
        ha="left",
        annotation_clip=False,
    )

    ax.set_ylabel("Cursor Agent added lines", color=NAVY, fontsize=10)
    ax2.set_ylabel("Manual added lines", color=TEAL, fontsize=10)
    ax.tick_params(axis="y", colors=NAVY)
    ax2.tick_params(axis="y", colors=TEAL)
    ax.tick_params(axis="x", colors="#000000")
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{int(value):,}"))
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _pos: f"{int(value):,}"))
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    ax.grid(axis="y", color="#E6E6E6", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax2.grid(False)
    for spine in ("top",):
        ax.spines[spine].set_visible(False)
        ax2.spines[spine].set_visible(False)
    ax.spines["left"].set_color(NAVY)
    ax.spines["bottom"].set_color("#000000")
    ax2.spines["right"].set_color(TEAL)
    ax2.spines["left"].set_visible(False)
    ax2.spines["bottom"].set_visible(False)

    handles = [
        Line2D([0], [0], color=NAVY, linewidth=2.2, label="Cursor Agent"),
        Line2D(
            [0],
            [0],
            color=TEAL,
            linewidth=2.2,
            marker="o",
            markersize=4,
            label="Manual (My Commits)",
        ),
    ]
    legend = ax.legend(handles=handles, frameon=False, loc="upper left", fontsize=9)
    for text in legend.get_texts():
        text.set_color("#000000")

    fig.suptitle(
        "Iterative Development Cadence: Cursor Agent vs. Manual Commits",
        fontsize=12,
        color="#000000",
        x=0.01,
        ha="left",
    )
    ax.set_title(
        "Cumulative added lines across core modules over time "
        "(reflecting my ongoing testing, reviews, and refinements)",
        fontsize=8.5,
        color="#000000",
        loc="left",
        pad=8,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.90))
    fig.savefig(OUT, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")
    print(f"points {len(dates)} manual marks {len(mark_at)} span {dates[0].date()} {dates[-1].date()}")


if __name__ == "__main__":
    main()
