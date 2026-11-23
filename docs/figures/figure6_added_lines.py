"""Added lines on HEAD: Cursor Agent versus manual aliases.

Manual merges SOPHIA, Sophia, and abssisophia9-hub.
cursor[bot] added no lines on these four paths and is omitted.
The counts are git log --numstat on HEAD, summed by author.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent / "figure6_added_lines.png"

# Top-to-bottom matches the former Table 11 path order.
PATHS = [
    "backend/app/ai/",
    "backend/tests/",
    "scripts/",
    "frontend/officehours-app/",
]
CURSOR_AGENT = [5146, 11376, 3495, 36378]
MANUAL = [125, 1492, 2, 2039]


def main() -> None:
    if list(zip(CURSOR_AGENT, MANUAL)) != [
        (5146, 125),
        (11376, 1492),
        (3495, 2),
        (36378, 2039),
    ]:
        raise SystemExit("counts do not match the merged Table 11 figures")
    order = slice(None, None, -1)
    paths = PATHS[order]
    agent = CURSOR_AGENT[order]
    manual = MANUAL[order]
    y = np.arange(len(paths))
    height = 0.36

    fig, ax = plt.subplots(figsize=(8.6, 4.6), dpi=200)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    agent_bars = ax.barh(
        y + height / 2,
        agent,
        height=height,
        color="#4C4C4C",
        label="Cursor Agent",
        zorder=2,
    )
    manual_bars = ax.barh(
        y - height / 2,
        manual,
        height=height,
        color="#B0B0B0",
        label="Manual",
        zorder=2,
    )
    for bar in (*agent_bars, *manual_bars):
        value = int(bar.get_width())
        ax.text(
            value + 450,
            bar.get_y() + bar.get_height() / 2,
            f"{value:,}",
            va="center",
            ha="left",
            color="#000000",
            fontsize=9,
        )
    ax.set_yticks(y, paths, fontsize=10)
    ax.set_xlabel("Added lines", fontsize=10, color="#000000")
    ax.set_xlim(0, 48000)
    ax.set_title(
        "Added lines on HEAD: Cursor Agent vs. Manual",
        fontsize=12,
        color="#000000",
        loc="left",
        pad=10,
    )
    legend = ax.legend(frameon=False, loc="upper right", fontsize=10)
    for text in legend.get_texts():
        text.set_color("#000000")
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
