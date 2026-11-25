"""Post-use usability and trust chart (n = 7). Writes fig_post_use_survey.png."""

from pathlib import Path

import matplotlib

matplotlib.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
    "axes.facecolor": "white",
})
import matplotlib.pyplot as plt

# Displayed top to bottom. barh draws the first row at the bottom.
rows = list(reversed([
    ("Q3   Boundary & refusal", 4.43, 5.0, 6, 1, 0),
    ("Q5   Workflow value", 4.14, 5.0, 6, 0, 1),
    ("Q1   Answer clarity", 4.00, 4.0, 6, 0, 1),
    ("Q4   Quiet Ask", 4.00, 5.0, 5, 1, 1),
    ("Q2   Citation trust", 3.86, 4.0, 5, 1, 1),
]))

NAVY = "#1B365D"
TEAL = "#1F7A6B"
AGREE = "#1B4332"
NEUTRAL = "#D4CBBC"
DISAGREE = "#9C534A"
LINE = "#8A8478"
INK = "#1C1C1C"
MUTE = "#5E5A54"

fig, (ax_l, ax_r) = plt.subplots(
    1, 2, figsize=(12.2, 5.6), dpi=300,
    gridspec_kw={"width_ratios": [1.02, 1.22], "wspace": 0.38},
)

y = list(range(len(rows)))
labels = [row[0] for row in rows]
means = [row[1] for row in rows]
medians = [row[2] for row in rows]
height = 0.32

ax_l.barh([i + height / 2 for i in y], means, height=height, color=NAVY, label="Mean", zorder=3)
ax_l.barh([i - height / 2 for i in y], medians, height=height, color=TEAL, label="Median", zorder=3)
for i, (mean, median) in enumerate(zip(means, medians)):
    ax_l.text(mean - 0.1, i + height / 2, f"{mean:.2f}", va="center", ha="right", fontsize=8, color="white")
    ax_l.text(median - 0.1, i - height / 2, f"{median:.1f}", va="center", ha="right", fontsize=8, color="white")

ax_l.axvline(4.09, color=LINE, linestyle=(0, (2.4, 2.4)), linewidth=0.9, zorder=4)
ax_l.annotate(
    "Composite mean  4.09",
    xy=(4.09, 4.35),
    xytext=(4.09, 4.72),
    ha="center", va="bottom", fontsize=8, color=MUTE,
    arrowprops=dict(arrowstyle="-", color=LINE, lw=0.6),
)
ax_l.set_yticks(y)
ax_l.set_yticklabels(labels, fontsize=9, color=INK)
ax_l.set_xlim(0, 5.15)
ax_l.set_ylim(-0.7, 5.15)
ax_l.set_xlabel("Score out of 5.0", fontsize=9, color=INK)
ax_l.set_title("Mean and median", loc="left", fontsize=12, color=INK, pad=10)
ax_l.tick_params(axis="x", labelsize=8, colors=MUTE, length=0)
ax_l.tick_params(axis="y", length=0)
for spine in ("top", "right"):
    ax_l.spines[spine].set_visible(False)
ax_l.spines["left"].set_color("#E4E0D8")
ax_l.spines["bottom"].set_color("#E4E0D8")
ax_l.xaxis.grid(True, color="#F1EDE6", linewidth=0.7, zorder=0)
ax_l.set_axisbelow(True)
ax_l.legend(frameon=False, fontsize=8, loc="lower right", borderaxespad=0.2)

left = [0.0] * len(rows)
series = [
    ("Agree / strongly agree (4–5)", AGREE, [row[3] for row in rows], "white"),
    ("Neutral (3)", NEUTRAL, [row[4] for row in rows], INK),
    ("Disagree / strongly disagree (1–2)", DISAGREE, [row[5] for row in rows], "white"),
]
for name, color, counts, text_color in series:
    widths = [count / 7 * 100 for count in counts]
    ax_r.barh(y, widths, left=left, height=0.58, color=color, label=name, zorder=3)
    for i, (count, width, start) in enumerate(zip(counts, widths, left)):
        if count == 0:
            continue
        ax_r.text(
            start + width / 2, i, f"{count}\n{count / 7 * 100:.1f}%",
            ha="center", va="center", fontsize=7.2, color=text_color, linespacing=1.05,
        )
    left = [a + b for a, b in zip(left, widths)]

ax_r.set_yticks(y)
ax_r.set_yticklabels(labels, fontsize=9, color=INK)
ax_r.set_xlim(0, 100)
ax_r.set_ylim(-0.7, 5.15)
ax_r.set_xlabel("Share of responses (n = 7)", fontsize=9, color=INK)
ax_r.set_title("Likert breakdown", loc="left", fontsize=12, color=INK, pad=10)
ax_r.tick_params(axis="x", labelsize=8, colors=MUTE, length=0)
ax_r.tick_params(axis="y", length=0)
for spine in ("top", "right"):
    ax_r.spines[spine].set_visible(False)
ax_r.spines["left"].set_color("#E4E0D8")
ax_r.spines["bottom"].set_color("#E4E0D8")
ax_r.legend(
    frameon=False, fontsize=8, loc="upper center",
    bbox_to_anchor=(0.48, -0.16), ncol=1,
)

fig.suptitle("Post-use usability and trust", fontsize=15, color=INK, x=0.012, ha="left")
fig.text(
    0.012, 0.925,
    "n = 7   ·   Al Akhawayn University   ·   23 November 2026   ·   synthetic course session",
    fontsize=8.5, color=MUTE, ha="left",
)
fig.subplots_adjust(left=0.155, right=0.985, top=0.84, bottom=0.20)
out = Path(__file__).with_suffix(".png")
fig.savefig(out, dpi=300)
print(out)
