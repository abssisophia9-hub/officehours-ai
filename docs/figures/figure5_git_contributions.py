"""Commit counts from the shortlog cited in Section 6.1.

The counts are git shortlog -sn on the 362-commit tree named in that section
(origin/main at the time the section was written): Cursor Agent 285, SOPHIA 46,
cursor[bot] 29, Sophia 1, abssisophia9-hub 1. They are not a fresh count of the
documentation commits on this branch.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "figure5_git_contributions.png"

COUNTS = [
    ("Cursor Agent", 285),
    ("SOPHIA", 46),
    ("cursor[bot]", 29),
    ("Sophia", 1),
    ("abssisophia9-hub", 1),
]


def main() -> None:
    if sum(count for _, count in COUNTS) != 362:
        raise SystemExit("counts must sum to the 362 commits named in Section 6.1")
    labels = [name for name, _ in COUNTS][::-1]
    values = [count for _, count in COUNTS][::-1]
    fig, ax = plt.subplots(figsize=(8.4, 3.8), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    bars = ax.barh(labels, values, color="#5C5C5C", height=0.62, zorder=2)
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_width() + 4,
            bar.get_y() + bar.get_height() / 2,
            str(value),
            va="center",
            ha="left",
            color="#000000",
            fontsize=10,
        )
    ax.set_xlim(0, 360)
    ax.set_xlabel("Commits", fontsize=10, color="#000000")
    ax.set_title(
        "git shortlog -sn, 362 commits\nSection 6.1 tree",
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


if __name__ == "__main__":
    main()
