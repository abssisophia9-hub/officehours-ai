#!/usr/bin/env python3
"""Slot-native SSE poster figures.

Each PNG is sized to the official dashed cell *content* area
(cell height minus 0.125in top+bottom margins, width minus 0.139in
side margins) so Word/LibreOffice cannot clip or squash labels.

Official cells (hRule=exact):
  OPTIONAL VISUAL                         1.150in
  PROPOSED DESIGN FIGURE                  2.550in
  PLANNED WORK / REQUIREMENTS VISUAL      0.700in
  PROPOSED PROCESS / PIPELINE             2.292in
  PLANNED EVALUATION FRAMEWORK            2.333in
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
FIGS = HERE.parent / "poster_figures"
DPI = 240

# Display inches written into Word (must match these pixel sizes).
# Stay a few hundredths inside the cell content box.
SLOT_IN = {
    "gap": (6.20, 0.85),
    "arch": (6.20, 1.70),
    "road": (6.20, 0.48),
    "pipe": (6.20, 1.70),
    "eval": (6.20, 1.70),
}

GREEN = "#006633"
GREEN_DK = "#004B2B"
INK = "#12201B"
MUTED = "#2A3531"
# Match the template dashed-cell fill so the PNG has no white halo.
CELL = "#F1F3F2"
GOLD = "#FFE28A"
BLUE = "#C9DFFF"
MINT = "#B9EBCB"
PEACH = "#FFC9A8"
SAND = "#E4EBE7"
WHITE = "#FFFFFF"


def px(inches: float) -> int:
    return max(1, int(round(inches * DPI)))


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


def tw(draw: ImageDraw.ImageDraw, s: str, f) -> tuple[int, int]:
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def fit_font(draw, text: str, max_w: int, start: int, min_size: int = 14, bold: bool = True):
    for size in range(start, min_size - 1, -1):
        f = font(size, bold)
        if tw(draw, text, f)[0] <= max_w:
            return f
    return font(min_size, bold)


def rounded(draw, box, fill, outline=GREEN_DK, radius=16, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_lines(draw, box, lines, sizes, fills, bold=(True, False, False)):
    x0, y0, x1, y1 = box
    inner_w = x1 - x0 - 16
    fonts = []
    heights = []
    for i, line in enumerate(lines):
        is_bold = bold[i] if i < len(bold) else False
        f = fit_font(draw, line, inner_w, sizes[i] if i < len(sizes) else 18, 12, is_bold)
        fonts.append(f)
        heights.append(tw(draw, line, f)[1])
    gap = 6
    total = sum(heights) + gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        ww, hh = tw(draw, line, fonts[i])
        color = fills[i] if i < len(fills) else INK
        draw.text((x0 + (x1 - x0 - ww) // 2, y), line, fill=color, font=fonts[i])
        y += hh + gap


def arrow_h(draw, x0, y, x1, color=GREEN_DK, width=5):
    if x1 - x0 < 12:
        return
    draw.line([(x0, y), (x1 - 10, y)], fill=color, width=width)
    draw.polygon([(x1, y), (x1 - 12, y - 7), (x1 - 12, y + 7)], fill=color)


def arrow_v(draw, x, y0, y1, color=GREEN_DK, width=5):
    draw.line([(x, y0), (x, y1 - 10)], fill=color, width=width)
    draw.polygon([(x, y1), (x - 7, y1 - 12), (x + 7, y1 - 12)], fill=color)


def save(img: Image.Image, name: str) -> Path:
    HERE.mkdir(parents=True, exist_ok=True)
    FIGS.mkdir(parents=True, exist_ok=True)
    path = HERE / name
    img.save(path, "PNG")
    img.save(FIGS / name, "PNG")
    return path


def canvas(key: str) -> tuple[Image.Image, ImageDraw.ImageDraw, int, int]:
    wi, hi = SLOT_IN[key]
    w, h = px(wi), px(hi)
    img = Image.new("RGB", (w, h), CELL)
    return img, ImageDraw.Draw(img), w, h


def slot_gap() -> Path:
    """OPTIONAL VISUAL — existing vs proposed (gap / feature comparison)."""
    img, d, w, h = canvas("gap")
    headers = ["Capability", "Today on campus", "OfficeHours AI"]
    rows = [
        ("Routing", "LMS inbox / Piazza", "Ask Triage (MiniLM)"),
        ("TA staffing", "No dual-TA match", "Matcher + queue"),
        ("Student AI", "Open chatbot / FAQ", "Stamped Study Agent"),
    ]
    pad = 8
    cols = [int(w * 0.20), int(w * 0.38), int(w * 0.42) - 2]
    row_h = (h - pad * 2) // 4
    y = pad
    x = pad
    for i, head in enumerate(headers):
        fill = GREEN if i == 2 else GREEN_DK if i == 0 else SAND
        color = WHITE
        d.rectangle((x, y, x + cols[i], y + row_h), fill=fill)
        f = fit_font(d, head, cols[i] - 16, 26, 14, True)
        ww, hh = tw(d, head, f)
        d.text((x + (cols[i] - ww) // 2, y + (row_h - hh) // 2), head, fill=color, font=f)
        x += cols[i]
    y += row_h
    for r, row in enumerate(rows):
        x = pad
        for i, cell in enumerate(row):
            bg = MINT if i == 2 else (WHITE if r % 2 == 0 else SAND)
            d.rectangle((x, y, x + cols[i], y + row_h), fill=bg, outline="#C5CDC9")
            f = fit_font(d, cell, cols[i] - 16, 24 if i else 22, 13, True)
            ww, hh = tw(d, cell, f)
            d.text((x + (cols[i] - ww) // 2, y + (row_h - hh) // 2), cell, fill=INK, font=f)
            x += cols[i]
        y += row_h
    return save(img, "SLOT_gap.png")


def slot_architecture() -> Path:
    """PROPOSED DESIGN FIGURE — conceptual architecture."""
    img, d, w, h = canvas("arch")
    d.rectangle((0, 0, w, 44), fill=GREEN)
    title = "Proposed architecture  ·  one app  ·  local Ask Triage  ·  Canvas as source of truth"
    f = fit_font(d, title, w - 24, 22, 14, True)
    ww, hh = tw(d, title, f)
    d.text(((w - ww) // 2, (44 - hh) // 2), title, fill=WHITE, font=f)

    top = [
        (GOLD, ["App :5180", "Student · TA · Professor", "React / Vite / Tailwind"]),
        (BLUE, ["FastAPI :8000", "REST · WebSocket · SQL", "SQLite now → Postgres"]),
        (MINT, ["Canvas LTI 1.3", "Launch + REST modules", "Materials → KB  ·  no scrape"]),
    ]
    bot = [
        (GOLD, ["Analyzer", "MiniLM + LogReg", "category · urgency · ETA"]),
        (BLUE, ["Matcher", "Primary + alt TA", "queue-wait blend"]),
        (MINT, ["Synthesizer", "Approved-KB RAG", "hint or seek-help"]),
        (PEACH, ["Professor stamp", "Only stamped KB", "reaches Study Agent"]),
    ]

    gap = 16
    top_y0 = 52
    top_y1 = 52 + int((h - 64) * 0.46)
    bot_y0 = top_y1 + 36
    bot_y1 = h - 10
    n = len(top)
    bw = (w - 20 - gap * (n - 1)) // n
    xs = []
    for i, (fill, lines) in enumerate(top):
        x0 = 10 + i * (bw + gap)
        x1 = x0 + bw
        xs.append((x0, x1))
        rounded(d, (x0, top_y0, x1, top_y1), fill, radius=18)
        center_lines(d, (x0, top_y0, x1, top_y1), lines, (28, 18, 16), (INK, MUTED, MUTED), (True, False, False))
        if i < n - 1:
            arrow_h(d, x1 + 1, (top_y0 + top_y1) // 2, x1 + gap - 1)

    # drop from FastAPI into Ask Triage row
    mid_x = (xs[1][0] + xs[1][1]) // 2
    arrow_v(d, mid_x, top_y1 + 2, bot_y0 - 4)

    n = len(bot)
    bw = (w - 20 - gap * (n - 1)) // n
    for i, (fill, lines) in enumerate(bot):
        x0 = 10 + i * (bw + gap)
        x1 = x0 + bw
        rounded(d, (x0, bot_y0, x1, bot_y1), fill, radius=18)
        center_lines(d, (x0, bot_y0, x1, bot_y1), lines, (26, 18, 16), (INK, MUTED, MUTED), (True, False, False))
        if i < n - 1:
            arrow_h(d, x1 + 1, (bot_y0 + bot_y1) // 2, x1 + gap - 1)
    return save(img, "SLOT_architecture.png")


def slot_pipeline() -> Path:
    """PROPOSED PROCESS / PIPELINE — inputs → processing → outputs."""
    img, d, w, h = canvas("pipe")
    d.rectangle((0, 0, w, 44), fill=GREEN)
    title = "Ask pipeline  ·  Input → local triage → TA desk → professor stamp → Study Agent"
    f = fit_font(d, title, w - 24, 22, 14, True)
    ww, hh = tw(d, title, f)
    d.text(((w - ww) // 2, (44 - hh) // 2), title, fill=WHITE, font=f)

    bands = [
        (0, 2, "INPUT"),
        (2, 5, "PROCESS  (Ask Triage)"),
        (5, 7, "OUTPUT"),
    ]
    steps = [
        (GOLD, ["1  Ask", "Quiet or named", "help mode"]),
        (GOLD, ["2  Intake", "course-scoped", "auth + request"]),
        (BLUE, ["3  Analyzer", "MiniLM + LogReg", "category · urgency"]),
        (BLUE, ["4  Matcher", "dual-TA + wait", "primary / alt"]),
        (MINT, ["5  Synthesizer", "approved-KB RAG", "hint or seek-help"]),
        (PEACH, ["6  TA + stamp", "Help Coach · KB", "professor gate"]),
        (MINT, ["7  Study Agent", "stamped KB only", "/agent/ask"]),
    ]
    gap = 10
    n = len(steps)
    bw = (w - 16 - gap * (n - 1)) // n
    band_y0, band_y1 = 56, 92
    box_y0, box_y1 = 104, h - 12

    # band labels spanning groups
    starts = [10 + i * (bw + gap) for i in range(n)]
    ends = [s + bw for s in starts]
    band_fills = [SAND, BLUE, MINT]
    for (a, b, label), bf in zip(bands, band_fills):
        x0, x1 = starts[a], ends[b - 1]
        rounded(d, (x0, band_y0, x1, band_y1), bf, GREEN_DK, 10, 2)
        f = fit_font(d, label, x1 - x0 - 12, 20, 12, True)
        ww, hh = tw(d, label, f)
        d.text((x0 + (x1 - x0 - ww) // 2, band_y0 + (band_y1 - band_y0 - hh) // 2), label, fill=INK, font=f)

    for i, (fill, lines) in enumerate(steps):
        x0 = starts[i]
        x1 = ends[i]
        rounded(d, (x0, box_y0, x1, box_y1), fill, radius=16)
        center_lines(d, (x0, box_y0, x1, box_y1), lines, (22, 16, 15), (INK, MUTED, MUTED), (True, False, False))
        if i < n - 1:
            arrow_h(d, x1 + 1, (box_y0 + box_y1) // 2, x1 + gap - 1, width=4)
    return save(img, "SLOT_pipeline.png")


def slot_roadmap() -> Path:
    """PLANNED WORK / REQUIREMENTS VISUAL — 0.52in banner; labels must fill the height."""
    img, d, w, h = canvas("road")
    items = [
        (SAND, "1", "Roles + auth"),
        (SAND, "2", "TA / KB gate"),
        (SAND, "3", "Rooms + demo"),
        (GOLD, "4", "LTI live"),
        (GOLD, "5", "Postgres"),
    ]
    gap = 10
    n = len(items)
    pad = 4
    bw = (w - pad * 2 - gap * (n - 1)) // n
    for i, (fill, num, label) in enumerate(items):
        x0 = pad + i * (bw + gap)
        x1 = x0 + bw
        rounded(d, (x0, 2, x1, h - 2), fill, radius=14, width=3)
        # number badge
        cy = h // 2
        br = max(16, h // 2 - 8)
        bx = x0 + 10 + br
        d.ellipse((bx - br, cy - br, bx + br, cy + br), fill=GREEN)
        nf = fit_font(d, num, br * 2 - 6, br, 14, True)
        ww, hh = tw(d, num, nf)
        d.text((bx - ww // 2, cy - hh // 2), num, fill=WHITE, font=nf)
        # label uses remaining width — this is the whole 0.52in cell, so type is large
        lx0 = bx + br + 8
        lf = fit_font(d, label, x1 - lx0 - 8, h - 18, 16, True)
        ww, hh = tw(d, label, lf)
        d.text((lx0, (h - hh) // 2), label, fill=INK, font=lf)
        if i < n - 1:
            arrow_h(d, x1 + 1, h // 2, x1 + gap - 1, width=4)
    return save(img, "SLOT_roadmap.png")


def slot_evaluation() -> Path:
    """PLANNED EVALUATION FRAMEWORK — test matrix + pass rules."""
    img, d, w, h = canvas("eval")
    d.rectangle((0, 0, w, 44), fill=GREEN)
    title = "Evaluation framework  ·  planned evidence only  ·  no unverified campus claims"
    f = fit_font(d, title, w - 24, 22, 14, True)
    ww, hh = tw(d, title, f)
    d.text(((w - ww) // 2, (44 - hh) // 2), title, fill=WHITE, font=f)

    headers = ["Method", "Evidence we will collect", "Pass / acceptance rule"]
    rows = [
        ("pytest + CI", "API, auth, KB-gate tests", "CI green on demo path"),
        ("Triage holdouts", "Category / routing quality", "Cite metrics carefully"),
        ("Gold-label TA lab", "Human labels on real asks", "Lab protocol in docs/"),
        ("Role walkthroughs", "Student · TA · professor", "Each role completes tasks"),
        ("Live Canvas check", "LTI launch + module sync", "One AUI test course"),
    ]
    pad = 10
    cols = [int(w * 0.24), int(w * 0.40), int(w * 0.36) - 4]
    table_h = h - 44 - pad - 6
    row_h = table_h // 6
    y = 50
    x = pad
    for i, head in enumerate(headers):
        d.rectangle((x, y, x + cols[i], y + row_h), fill=GREEN_DK)
        f = fit_font(d, head, cols[i] - 14, 22, 13, True)
        ww, hh = tw(d, head, f)
        d.text((x + (cols[i] - ww) // 2, y + (row_h - hh) // 2), head, fill=WHITE, font=f)
        x += cols[i]
    y += row_h
    zebra = [WHITE, SAND]
    for r, row in enumerate(rows):
        x = pad
        for i, cell in enumerate(row):
            bg = MINT if i == 2 else zebra[r % 2]
            d.rectangle((x, y, x + cols[i], y + row_h), fill=bg, outline="#C5CDC9")
            f = fit_font(d, cell, cols[i] - 14, 22, 13, True if i == 0 else False)
            ww, hh = tw(d, cell, f)
            d.text((x + (cols[i] - ww) // 2, y + (row_h - hh) // 2), cell, fill=INK, font=f)
            x += cols[i]
        y += row_h
    return save(img, "SLOT_evaluation.png")


def build_all() -> dict[str, Path]:
    paths = {
        "gap": slot_gap(),
        "arch": slot_architecture(),
        "road": slot_roadmap(),
        "pipe": slot_pipeline(),
        "eval": slot_evaluation(),
    }
    for key, p in paths.items():
        im = Image.open(p)
        wi, hi = SLOT_IN[key]
        print(f"{p.name:24} {im.size}  ({wi:.2f}in x {hi:.2f}in @ {DPI}dpi)")
    return paths


if __name__ == "__main__":
    build_all()
