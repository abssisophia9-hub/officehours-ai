#!/usr/bin/env python3
"""Print-size OfficeHours AI poster visuals — large type, readable from a few steps away."""

from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
REPO_URL = "https://github.com/abssisophia9-hub/officehours-ai"

GREEN = "#006633"
GREEN_DK = "#004B2B"
INK = "#14201C"
MUTED = "#3A4541"
LINE = "#7F8C86"
PAPER = "#FFFFFF"
SAND = "#F2F6F3"
GOLD = "#FFF3C4"
BLUE = "#DCEBFF"
MINT = "#D8F3E6"
PEACH = "#FFD9C2"
LILAC = "#E8E0FF"


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


def header(draw, w, title, subtitle):
    draw.rectangle((0, 0, w, 110), fill=GREEN)
    draw.text((36, 18), "OfficeHours AI  ·  Capstone poster visual", fill="#C8EBCF", font=font(22, True))
    draw.text((36, 48), title, fill="#FFFFFF", font=font(40, True))
    draw.text((36, 92), subtitle, fill="#D7F0DE", font=font(20))


def box(draw, r, fill, outline=GREEN_DK, radius=22, width=4):
    draw.rounded_rectangle(r, radius=radius, fill=fill, outline=outline, width=width)


def centered(draw, r, lines, title_size=28, body_size=20):
    x0, y0, x1, y1 = r
    tf, bf = font(title_size, True), font(body_size)
    heights = [tw(draw, line, tf if i == 0 else bf)[1] for i, line in enumerate(lines)]
    total = sum(heights) + 8 * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        f = tf if i == 0 else bf
        color = INK if i == 0 else MUTED
        ww, hh = tw(draw, line, f)
        draw.text((x0 + (x1 - x0 - ww) // 2, y), line, fill=color, font=f)
        y += hh + 8


def arrow_h(draw, x0, y, x1):
    draw.line([(x0, y), (x1 - 16, y)], fill=GREEN_DK, width=6)
    draw.polygon([(x1, y), (x1 - 20, y - 11), (x1 - 20, y + 11)], fill=GREEN_DK)


def arrow_v(draw, x, y0, y1):
    draw.line([(x, y0), (x, y1 - 16)], fill=GREEN_DK, width=6)
    draw.polygon([(x, y1), (x - 11, y1 - 20), (x + 11, y1 - 20)], fill=GREEN_DK)


def save(img: Image.Image, name: str) -> Path:
    HERE.mkdir(parents=True, exist_ok=True)
    path = HERE / name
    img.save(path, "PNG")
    # also keep a copy used by the filled poster
    alt = HERE.parent / "poster_figures" / name
    alt.parent.mkdir(parents=True, exist_ok=True)
    img.save(alt, "PNG")
    return path


def v01_architecture() -> Path:
    w, h = 2400, 1500
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "1 · System architecture", "What a visitor sees first: one app, one API, Canvas as the course source of truth")

    top = [
        (60, 150, 760, 520, GOLD, ["Student / TA / Professor app", "officehours-app  :5180", "React · Vite · Tailwind", "Quiet ask · Live Queue · KB stamp", "One login  ·  role per course"]),
        (840, 150, 1560, 520, BLUE, ["FastAPI backend  :8000", "/requests  /ta  /knowledge  /lti", "/help-room  /agent/ask  /ws", "SQLite now  →  Postgres at go-live", "Auth + CORS + course scope"]),
        (1640, 150, 2340, 520, MINT, ["AUI Canvas LMS", "LTI 1.3 launch + REST modules", "Materials → course knowledge base", "No AUI portal scraping", "IT credentials required for live"]),
    ]
    for r in top:
        box(d, r[:4], r[4])
        centered(d, r[:4], r[5], 30, 22)
    arrow_h(d, 760, 335, 840)
    arrow_h(d, 1560, 335, 1640)

    mid = [
        (60, 580, 760, 980, GOLD, ["Ask Triage · Analyzer", "MiniLM embeddings + LogReg", "category · urgency · difficulty", "request_classifier.joblib"]),
        (840, 580, 1560, 980, BLUE, ["Ask Triage · Matcher", "TA assign + queue penalty", "primary / alternate TA · wait", "matcher_classifier.joblib"]),
        (1640, 580, 2340, 980, MINT, ["Ask Triage · Synthesizer", "RAG over approved KB only", "hint · teaching approach", "synthesizer_ranker.joblib"]),
    ]
    for r in mid:
        box(d, r[:4], r[4])
        centered(d, r[:4], r[5], 30, 22)
    arrow_h(d, 760, 780, 840)
    arrow_h(d, 1560, 780, 1640)
    arrow_v(d, 1200, 520, 580)

    box(d, (60, 1040, 1170, 1430), PEACH)
    centered(d, (60, 1040, 1170, 1430), [
        "Professor-in-the-loop",
        "TA notes become pending_review",
        "Approve / edit / reject the knowledge draft",
        "Only stamped answers reach Study Agent",
    ], 30, 22)
    box(d, (1230, 1040, 2340, 1430), SAND)
    centered(d, (1230, 1040, 2340, 1430), [
        "Identity + help mode",
        "Quiet ask hides the name from staff",
        "Help Coach is TA-only, mid-session",
        "External LLM off  (OFFICEHOURS_ALLOW_EXTERNAL_LLM=false)",
    ], 30, 22)
    return save(img, "V01_architecture.png")


def v02_agents() -> Path:
    w, h = 2400, 1200
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "2 · Ask Triage agents", "Three local models at intake — not a ChatGPT backend")

    cards = [
        (60, 160, 760, 900, GOLD, [
            "Analyzer",
            "Input: student ask (+ code)",
            "Model: MiniLM + LogisticRegression",
            "Output: category, urgency,",
            "difficulty, tags, ETA",
            "Artifact:",
            "request_classifier.joblib",
        ]),
        (840, 160, 1560, 900, BLUE, [
            "Matcher",
            "Input: Analyzer + TA roster",
            "Model: embeddings + LogReg",
            "Output: primary / alt TA,",
            "wait minutes, rationale",
            "Artifact:",
            "matcher_classifier.joblib",
        ]),
        (1640, 160, 2340, 900, MINT, [
            "Synthesizer",
            "Input: ask + approved KB",
            "Model: RAG + style ranker",
            "Output: student hint +",
            "teaching approach / seek-help",
            "Artifact:",
            "synthesizer_ranker.joblib",
        ]),
    ]
    for r in cards:
        box(d, r[:4], r[4])
        centered(d, r[:4], r[5], 36, 24)
    arrow_h(d, 760, 530, 840)
    arrow_h(d, 1560, 530, 1640)
    d.text((60, 960), "Shared backbone: sentence-transformers  all-MiniLM-L6-v2     ·     Help Coach is a separate TA-only surface, not a fourth intake joblib", fill=MUTED, font=font(24))
    d.text((60, 1020), "FYP constraint: OFFICEHOURS_ALLOW_EXTERNAL_LLM=false     ·     Labels are synthetic / silver unless a gold-label TA lab is run", fill=MUTED, font=font(24))
    return save(img, "V02_ask_triage_agents.png")


