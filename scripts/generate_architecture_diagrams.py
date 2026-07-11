#!/usr/bin/env python3
"""Generate OfficeHours AI architecture diagrams with Pillow."""

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
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def rounded_box(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: str,
    outline: str,
    radius: int = 18,
    width: int = 2,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def center_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[str],
    title_size: int = 22,
    body_size: int = 15,
    title_color: str = "#0F172A",
    body_color: str = "#334155",
) -> None:
    x0, y0, x1, y1 = box
    title_f = font(title_size, bold=True)
    body_f = font(body_size)
    heights = []
    for i, line in enumerate(lines):
        f = title_f if i == 0 else body_f
        bbox = draw.textbbox((0, 0), line, font=f)
        heights.append(bbox[3] - bbox[1])
    total = sum(heights) + 6 * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        f = title_f if i == 0 else body_f
        color = title_color if i == 0 else body_color
        bbox = draw.textbbox((0, 0), line, font=f)
        w = bbox[2] - bbox[0]
        x = x0 + (x1 - x0 - w) // 2
        draw.text((x, y), line, fill=color, font=f)
        y += heights[i] + 6


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = "#475569",
    width: int = 3,
) -> None:
    draw.line([start, end], fill=color, width=width)
    x0, y0 = start
    x1, y1 = end
    if abs(x1 - x0) >= abs(y1 - y0):
        direction = 1 if x1 > x0 else -1
        draw.polygon(
            [
                (x1, y1),
                (x1 - 12 * direction, y1 - 7),
                (x1 - 12 * direction, y1 + 7),
            ],
            fill=color,
        )
    else:
        direction = 1 if y1 > y0 else -1
        draw.polygon(
            [
                (x1, y1),
                (x1 - 7, y1 - 12 * direction),
                (x1 + 7, y1 - 12 * direction),
            ],
            fill=color,
        )


def save(img: Image.Image, name: str) -> None:
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        img.save(path, "PNG")
        print(f"Wrote {path}")


def draw_architecture() -> None:
    w, h = 1600, 980
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    # background atmosphere
    draw.rectangle((0, 0, w, 140), fill="#0F172A")
    draw.text((48, 36), "OfficeHours AI", fill="#A5B4FC", font=font(22, bold=True))
    draw.text((48, 72), "System Architecture", fill="#F8FAFC", font=font(42, bold=True))
    draw.text(
        (48, 122),
        "Student kiosk + professor dashboard + FastAPI + AI/NLP + action orchestration",
        fill="#CBD5E1",
        font=font(18),
    )

    boxes = [
        ((60, 200, 380, 380), "#EEF2FF", "#6366F1", ["Student Kiosk", "Check-in / barcode", "Anonymous or ID", "Submit request", "Status lookup"]),
        ((460, 200, 780, 380), "#ECFDF5", "#059669", ["Professor Dashboard", "Queue + charts", "Recommendation cards", "Office hours setup", "Approve / edit / dismiss"]),
        ((860, 200, 1180, 380), "#FFF7ED", "#EA580C", ["Backend API", "FastAPI + SQLite", "/requests /actions", "/office-hours", "CORS + health"]),
        ((1260, 200, 1540, 380), "#FDF2F8", "#DB2777", ["AI / NLP Layer", "Rule + ML classifier", "Embeddings / clusters", "Summarizer", "Recommendations"]),
        ((460, 480, 1140, 680), "#F1F5F9", "#334155", ["Action Orchestration", "Persist professor decision", "Build agenda / status / privacy plan", "Optional .ics calendar export", "Anonymous request-code guidance"]),
        ((60, 740, 1540, 900), "#FFFFFF", "#0F172A", ["Data & Evaluation", "Synthetic + labeled datasets  ·  Demo seed script  ·  Survey templates + analysis  ·  Mid/final reports  ·  CI (pytest + Vite builds)"]),
    ]

    for box, fill, outline, lines in boxes:
        rounded_box(draw, box, fill, outline, radius=22, width=3)
        center_text(draw, box, lines, title_size=24, body_size=16)

    # Frontends talk to the API; API uses AI and orchestration.
    draw.line([(220, 380), (220, 430), (980, 430), (980, 380)], fill="#6366F1", width=3)
    arrow(draw, (980, 395), (980, 380), "#6366F1")
    draw.line([(620, 380), (620, 430)], fill="#059669", width=3)
    arrow(draw, (1180, 290), (1260, 290), "#EA580C")
    arrow(draw, (1020, 380), (1020, 480), "#334155")
    arrow(draw, (1400, 380), (1400, 560), "#DB2777")
    draw.line([(1400, 560), (1140, 560)], fill="#DB2777", width=3)
    arrow(draw, (800, 680), (800, 740), "#0F172A")

    draw.text((60, 930), "Professor remains in control of every final action.", fill="#64748B", font=font(18))
    save(img, "architecture.png")


