#!/usr/bin/env python3
"""Generate OfficeHours AI architecture diagrams (custom-trained Oracle era)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIRS = [
    ROOT / "diagrams",
    Path("/opt/cursor/artifacts/diagrams"),
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_box(draw, box, fill, outline, radius=18, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(
    draw,
    box,
    lines,
    title_size=20,
    body_size=14,
    title_color="#0F172A",
    body_color="#334155",
):
    x0, y0, x1, y1 = box
    title_f = font(title_size, bold=True)
    body_f = font(body_size)
    heights = []
    for i, line in enumerate(lines):
        f = title_f if i == 0 else body_f
        bbox = draw.textbbox((0, 0), line, font=f)
        heights.append(bbox[3] - bbox[1])
    total = sum(heights) + 5 * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        f = title_f if i == 0 else body_f
        color = title_color if i == 0 else body_color
        bbox = draw.textbbox((0, 0), line, font=f)
        w = bbox[2] - bbox[0]
        x = x0 + (x1 - x0 - w) // 2
        draw.text((x, y), line, fill=color, font=f)
        y += heights[i] + 5


def arrow(draw, start, end, color="#475569", width=3):
    draw.line([start, end], fill=color, width=width)
    x0, y0 = start
    x1, y1 = end
    if abs(x1 - x0) >= abs(y1 - y0):
        direction = 1 if x1 > x0 else -1
        draw.polygon(
            [(x1, y1), (x1 - 12 * direction, y1 - 7), (x1 - 12 * direction, y1 + 7)],
            fill=color,
        )
    else:
        direction = 1 if y1 > y0 else -1
        draw.polygon(
            [(x1, y1), (x1 - 7, y1 - 12 * direction), (x1 + 7, y1 - 12 * direction)],
            fill=color,
        )


def save(img: Image.Image, name: str) -> None:
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        img.save(path, "PNG")
        print(f"Wrote {path}")


def draw_header(draw, w, title, subtitle, fill="#0A4F34"):
    draw.rectangle((0, 0, w, 132), fill=fill)
    draw.text((48, 28), "OfficeHours AI · Al Akhawayn University", fill="#A7F3D0", font=font(18, bold=True))
    draw.text((48, 60), title, fill="#F8FAFC", font=font(36, bold=True))
    draw.text((48, 104), subtitle, fill="#D1FAE5", font=font(16))


def draw_architecture() -> None:
    w, h = 1700, 1100
    img = Image.new("RGB", (w, h), "#ECFDF5")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "System Architecture (Custom-Trained Oracle)",
        "Three browser apps + FastAPI + local ML agents · no prompted Claude on the FYP path",
    )

    boxes = [
        (
            (50, 170, 350, 360),
            "#FEF3C7",
            "#B45309",
            ["Student Kiosk", "Port 5173", "Check-in / submit", "Status lookup", "KB agent chat"],
        ),
        (
            (390, 170, 690, 360),
            "#DBEAFE",
            "#1D4ED8",
            ["Professor Dashboard", "Port 5174", "Triage + curation", "Heatmap / escalations", "Office hours"],
        ),
        (
            (730, 170, 1030, 360),
            "#FFEDD5",
            "#C2410C",
            ["TA Dashboard", "Port 5175", "Live queue", "Edit teaching draft", "Resolve → pending"],
        ),
        (
            (1070, 170, 1650, 360),
            "#E0E7FF",
            "#4338CA",
            [
                "Backend API (FastAPI :8000)",
                "SQLite + SQLAlchemy",
                "REST + WebSocket /ws (live push)",
                "/requests /ta /knowledge /agent /analytics",
            ],
        ),
        (
            (50, 420, 560, 680),
            "#D1FAE5",
            "#047857",
            [
                "Oracle Analyzer",
                "Fine-tuned embedding + LogReg",
                "request_classifier.joblib",
                "Category · urgency · tags · ETA",
            ],
        ),
        (
            (600, 420, 1110, 680),
            "#A7F3D0",
            "#0F766E",
            [
                "Oracle Matcher",
                "Embedding + LogReg TA assigner",
                "matcher_classifier.joblib",
                "+ queue-depth penalty",
            ],
        ),
        (
            (1150, 420, 1650, 680),
            "#99F6E4",
            "#0F766E",
            [
                "Oracle Synthesizer",
                "Teaching-bank / approved-KB RAG",
                "synthesizer_ranker.joblib",
                "Hint + teaching approach (no LLM)",
            ],
        ),
        (
            (50, 730, 820, 930),
            "#FFF7ED",
            "#EA580C",
            [
                "Professor-in-the-loop gate",
                "TA resolve → pending_review KB entry",
                "Professor approve / edit / reject",
                "Only approved answers reach student KB agent",
            ],
        ),
        (
            (860, 730, 1650, 930),
            "#FFFFFF",
            "#0F172A",
            [
                "Training data & models",
                "120 labeled Analyzer examples · 40 learning-style labels",
                "120 Matcher silver labels · 50 Synthesizer teaching-bank rows",
                "sentence-transformers all-MiniLM-L6-v2 + scikit-learn",
            ],
        ),
    ]

    for box, fill, outline, lines in boxes:
        rounded_box(draw, box, fill, outline, radius=20, width=3)
        center_text(draw, box, lines, title_size=20, body_size=14)

    # frontends → API
    for x in (200, 540, 880):
        arrow(draw, (x, 360), (x, 390), "#334155", 3)
    draw.line([(200, 390), (1360, 390)], fill="#334155", width=3)
    arrow(draw, (1360, 390), (1360, 360), "#334155", 3)

    # API → agents
    arrow(draw, (1200, 360), (300, 420), "#047857", 3)
    arrow(draw, (1300, 360), (850, 420), "#0F766E", 3)
    arrow(draw, (1400, 360), (1400, 420), "#0F766E", 3)

    # agents → gate
    arrow(draw, (300, 680), (300, 730), "#EA580C", 3)
    arrow(draw, (850, 680), (500, 730), "#EA580C", 3)
    arrow(draw, (1400, 680), (700, 730), "#EA580C", 3)

    draw.text(
        (50, 970),
        "Deployment: browser web apps (campus Wi‑Fi / localhost demo). Not a native desktop installer. Auth is demo-mode (no login yet).",
        fill="#065F46",
        font=font(16, bold=True),
    )
    draw.text(
        (50, 1005),
        "FYP constraint: OFFICEHOURS_ALLOW_EXTERNAL_LLM=false — Analyzer / Matcher / Synthesizer are custom-trained local models.",
        fill="#334155",
        font=font(15),
    )
    save(img, "architecture.png")


def draw_workflow() -> None:
    w, h = 1800, 1020
    img = Image.new("RGB", (w, h), "#ECFDF5")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "End-to-End Oracle Workflow",
        "Submit → Analyzer → Matcher → Synthesizer → TA → Professor curation → Student KB",
        fill="#0F766E",
    )

    steps = [
        (40, 170, "1. Check-in", "Scan ID or stay\nanonymous (kiosk)"),
        (270, 170, "2. Submit", "Question (+ optional\ncode) POST /requests"),
        (500, 170, "3. Analyzer", "ML classifier\ncategory / difficulty"),
        (730, 170, "4. Matcher", "Custom TA model\n+ wait estimate"),
        (960, 170, "5. Synthesizer", "RAG teaching bank\n+ style ranker"),
        (1190, 170, "6. Live push", "WebSocket events\nto dashboards"),
        (1420, 170, "7. Cluster", "Semantic cluster_id\nfor triage groups"),
        (100, 430, "8. TA queue", "TA edits draft &\nmarks resolved"),
        (400, 430, "9. Pending KB", "Entry stays\npending_review"),
        (700, 430, "10. Professor", "Approve / edit /\nreject curation"),
        (1000, 430, "11. Approved KB", "Student agent may\nretrieve answer"),
        (1300, 430, "12. Status", "Student looks up\nrequest code"),
        (1550, 430, "13. Actions", "Agenda / .ics /\nlifetime confusion"),
    ]

    for x, y, title, body in steps:
        box = (x, y, x + 210, y + 150)
        rounded_box(draw, box, "#FFFFFF", "#065F46", radius=16, width=2)
        center_text(draw, box, [title, *body.split("\n")], title_size=17, body_size=13)

    for x in (250, 480, 710, 940, 1170, 1400):
        arrow(draw, (x, 245), (x + 20, 245), "#047857")
    draw.line([(1525, 320), (1525, 380), (205, 380), (205, 430)], fill="#047857", width=3)
    arrow(draw, (205, 415), (205, 430), "#047857")
    for x in (310, 610, 910, 1210, 1510):
        arrow(draw, (x, 505), (x + 20, 505), "#0F766E")

    note = (40, 650, 1760, 940)
    rounded_box(draw, note, "#FEF3C7", "#B45309", radius=20, width=3)
    center_text(
        draw,
        note,
        [
            "What ships as the final product?",
            "A campus web system (not a single App Store desktop app): shared student kiosk URL/device,",
            "professor browser dashboard, TA browser dashboard, all talking to one FastAPI backend.",
            "AI drafts help — professors still approve what students can see. No Claude / no mock-LLM on the assessed FYP path.",
        ],
        title_size=22,
        body_size=16,
        title_color="#92400E",
        body_color="#1C1917",
    )
    save(img, "workflow.png")


def draw_oracle_agents() -> None:
    w, h = 1600, 980
    img = Image.new("RGB", (w, h), "#ECFDF5")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Oracle Multi-Agent Design",
        "Three specialized local models · professor remains the publication gate",
        fill="#065F46",
    )

    agents = [
        (
            (60, 180, 520, 520),
            "#FEF3C7",
            "#B45309",
            [
                "Analyzer",
                "Input: question (+ code)",
                "Model: embeddings + LogReg",
                "Train: 120 labeled requests",
                "Out: category, urgency,",
                "difficulty, tags, ETA",
                "Artifact: request_classifier.joblib",
            ],
        ),
        (
            (560, 180, 1040, 520),
            "#DBEAFE",
            "#1D4ED8",
            [
                "Matcher",
                "Input: Analyzer + TA roster",
                "Model: embeddings + LogReg",
                "Train: 120 silver TA labels",
                "Out: assigned_ta, alt TA,",
                "wait minutes, rationale",
                "Artifact: matcher_classifier.joblib",
            ],
        ),
        (
            (1080, 180, 1540, 520),
            "#D1FAE5",
            "#047857",
            [
                "Synthesizer",
                "Input: Q + style + KB hits",
                "Model: RAG + style ranker",
                "Train: 50 teaching-bank rows",
                "Out: student_hint,",
                "teaching_approach",
                "Artifact: synthesizer_ranker.joblib",
            ],
        ),
    ]
    for box, fill, outline, lines in agents:
        rounded_box(draw, box, fill, outline, radius=22, width=3)
        center_text(draw, box, lines, title_size=24, body_size=15)

    arrow(draw, (520, 350), (560, 350), "#334155")
    arrow(draw, (1040, 350), (1080, 350), "#334155")

    bottom = (60, 580, 1540, 900)
    rounded_box(draw, bottom, "#FFFFFF", "#0F172A", radius=20, width=3)
    center_text(
        draw,
        bottom,
        [
            "Embeddings backbone: sentence-transformers all-MiniLM-L6-v2 (shared)",
            "Extra: learning_style_classifier.joblib trained on 40 style-labeled texts",
            "All labels are synthetic / silver / curated for the FYP — not real private student transcripts",
            "Runtime default: OFFICEHOURS_ALLOW_EXTERNAL_LLM=false (Claude path gated off)",
        ],
        title_size=20,
        body_size=16,
    )
    save(img, "oracle_agents.png")


def draw_product_deployment() -> None:
    w, h = 1600, 980
    img = Image.new("RGB", (w, h), "#FFFBEB")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Final Product & Deployment Model",
        "What you demo / submit — and what it is not",
        fill="#92400E",
    )

    boxes = [
        (
            (60, 180, 520, 460),
            "#FEF3C7",
            "#B45309",
            [
                "Student experience",
                "Shared hallway kiosk OR",
                "laptop/tablet browser URL",
                "Optional barcode scan",
                "Anonymous OK",
                "No student login accounts yet",
            ],
        ),
        (
            (560, 180, 1040, 460),
            "#DBEAFE",
            "#1D4ED8",
            [
                "Staff experience",
                "Professor opens dashboard",
                "in desktop Chrome/Edge",
                "TA opens TA dashboard",
                "Live WebSocket updates",
                "Demo: pick TA name in UI",
            ],
        ),
        (
            (1080, 180, 1540, 460),
            "#D1FAE5",
            "#047857",
            [
                "Backend",
                "One FastAPI process",
                "SQLite file by default",
                "Can swap to Postgres",
                "Campus server / laptop",
                "for the FYP demo day",
            ],
        ),
        (
            (60, 520, 780, 880),
            "#FEE2E2",
            "#B91C1C",
            [
                "Not (yet) this",
                "Not an App Store / Play Store app",
                "Not a native Windows/Mac installer",
                "Not SSO/AUI login (future work)",
                "Not auto-publishing answers to students",
            ],
        ),
        (
            (840, 520, 1540, 880),
            "#DCFCE7",
            "#15803D",
            [
                "FYP deliverable",
                "Working multi-agent triage demo",
                "Custom-trained models + metrics",
                "Professor-in-the-loop KB curation",
                "Architecture diagrams + evaluation",
            ],
        ),
    ]
    for box, fill, outline, lines in boxes:
        rounded_box(draw, box, fill, outline, radius=20, width=3)
        center_text(draw, box, lines, title_size=22, body_size=15)
    save(img, "product_deployment.png")


def draw_erd() -> None:
    w, h = 1700, 1100
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Database Entity-Relationship Diagram",
        "SQLite (officehours.db) · Oracle + KB + TA roster tables",
        fill="#1E3A8A",
    )

    entities = [
        (
            (40, 170, 420, 520),
            "#FEF3C7",
            "#B45309",
            [
                "requests",
                "id PK",
                "text / anonymous / student_id",
                "category / urgency / style",
                "cluster_id / recommended_action",
                "oracle_* / assigned_ta",
                "student_hint / oracle_trace_json",
                "created_at",
            ],
        ),
        (
            (460, 170, 840, 430),
            "#DBEAFE",
            "#1D4ED8",
            [
                "knowledge_entries",
                "id PK",
                "question_text / answer_draft",
                "student_hint / status",
                "drafter_backend / style",
                "source_request_id FK",
                "reviewed_at",
            ],
        ),
        (
            (880, 170, 1240, 390),
            "#D1FAE5",
            "#047857",
            [
                "ta_roster",
                "id PK",
                "name UNIQUE",
                "expertise_tags JSON",
                "queue_depth",
                "is_available",
            ],
        ),
        (
            (1280, 170, 1660, 430),
            "#E0E7FF",
            "#4338CA",
            [
                "recommendation_decisions",
                "id PK",
                "card_id / action_kind",
                "status / cluster_id",
                "request_ids JSON",
                "action_plan JSON",
            ],
        ),
        (
            (460, 500, 840, 720),
            "#FFEDD5",
            "#C2410C",
            [
                "office_hours_windows",
                "id PK",
                "day / start / end",
                "location",
                "created_at",
            ],
        ),
    ]

    for box, fill, outline, lines in entities:
        rounded_box(draw, box, fill, outline, radius=16, width=3)
        x0, y0, x1, y1 = box
        draw.rectangle((x0, y0, x1, y0 + 48), fill=outline)
        draw.text((x0 + 16, y0 + 12), lines[0], fill="#FFFFFF", font=font(20, bold=True))
        y = y0 + 62
        for line in lines[1:]:
            draw.text((x0 + 18, y), line, fill="#111827", font=font(15))
            y += 26

    arrow(draw, (420, 300), (460, 300), "#1D4ED8")
    draw.text((425, 260), "creates", fill="#1E3A8A", font=font(14, bold=True))
    arrow(draw, (300, 520), (300, 620), "#047857")
    draw.line([(300, 620), (880, 280)], fill="#047857", width=2)
    arrow(draw, (860, 280), (880, 280), "#047857")
    draw.text((310, 560), "Matcher reads roster", fill="#065F46", font=font(14, bold=True))

    note = (40, 780, 1660, 1040)
    rounded_box(draw, note, "#ECFEFF", "#0891B2", radius=18, width=3)
    center_text(
        draw,
        note,
        [
            "Key runtime paths",
            "POST /requests → Oracle agents → persist Request + pending KnowledgeEntry + WS broadcast",
            "POST /ta/resolve → update teaching notes; status remains pending_review until professor PATCH /knowledge/{id}",
            "POST /agent/ask → semantic search over approved knowledge_entries only",
        ],
        title_size=20,
        body_size=15,
        title_color="#155E75",
    )
    save(img, "database_erd.png")


if __name__ == "__main__":
    draw_architecture()
    draw_workflow()
    draw_oracle_agents()
    draw_product_deployment()
    draw_erd()