def v03_pipeline() -> Path:
    w, h = 2400, 900
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "3 · Ask pipeline", "The walk-up story: ask → local triage → human desk → professor stamp → student AI")

    steps = [
        (GOLD, ["1  Ask", "Quiet or identified", "help mode"]),
        (BLUE, ["2  Analyzer", "category · urgency", "difficulty · ETA"]),
        (BLUE, ["3  Matcher", "primary / alt TA", "queue wait"]),
        (MINT, ["4  Synthesizer", "hint + approach", "or seek-help"]),
        (PEACH, ["5  TA desk", "queue + Help Coach", "claim / reply"]),
        (PEACH, ["6  Professor", "stamp / edit KB", "cluster review"]),
        (MINT, ["7  Study Agent", "approved KB only", "/agent/ask"]),
    ]
    gap = 18
    bw = (w - 80 - gap * 6) // 7
    for i, (fill, lines) in enumerate(steps):
        x0 = 40 + i * (bw + gap)
        box(d, (x0, 170, x0 + bw, 820), fill, radius=20)
        centered(d, (x0 + 8, 170, x0 + bw - 8, 820), lines, 28, 20)
        if i < 6:
            arrow_h(d, x0 + bw + 1, 495, x0 + bw + gap - 1)
    return save(img, "V03_pipeline.png")


