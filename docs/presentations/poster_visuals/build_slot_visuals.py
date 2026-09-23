#!/usr/bin/env python3
"""Slot-native poster visuals: designed for the SSE dashed boxes, large type, readable."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
# Pixel canvas = print inches * 220 dpi (type stays large when placed at ~6.2 x 1.2 in)
W = 1364  # 6.2 in * 220
H_TALL = 286  # 1.30 in
H_ROW = 242  # 1.10 in

GREEN = "#006633"
GREEN_DK = "#004B2B"
INK = "#14201C"
MUTED = "#2E3834"
LINE = "#5C6B65"
PAPER = "#FFFFFF"
GOLD = "#FFE9A8"
BLUE = "#D4E6FF"
MINT = "#C8EED9"
PEACH = "#FFD2B5"
SAND = "#EEF3F0"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


def tw(draw, s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def rounded(draw, box, fill, outline=GREEN_DK, radius=16, width=3):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center(draw, box, lines, sizes, colors=None):
    x0, y0, x1, y1 = box
    fonts = [font(sz, i == 0) for i, sz in enumerate(sizes)]
    heights = [tw(draw, line, fonts[i])[1] for i, line in enumerate(lines)]
    total = sum(heights) + 4 * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        color = (colors[i] if colors else (INK if i == 0 else MUTED))
        ww, hh = tw(draw, line, fonts[i])
        draw.text((x0 + (x1 - x0 - ww) // 2, y), line, fill=color, font=fonts[i])
        y += hh + 4


def arrow(draw, x0, y, x1):
    draw.line([(x0, y), (x1 - 14, y)], fill=GREEN_DK, width=5)
    draw.polygon([(x1, y), (x1 - 16, y - 9), (x1 - 16, y + 9)], fill=GREEN_DK)


def save(img: Image.Image, name: str) -> Path:
    path = HERE / name
    img.save(path, "PNG")
    (HERE.parent / "poster_figures" / name).parent.mkdir(parents=True, exist_ok=True)
    img.save(HERE.parent / "poster_figures" / name, "PNG")
    return path


def slot_gap() -> Path:
    """OPTIONAL VISUAL — existing approaches vs proposed direction / gap map."""
    img = Image.new("RGB", (W, H_TALL), PAPER)
    d = ImageDraw.Draw(img)
    # 3 comparison cards: Today → OfficeHours
    pairs = [
        (SAND, "Today: LMS inbox", GOLD, "OfficeHours: Ask Triage"),
        (SAND, "Today: no TA match", BLUE, "OfficeHours: dual-TA Matcher"),
        (SAND, "Today: open chatbot", MINT, "OfficeHours: stamped Study Agent"),
    ]
    gap = 16
    bw = (W - 24 - gap * 2) // 3
    for i, (c1, t1, c2, t2) in enumerate(pairs):
        x0 = 12 + i * (bw + gap)
        rounded(d, (x0, 10, x0 + bw, 132), c1)
        center(d, (x0, 10, x0 + bw, 132), [t1], [26])
        rounded(d, (x0, 150, x0 + bw, 276), c2)
        center(d, (x0, 150, x0 + bw, 276), [t2], [24])
        # down arrow
        cx = x0 + bw // 2
        d.line([(cx, 132), (cx, 150)], fill=GREEN_DK, width=4)
        d.polygon([(cx, 154), (cx - 8, 140), (cx + 8, 140)], fill=GREEN_DK)
    return save(img, "SLOT_gap.png")


def slot_architecture() -> Path:
    """PROPOSED DESIGN FIGURE — conceptual architecture / system model."""
    img = Image.new("RGB", (W, H_TALL), PAPER)
    d = ImageDraw.Draw(img)
    boxes = [
        (GOLD, ["App :5180", "Student · TA · Professor"]),
        (BLUE, ["FastAPI :8000", "requests · ta · lti · /ws"]),
        (MINT, ["Ask Triage", "Analyzer · Matcher · Synthesizer"]),
        (PEACH, ["Professor stamp", "only approved KB is AI"]),
        (SAND, ["Canvas LTI", "course + modules"]),
    ]
    gap = 12
    bw = (W - 20 - gap * 4) // 5
    for i, (fill, lines) in enumerate(boxes):
        x0 = 10 + i * (bw + gap)
        rounded(d, (x0, 18, x0 + bw, 268), fill)
        center(d, (x0 + 6, 18, x0 + bw - 6, 268), lines, [26, 20])
        if i < 4:
            arrow(d, x0 + bw + 1, 143, x0 + bw + gap - 1)
    return save(img, "SLOT_architecture.png")


def slot_pipeline() -> Path:
    """PROPOSED PROCESS / PIPELINE — Inputs → processing → outputs."""
    img = Image.new("RGB", (W, H_ROW), PAPER)
    d = ImageDraw.Draw(img)
    steps = [
        (GOLD, ["Ask", "input"]),
        (BLUE, ["Analyzer", "category"]),
        (BLUE, ["Matcher", "TA + wait"]),
        (MINT, ["Synthesizer", "hint"]),
        (PEACH, ["TA desk", "Help Coach"]),
        (PEACH, ["Stamp", "professor"]),
        (MINT, ["Study Agent", "output"]),
    ]
    gap = 8
    bw = (W - 16 - gap * 6) // 7
    for i, (fill, lines) in enumerate(steps):
        x0 = 8 + i * (bw + gap)
        rounded(d, (x0, 14, x0 + bw, 228), fill, radius=14)
        center(d, (x0 + 4, 14, x0 + bw - 4, 228), lines, [24, 18])
        if i < 6:
            arrow(d, x0 + bw + 1, 121, x0 + bw + gap - 1)
    return save(img, "SLOT_pipeline.png")


def slot_roadmap() -> Path:
    """PLANNED WORK / REQUIREMENTS VISUAL — development roadmap."""
    img = Image.new("RGB", (W, H_ROW), PAPER)
    d = ImageDraw.Draw(img)
    phases = [
        ("1", "Triage + roles"),
        ("2", "TA + KB gate"),
        ("3", "Rooms + demo"),
        ("4", "LTI live"),
        ("5", "Postgres / grades"),
    ]
    gap = 14
    bw = (W - 20 - gap * 4) // 5
    for i, (n, title) in enumerate(phases):
        x0 = 10 + i * (bw + gap)
        fill = GOLD if i >= 3 else SAND
        rounded(d, (x0, 14, x0 + bw, 228), fill)
        # number badge
        d.ellipse((x0 + bw // 2 - 22, 28, x0 + bw // 2 + 22, 72), fill=GREEN)
        nw, nh = tw(d, n, font(26, True))
        d.text((x0 + bw // 2 - nw / 2, 34), n, fill="white", font=font(26, True))
        center(d, (x0 + 8, 78, x0 + bw - 8, 220), [title], [24])
        if i < 4:
            arrow(d, x0 + bw + 1, 121, x0 + bw + gap - 1)
    return save(img, "SLOT_roadmap.png")


def slot_evaluation() -> Path:
    """PLANNED EVALUATION FRAMEWORK — test matrix / metric plan."""
    img = Image.new("RGB", (W, H_ROW), PAPER)
    d = ImageDraw.Draw(img)
    cards = [
        (BLUE, ["pytest + CI", "API / KB gate"]),
        (GOLD, ["Holdouts", "routing quality"]),
        (MINT, ["Gold-label lab", "TA labels"]),
        (PEACH, ["Walkthroughs", "3 roles"]),
        (SAND, ["Live Canvas", "1 test course"]),
    ]
    gap = 12
    bw = (W - 20 - gap * 4) // 5
    for i, (fill, lines) in enumerate(cards):
        x0 = 10 + i * (bw + gap)
        rounded(d, (x0, 14, x0 + bw, 228), fill)
        center(d, (x0 + 6, 14, x0 + bw - 6, 228), lines, [24, 20])
    return save(img, "SLOT_evaluation.png")


def main() -> None:
    for fn in (slot_gap, slot_architecture, slot_pipeline, slot_roadmap, slot_evaluation):
        p = fn()
        im = Image.open(p)
        print(p.name, im.size)


if __name__ == "__main__":
    main()