def draw_workflow() -> None:
    w, h = 1700, 900
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, w, 130), fill="#0B1220")
    draw.text((48, 34), "OfficeHours AI", fill="#93C5FD", font=font(20, bold=True))
    draw.text((48, 68), "End-to-End Request Workflow", fill="#F8FAFC", font=font(40, bold=True))

    steps = [
        (60, 190, "1. Office hours", "Professor sets\navailability windows"),
        (300, 190, "2. Check-in", "Student scans or\ntypes ID / stays anon"),
        (540, 190, "3. Submit", "Free-text request\nto POST /requests"),
        (780, 190, "4. Classify", "Rule or ML backend\ncategory + urgency"),
        (1020, 190, "5. Cluster", "Embed + cosine\nassign cluster_id"),
        (1260, 190, "6. Recommend", "Suggest FAQ / group\n1:1 / TA / admin"),
        (150, 470, "7. Dashboard", "Charts + triage table\n+ action cards"),
        (470, 470, "8. Decide", "Approve / edit /\ndismiss card"),
        (790, 470, "9. Orchestrate", "Agenda + status +\nprivacy plan"),
        (1110, 470, "10. Export", ".ics calendar when\noffice hours exist"),
        (1430, 470, "11. Status", "Student looks up\nrequest code"),
    ]

    for x, y, title, body in steps:
        box = (x, y, x + 210, y + 150)
        rounded_box(draw, box, "#FFFFFF", "#1E293B", radius=18, width=2)
        center_text(draw, box, [title, *body.split("\n")], title_size=18, body_size=14)

    # top row arrows
    for x in (270, 510, 750, 990, 1230):
        arrow(draw, (x, 265), (x + 30, 265), "#2563EB")
    # down from recommend to dashboard path
    draw.line([(1365, 340), (1365, 400), (255, 400), (255, 470)], fill="#2563EB", width=3)
    arrow(draw, (255, 455), (255, 470), "#2563EB")
    for x in (360, 680, 1000, 1320):
        arrow(draw, (x, 545), (x + 30, 545), "#0F766E")

    note_box = (60, 700, 1640, 850)
    rounded_box(draw, note_box, "#ECFEFF", "#0891B2", radius=20, width=3)
    center_text(
        draw,
        note_box,
        [
            "Human-in-the-loop triage",
            "AI never auto-acts. Anonymous students get request-code guidance;",
            "identified students can receive direct follow-up. Open office hours stay walk-in friendly.",
        ],
        title_size=24,
        body_size=17,
        title_color="#155E75",
        body_color="#0F172A",
    )
    save(img, "workflow.png")


def draw_erd() -> None:
    w, h = 1500, 920
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    draw.rectangle((0, 0, w, 130), fill="#111827")
    draw.text((48, 34), "OfficeHours AI", fill="#FDE68A", font=font(20, bold=True))
    draw.text((48, 68), "Database Entity-Relationship Diagram", fill="#F9FAFB", font=font(38, bold=True))

    entities = [
        (
            (80, 190, 480, 470),
            "#FEF3C7",
            "#B45309",
            [
                "requests",
                "id PK",
                "text",
                "anonymous",
                "student_id",
                "category",
                "cluster_id",
                "recommended_action",
                "created_at",
            ],
        ),
        (
            (540, 190, 980, 500),
            "#DBEAFE",
            "#1D4ED8",
            [
                "recommendation_decisions",
                "id PK",
                "card_id",
                "action_kind / title",
                "status",
                "cluster_id",
                "professor_note",
                "request_ids (JSON)",
                "action_plan (JSON)",
                "created_at / updated_at",
            ],
        ),
        (
            (1040, 190, 1420, 430),
            "#DCFCE7",
            "#15803D",
            [
                "office_hours_windows",
                "id PK",
                "day",
                "start / end",
                "location",
                "created_at",
            ],
        ),
    ]

    for box, fill, outline, lines in entities:
        rounded_box(draw, box, fill, outline, radius=18, width=3)
        x0, y0, x1, y1 = box
        draw.rectangle((x0, y0, x1, y0 + 54), fill=outline)
        draw.text((x0 + 20, y0 + 14), lines[0], fill="#FFFFFF", font=font(22, bold=True))
        y = y0 + 70
        for line in lines[1:]:
            draw.text((x0 + 24, y), line, fill="#111827", font=font(17))
            y += 28

    # relationship labels
    arrow(draw, (480, 300), (540, 300), "#1D4ED8")
    draw.text((485, 250), "1..n linked via", fill="#1E3A8A", font=font(15, bold=True))
    draw.text((485, 272), "request_ids JSON", fill="#1E3A8A", font=font(15))

    arrow(draw, (980, 320), (1040, 320), "#15803D")
    draw.text((980, 270), "used by", fill="#14532D", font=font(15, bold=True))
    draw.text((980, 292), "ICS scheduling", fill="#14532D", font=font(15))

    note = (80, 560, 1420, 860)
    rounded_box(draw, note, "#FFFFFF", "#334155", radius=20, width=3)
    center_text(
        draw,
        note,
        [
            "Runtime store: SQLite (officehours.db) via SQLAlchemy",
            "Create path: POST /requests → classify + cluster → persist Request",
            "Decision path: POST /actions/recommendations → persist RecommendationDecision + action_plan JSON",
            "Status path: GET /requests/{id}/status → privacy-safe student update from latest decision",
            "Availability path: CRUD /office-hours → OfficeHoursWindow used for .ics export windows",
        ],
        title_size=22,
        body_size=17,
    )
    save(img, "database_erd.png")


if __name__ == "__main__":
    draw_architecture()
    draw_workflow()
    draw_erd()