def v04_gap() -> Path:
    w, h = 2400, 1100
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "4 · Gap map", "What people already know vs what this product adds")

    headers = ["Capability", "LMS inbox / Piazza / chatbot", "OfficeHours AI"]
    rows = [
        ("Routing", "Manual, first-come, untyped", "Ask Triage: MiniLM + LogReg"),
        ("TA staffing", "No dual-TA match or queue model", "Matcher + queue + dual-TA roster"),
        ("Student AI", "Unconstrained LLM or FAQ dump", "Study Agent quotes stamped KB only"),
        ("Ask barrier", "Public post or email only", "Quiet ask → private My asks reply"),
        ("Faculty control", "AI can invent the syllabus", "Professor stamp is the publication gate"),
    ]
    cols = [420, 960, 960]
    y = 150
    x = 40
    hf, rf, bf = font(26, True), font(24), font(24, True)
    for i, head in enumerate(headers):
        fill = GREEN_DK if i == 2 else SAND
        color = "white" if i == 2 else INK
        d.rectangle((x, y, x + cols[i], y + 70), fill=fill, outline=LINE, width=2)
        d.text((x + 18, y + 18), head, fill=color, font=hf)
        x += cols[i]
    y = 220
    for r, row in enumerate(rows):
        x = 40
        bg = PAPER if r % 2 == 0 else SAND
        for i, cell in enumerate(row):
            fill = MINT if i == 2 else bg
            d.rectangle((x, y, x + cols[i], y + 150), fill=fill, outline=LINE, width=2)
            f = bf if i in (0, 2) else rf
            d.text((x + 18, y + 54), cell, fill=INK, font=f)
            x += cols[i]
        y += 150
    return save(img, "V04_gap_map.png")


def v05_roles() -> Path:
    w, h = 2400, 1100
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "5 · Three roles, one course", "Role comes from Canvas / course membership — a TA is staff, not a classmate")

    cards = [
        (60, 160, 780, 1020, GOLD, [
            "Student",
            "Ask is the only primary",
            "Quiet ask if they hesitate",
            "My asks = TA reply path",
            "Study Agent after stamp",
            "Rooms = classmate forum",
            "Strategist = revision planner",
        ]),
        (840, 160, 1560, 1020, BLUE, [
            "TA  (staff)",
            "Live Queue is the desk",
            "Claim → help → resolve",
            "Help Coach mid-session",
            "Does not publish the KB",
            "Drafts stay pending_review",
            "Dual-TA roster per course",
        ]),
        (1640, 160, 2340, 1020, MINT, [
            "Professor",
            "Repeated Topics first",
            "Stamp / edit / reject KB",
            "Canvas module sync",
            "Group-meeting clusters",
            "Only stamped text is AI",
            "Owns the course answers",
        ]),
    ]
    for r in cards:
        box(d, r[:4], r[4])
        centered(d, r[:4], r[5], 36, 26)
    return save(img, "V05_roles.png")


def v06_gate() -> Path:
    w, h = 2400, 900
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "6 · Professor stamp gate", "The integrity story: AI may not invent the syllabus")

    steps = [
        (PEACH, ["TA resolve", "teaching notes", "→ pending_review"]),
        (GOLD, ["Professor", "approve / edit", "or reject"]),
        (MINT, ["Approved KB", "course-scoped", "stamped text only"]),
        (BLUE, ["Study Agent", "/agent/ask", "quotes stamp only"]),
        (SAND, ["Refuse", "weak / missing KB", "0 unauthorized quotes"]),
    ]
    gap = 28
    bw = (w - 80 - gap * 4) // 5
    for i, (fill, lines) in enumerate(steps):
        x0 = 40 + i * (bw + gap)
        box(d, (x0, 180, x0 + bw, 820), fill)
        centered(d, (x0 + 10, 180, x0 + bw - 10, 820), lines, 30, 22)
        if i < 4:
            arrow_h(d, x0 + bw + 2, 500, x0 + bw + gap - 2)
    return save(img, "V06_stamp_gate.png")


def v07_roadmap() -> Path:
    w, h = 2400, 900
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "7 · Work plan  ·  demo → live", "Five staged phases — live Canvas is an IT gate, not missing product code")

    phases = [
        ("1", "Triage + roles", "Ask path, auth,", "course membership"),
        ("2", "TA + KB gate", "Queue, Help Coach,", "professor stamp"),
        ("3", "Rooms + demo", "Forum + local", "Canvas mirror"),
        ("4", "LTI live", "Signed LTI 1.3 +", "module sync"),
        ("5", "Scale path", "Postgres host +", "Strategist grades"),
    ]
    gap = 28
    bw = (w - 80 - gap * 4) // 5
    for i, (n, title, a, b) in enumerate(phases):
        x0 = 40 + i * (bw + gap)
        fill = SAND if i < 3 else GOLD
        box(d, (x0, 170, x0 + bw, 820), fill)
        d.ellipse((x0 + bw // 2 - 40, 210, x0 + bw // 2 + 40, 290), fill=GREEN)
        nw, nh = tw(d, n, font(36, True))
        d.text((x0 + bw // 2 - nw / 2, 226), n, fill="white", font=font(36, True))
        centered(d, (x0 + 12, 310, x0 + bw - 12, 800), [title, a, b], 30, 22)
        if i < 4:
            arrow_h(d, x0 + bw + 2, 495, x0 + bw + gap - 2)
    return save(img, "V07_roadmap.png")


def v08_evaluation() -> Path:
    w, h = 2400, 1000
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "8 · Evaluation framework", "How we will know it works — no unverified campus performance claims")

    cards = [
        (BLUE, ["pytest + CI", "API / auth / KB gate", "regression on demo path"]),
        (GOLD, ["Triage holdouts", "category / routing", "cite metrics carefully"]),
        (MINT, ["Gold-label TA lab", "human labels on asks", "docs/gold_label_lab.md"]),
        (PEACH, ["Role walkthroughs", "student · TA · professor", "task completion"]),
        (SAND, ["Live Canvas check", "LTI launch + sync", "one AUI test course"]),
    ]
    gap = 24
    bw = (w - 80 - gap * 4) // 5
    for i, (fill, lines) in enumerate(cards):
        x0 = 40 + i * (bw + gap)
        box(d, (x0, 170, x0 + bw, 920), fill)
        centered(d, (x0 + 12, 170, x0 + bw - 12, 920), lines, 28, 22)
    return save(img, "V08_evaluation.png")


def v09_canvas() -> Path:
    w, h = 2400, 1000
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "9 · Demo path vs live Canvas", "Same product. Live needs IT — LTI key, API token, HTTPS")

    box(d, (60, 170, 1140, 920), GOLD)
    centered(d, (80, 170, 1120, 920), [
        "DEMO  ·  OFFICEHOURS_DEMO=true",
        "Sara / Youssef sample accounts",
        "Local Canvas mirror + chapter outlines",
        "SQLite on the laptop",
        "Showcase and FYP walkthroughs",
        "No campus credentials required",
    ], 32, 26)
    box(d, (1260, 170, 2340, 920), MINT)
    centered(d, (1280, 170, 2320, 920), [
        "LIVE  ·  OFFICEHOURS_DEMO=false",
        "Users come from the linked LMS course",
        "Signed Canvas LTI 1.3 + REST modules",
        "Postgres at go-live",
        "One AUI test course first",
        "Strategist grades wait on the token",
    ], 32, 26)
    return save(img, "V09_demo_vs_live.png")


def v10_qr() -> Path:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=16, border=2)
    qr.add_data(REPO_URL)
    qr.make(fit=True)
    raw = qr.make_image(fill_color=GREEN_DK, back_color="white").convert("RGB")
    raw = raw.resize((900, 900), Image.Resampling.NEAREST)
    w, h = 1200, 1400
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    header(d, w, "10 · Repository", "Scan for code, diagrams, and the working prototype")
    img.paste(raw, ((w - 900) // 2, 200))
    label = "github.com/abssisophia9-hub/officehours-ai"
    lw, _ = tw(d, label, font(26, True))
    d.text(((w - lw) // 2, 1140), label, fill=GREEN_DK, font=font(26, True))
    d.text((80, 1200), "Proposal  ·  Repository  ·  Supporting material", fill=MUTED, font=font(24))
    save(img, "V10_qr.png")
    # also write a clean square QR for the template slot
    raw.save(HERE / "V10_qr_square.png")
    raw.save(HERE.parent / "poster_figures" / "fig_qr.png")
    return HERE / "V10_qr.png"


def copy_repo_diagrams() -> list[Path]:
    mapping = {
        "architecture.png": "V11_repo_architecture.png",
        "workflow.png": "V12_repo_workflow.png",
        "oracle_agents.png": "V13_repo_ask_triage.png",
        "product_deployment.png": "V14_repo_deployment.png",
        "database_erd.png": "V15_repo_database.png",
        "canvas_enrollment.png": "V16_repo_canvas.png",
    }
    out = []
    src_dir = REPO / "diagrams"
    for src_name, dest_name in mapping.items():
        src = src_dir / src_name
        dest = HERE / dest_name
        dest.write_bytes(src.read_bytes())
        out.append(dest)
    return out


def write_index(paths: list[Path]) -> None:
    cards = []
    for p in paths:
        cards.append(
            f'<figure><a href="{p.name}"><img src="{p.name}" alt="{p.stem}"></a>'
            f"<figcaption>{p.stem.replace('_', ' ')}</figcaption></figure>"
        )
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>OfficeHours AI — Poster visuals</title>
  <style>
    body {{ margin: 0; font-family: "Liberation Sans", "Segoe UI", sans-serif; background: #f4f7f5; color: #14201C; }}
    header {{ background: #006633; color: #fff; padding: 28px 32px; }}
    header h1 {{ margin: 0 0 8px; font-size: 32px; }}
    header p {{ margin: 0; opacity: .92; }}
    main {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: 1fr; gap: 28px; }}
    figure {{ margin: 0; background: #fff; border: 1px solid #c9d2ce; box-shadow: 0 8px 24px rgba(0,75,43,.08); }}
    img {{ width: 100%; display: block; }}
    figcaption {{ padding: 10px 14px; font-weight: 700; font-size: 15px; color: #004B2B; }}
  </style>
</head>
<body>
  <header>
    <h1>OfficeHours AI — all poster visuals</h1>
    <p>Print-size PNGs. These are the first thing a visitor should see. Drop V01–V10 into the SSE template figure slots. V11–V16 are the repo architecture diagrams.</p>
  </header>
  <main><div class="grid">{''.join(cards)}</div></main>
</body>
</html>
"""
    (HERE / "index.html").write_text(html, encoding="utf-8")


def write_readme(paths: list[Path]) -> None:
    lines = [
        "# Poster visuals",
        "",
        "These are the walk-up figures. Print them large. Text on the SSE poster supports them — it does not replace them.",
        "",
        "| File | Slot on the SSE template |",
        "| --- | --- |",
        "| `V01_architecture.png` | **PROPOSED DESIGN FIGURE** |",
        "| `V02_ask_triage_agents.png` | Optional extra / backboard |",
        "| `V03_pipeline.png` | **PROPOSED PROCESS / PIPELINE** |",
        "| `V04_gap_map.png` | **OPTIONAL VISUAL** (gap map) |",
        "| `V05_roles.png` | Optional extra next to Problem / Stakeholders |",
        "| `V06_stamp_gate.png` | Optional extra next to Ethics / Study Agent |",
        "| `V07_roadmap.png` | **PLANNED WORK / REQUIREMENTS VISUAL** |",
        "| `V08_evaluation.png` | **PLANNED EVALUATION FRAMEWORK** |",
        "| `V09_demo_vs_live.png` | Optional extra next to Feasibility |",
        "| `V10_qr.png` / `V10_qr_square.png` | **Replace with QR** |",
        "| `V11`–`V16` | Full repo diagrams if a judge wants more detail |",
        "",
        "Open [`index.html`](index.html) to review every figure.",
        "",
        "Rebuild:",
        "",
        "```bash",
        "backend/venv/bin/python docs/presentations/poster_visuals/build_visuals.py",
        "```",
        "",
    ]
    (HERE / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    paths = [
        v01_architecture(),
        v02_agents(),
        v03_pipeline(),
        v04_gap(),
        v05_roles(),
        v06_gate(),
        v07_roadmap(),
        v08_evaluation(),
        v09_canvas(),
        v10_qr(),
        *copy_repo_diagrams(),
    ]
    write_index(paths)
    write_readme(paths)
    for p in paths:
        print(p.name, Image.open(p).size)


if __name__ == "__main__":
    main()
