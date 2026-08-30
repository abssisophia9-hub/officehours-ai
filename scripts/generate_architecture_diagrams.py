#!/usr/bin/env python3
"""Generate OfficeHours AI architecture diagrams (unified product + Canvas era)."""

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


def polyline_arrow(draw, points, color="#475569", width=3):
    for start, end in zip(points, points[1:]):
        arrow(draw, start, end, color=color, width=width)


def label_text(draw, xy, text, color="#1E293B", size=12, bold=False):
    draw.text(xy, text, fill=color, font=font(size, bold=bold))


def draw_layer_band(draw, y0, y1, label, fill, label_color="#0F172A"):
    draw.rectangle((30, y0, 2570, y1), fill=fill, outline="#CBD5E1", width=2)
    draw.text((42, y0 + 8), label, fill=label_color, font=font(15, bold=True))


def save(img: Image.Image, name: str) -> None:
    for out_dir in OUT_DIRS:
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / name
        img.save(path, "PNG")
        print(f"Wrote {path}")


def draw_header(draw, w, title, subtitle, fill="#0A4F34"):
    draw.rectangle((0, 0, w, 132), fill=fill)
    draw.text(
        (48, 28),
        "OfficeHours AI · Al Akhawayn University",
        fill="#A7F3D0",
        font=font(18, bold=True),
    )
    draw.text((48, 60), title, fill="#F8FAFC", font=font(34, bold=True))
    draw.text((48, 104), subtitle, fill="#D1FAE5", font=font(16))


def draw_architecture() -> None:
    w, h = 1800, 1180
    img = Image.new("RGB", (w, h), "#ECFDF5")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "System Architecture (unified product)",
        "One login app · role per course · Canvas launch · Ask Triage · professor KB gate",
    )

    boxes = [
        (
            (50, 170, 560, 370),
            "#FEF3C7",
            "#B45309",
            [
                "officehours-app :5180",
                "Login · course picker",
                "Student / TA / Professor workspaces",
                "Quiet ask · Identify me · meetings",
                "Canvas simulator /launch",
            ],
        ),
        (
            (600, 170, 1140, 370),
            "#DBEAFE",
            "#1D4ED8",
            [
                "FastAPI :8000",
                "Auth sessions · memberships",
                "/requests · /ta · /knowledge · /agent",
                "/canvas/launch · WebSocket /ws",
                "SQLite (Postgres-ready)",
            ],
        ),
        (
            (1180, 170, 1750, 370),
            "#E0E7FF",
            "#4338CA",
            [
                "Canvas LMS (AUI)",
                "Course + role source of truth",
                "LTI launch (prod) / demo stub",
                "Materials sync → course KB",
                "Not AUI portal scraping",
            ],
        ),
        (
            (50, 420, 560, 680),
            "#D1FAE5",
            "#047857",
            [
                "Ask Triage · Analyzer",
                "Embeddings + LogReg",
                "Category · urgency · tags",
                "request_classifier.joblib",
            ],
        ),
        (
            (600, 420, 1140, 680),
            "#A7F3D0",
            "#0F766E",
            [
                "Ask Triage · Matcher",
                "TA assigner + queue blend",
                "Primary / alt TA · wait",
                "matcher_classifier.joblib",
            ],
        ),
        (
            (1180, 420, 1750, 680),
            "#99F6E4",
            "#0F766E",
            [
                "Ask Triage · Synthesizer",
                "Approved-KB RAG + teaching bank",
                "Hint · teaching approach",
                "Weak hit → seek Quiet ask",
            ],
        ),
        (
            (50, 730, 900, 960),
            "#FFF7ED",
            "#EA580C",
            [
                "Professor-in-the-loop",
                "TA resolve → pending_review",
                "Approve / edit / reject KB",
                "Only approved answers → /agent/ask",
            ],
        ),
        (
            (940, 730, 1750, 960),
            "#FFFFFF",
            "#0F172A",
            [
                "Identity model",
                "users · courses · course_memberships",
                "Role is per course (TA can also be student)",
                "help_mode: message | face_to_face | online_meeting",
            ],
        ),
    ]

    for box, fill, outline, lines in boxes:
        rounded_box(draw, box, fill, outline, radius=20, width=3)
        center_text(draw, box, lines, title_size=20, body_size=14)

    arrow(draw, (560, 270), (600, 270), "#334155", 3)
    arrow(draw, (1140, 270), (1180, 270), "#334155", 3)
    arrow(draw, (870, 370), (300, 420), "#047857", 3)
    arrow(draw, (870, 370), (870, 420), "#0F766E", 3)
    arrow(draw, (870, 370), (1450, 420), "#0F766E", 3)
    arrow(draw, (300, 680), (300, 730), "#EA580C", 3)
    arrow(draw, (870, 680), (500, 730), "#EA580C", 3)
    arrow(draw, (1450, 680), (700, 730), "#EA580C", 3)

    draw.text(
        (50, 1000),
        "Legacy ports 5173–5175 are older web shells only (no hardware) — product testing uses :5180.",
        fill="#065F46",
        font=font(16, bold=True),
    )
    draw.text(
        (50, 1040),
        "FYP constraint: OFFICEHOURS_ALLOW_EXTERNAL_LLM=false — Analyzer / Matcher / Synthesizer are custom-trained local models.",
        fill="#334155",
        font=font(15),
    )
    draw.text(
        (50, 1075),
        "Community deploy recommendation: Canvas LTI as enrollment + auth entry; admin manual fix only as escape hatch.",
        fill="#1E3A8A",
        font=font(15, bold=True),
    )
    save(img, "architecture.png")


def draw_workflow() -> None:
    w, h = 1860, 1080
    img = Image.new("RGB", (w, h), "#ECFDF5")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "End-to-End Product Workflow",
        "Identity + help mode → Ask Triage → TA → professor curation → student KB / meetings",
        fill="#0F766E",
    )

    steps = [
        (40, 170, "1. Enter", "Login or Canvas\nlaunch into course"),
        (270, 170, "2. Ask", "Quiet ask OR\nIdentify me"),
        (500, 170, "3. Help mode", "Message · face-to-\nface · online"),
        (730, 170, "4. Analyzer", "Category / urgency\n/ difficulty"),
        (960, 170, "5. Matcher", "Assign TA +\nwait estimate"),
        (1190, 170, "6. Synthesizer", "Hint + teaching\ndraft (or seek help)"),
        (1420, 170, "7. Live push", "WebSocket to\nTA + professor"),
        (1650, 170, "8. Cluster", "Similar topics\nfor group review"),
        (100, 430, "9. TA queue", "See From + Help\nedit draft / resolve"),
        (400, 430, "10. Pending KB", "Entry stays\npending_review"),
        (700, 430, "11. Professor", "Approve / edit /\nreject + Canvas sync"),
        (1000, 430, "12. Approved KB", "Student agent may\nanswer from materials"),
        (1300, 430, "13. Meetings", "Face-to-face / online\nflag for scheduling"),
        (1600, 430, "14. Status", "Student looks up\nrequest code"),
    ]

    for x, y, title, body in steps:
        box = (x, y, x + 200, y + 150)
        rounded_box(draw, box, "#FFFFFF", "#065F46", radius=16, width=2)
        center_text(draw, box, [title, *body.split("\n")], title_size=16, body_size=12)

    for x in (240, 470, 700, 930, 1160, 1390, 1620):
        arrow(draw, (x, 245), (x + 30, 245), "#047857")
    draw.line([(1750, 320), (1750, 380), (200, 380), (200, 430)], fill="#047857", width=3)
    arrow(draw, (200, 415), (200, 430), "#047857")
    for x in (300, 600, 900, 1200, 1500):
        arrow(draw, (x, 505), (x + 30, 505), "#0F766E")

    note = (40, 660, 1820, 1000)
    rounded_box(draw, note, "#FEF3C7", "#B45309", radius=20, width=3)
    center_text(
        draw,
        note,
        [
            "Product rules baked into this flow",
            "Role comes from the active course membership — a TA in CSC 2302 can switch to student mode in MTH 1304.",
            "Anonymous asks never store name/ID. Identified asks require at least one identity field.",
            "Meeting modes override recommended_action so staff know to schedule, not only reply asynchronously.",
            "AI drafts help — professors still approve what the student KB agent can retrieve.",
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
        "Ask Triage Multi-Agent Design",
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
                "CSC topic overlays",
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
                "Expertise / queue blend",
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
                "CSC teaching-bank rows",
                "Out: student_hint,",
                "teaching_approach / seek-help",
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
            "Learning-style classifier defaults to ML; tests may use lexical clustering",
            "Labels are synthetic / silver / curated for the FYP — not private student transcripts",
            "Quality ceiling = course KB coverage + labeled CSC topics (see docs/agent_performance.md)",
        ],
        title_size=20,
        body_size=16,
    )
    save(img, "oracle_agents.png")


def draw_product_deployment() -> None:
    w, h = 1700, 1080
    img = Image.new("RGB", (w, h), "#FFFBEB")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Community Deployment Model",
        "What to ship for AUI — and what not to build first",
        fill="#92400E",
    )

    boxes = [
        (
            (60, 180, 560, 480),
            "#DCFCE7",
            "#15803D",
            [
                "Optimal: Canvas LTI",
                "Open from Canvas course",
                "JIT account + membership",
                "Role from Canvas enrollment",
                "Materials via Canvas API",
                "TA can also be student",
            ],
        ),
        (
            (600, 180, 1100, 480),
            "#FEE2E2",
            "#B91C1C",
            [
                "Not primary: AUI portal",
                "No JICS/SIS code today",
                "Slow campus IT projects",
                "Canvas already mirrors",
                "enrollments for teaching",
                "Defer unless IT requires",
            ],
        ),
        (
            (1140, 180, 1640, 480),
            "#FEF3C7",
            "#B45309",
            [
                "Support only: manual",
                "Admin fix for bad rows",
                "Not how the community",
                "enrolls day-to-day",
                "No public self-serve",
                "course typing at login",
            ],
        ),
        (
            (60, 530, 820, 980),
            "#DBEAFE",
            "#1D4ED8",
            [
                "What ships in the FYP package",
                "Unified web app + FastAPI",
                "Demo seed (aui-demo) for local tests",
                "Canvas launch simulator + stub",
                "Quiet ask / Identify / meetings",
                "Ask Triage + Help Coach + KB gate",
                "Next: real LTI 1.3 signatures",
            ],
        ),
        (
            (880, 530, 1640, 980),
            "#FFEDD5",
            "#C2410C",
            [
                "Still not (and OK for now)",
                "Not App Store / Play Store",
                "Not native desktop installer",
                "Not auto-publish unapproved FAQ",
                "Demo launch is unsigned (unsafe",
                "until LTI lands for production)",
            ],
        ),
    ]
    for box, fill, outline, lines in boxes:
        rounded_box(draw, box, fill, outline, radius=20, width=3)
        center_text(draw, box, lines, title_size=20, body_size=15)
    save(img, "product_deployment.png")


def draw_erd() -> None:
    w, h = 1800, 1180
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Database Entity-Relationship Diagram",
        "Auth · memberships · requests (help_mode) · KB · Ask Triage · TA roster",
        fill="#1E3A8A",
    )

    entities = [
        (
            (40, 170, 360, 420),
            "#FEF3C7",
            "#B45309",
            [
                "users",
                "id PK",
                "email UNIQUE",
                "password_hash",
                "display_name",
                "student_id",
                "is_active",
            ],
        ),
        (
            (400, 170, 720, 400),
            "#DBEAFE",
            "#1D4ED8",
            [
                "courses",
                "id PK",
                "code / title / term",
                "canvas_course_id",
                "is_active",
            ],
        ),
        (
            (760, 170, 1140, 430),
            "#D1FAE5",
            "#047857",
            [
                "course_memberships",
                "id PK",
                "course_id FK",
                "user_id FK",
                "role: student|ta|professor",
                "UNIQUE(course, user)",
            ],
        ),
        (
            (1180, 170, 1760, 520),
            "#FFEDD5",
            "#C2410C",
            [
                "requests",
                "id PK · text · anonymous",
                "student_id / student_name",
                "help_mode (message|f2f|online)",
                "category / urgency / style",
                "cluster_id / recommended_action",
                "oracle_* / assigned_ta",
                "course_id FK · created_at",
            ],
        ),
        (
            (40, 480, 400, 740),
            "#E0E7FF",
            "#4338CA",
            [
                "knowledge_entries",
                "id PK · status",
                "question / answer_draft",
                "student_hint · course_id",
                "source_request_id FK",
            ],
        ),
        (
            (440, 480, 760, 700),
            "#FCE7F3",
            "#BE185D",
            [
                "ta_roster",
                "name UNIQUE",
                "expertise_tags",
                "queue_depth",
                "is_available",
            ],
        ),
        (
            (800, 500, 1140, 720),
            "#ECFEFF",
            "#0891B2",
            [
                "auth_sessions",
                "token UNIQUE",
                "user_id FK",
                "expires_at",
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

    arrow(draw, (360, 280), (400, 280), "#1D4ED8")
    arrow(draw, (720, 280), (760, 280), "#047857")
    draw.text((370, 240), "N:M via", fill="#1E3A8A", font=font(14, bold=True))
    arrow(draw, (950, 430), (1300, 520), "#C2410C")
    draw.text((980, 450), "asks in course", fill="#9A3412", font=font(14, bold=True))

    note = (40, 800, 1760, 1100)
    rounded_box(draw, note, "#ECFEFF", "#0891B2", radius=18, width=3)
    center_text(
        draw,
        note,
        [
            "Key runtime paths",
            "Login / Canvas launch → memberships decide workspace role for the active course",
            "POST /requests → Ask Triage → Request + pending KnowledgeEntry + WS broadcast (help_mode preserved)",
            "POST /ta/resolve → notes; professor PATCH /knowledge/{id} publishes to /agent/ask",
            "Same user may hold ta in one course and student in another — never two roles in one course",
        ],
        title_size=20,
        body_size=15,
        title_color="#155E75",
    )
    save(img, "database_erd.png")


def draw_canvas_enrollment() -> None:
    w, h = 1700, 1000
    img = Image.new("RGB", (w, h), "#EFF6FF")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Canvas Enrollment & Dual Roles",
        "One person · many courses · one role per course · JIT provision",
        fill="#1D4ED8",
    )

    steps = [
        (60, 180, "Canvas course", "User already enrolled\nin LMS as student/TA/\nteacher"),
        (380, 180, "Open tool", "Click OfficeHours AI\n(LTI in prod; /canvas-\ndemo locally)"),
        (700, 180, "Launch payload", "email · canvas_course_id\n· Canvas role"),
        (1020, 180, "Upsert", "User + Course +\nmembership.role"),
        (1340, 180, "Workspace", "Land in student / TA /\nprofessor for THAT course"),
    ]
    for x, y, title, body in steps:
        box = (x, y, x + 280, y + 180)
        rounded_box(draw, box, "#FFFFFF", "#1D4ED8", radius=16, width=2)
        center_text(draw, box, [title, *body.split("\n")], title_size=18, body_size=13)
    for x in (340, 660, 980, 1300):
        arrow(draw, (x, 270), (x + 40, 270), "#1D4ED8")

    left = (60, 420, 820, 900)
    right = (880, 420, 1640, 900)
    rounded_box(draw, left, "#D1FAE5", "#047857", radius=20, width=3)
    center_text(
        draw,
        left,
        [
            "Example: Alice / Karim",
            "CSC 2302 → role = ta",
            "CSC 3323 → role = student",
            "MTH 1304 → role = student",
            "",
            "Course picker switches workspace",
            "with the membership role",
        ],
        title_size=22,
        body_size=16,
        title_color="#065F46",
    )
    rounded_box(draw, right, "#FEF3C7", "#B45309", radius=20, width=3)
    center_text(
        draw,
        right,
        [
            "Why not portal / manual?",
            "Canvas already has the roster",
            "and teaching materials",
            "",
            "Portal sync = slow IT project",
            "Manual entry ≠ community scale",
            "",
            "Admin tools = exception handling",
        ],
        title_size=22,
        body_size=16,
        title_color="#92400E",
    )
    save(img, "canvas_enrollment.png")


def draw_project_journey() -> None:
    w, h = 1800, 980
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)
    draw_header(
        draw,
        w,
        "Project Journey — Day 1 → This Upgrade",
        "From proposal kiosk to Canvas-ready multi-role campus product",
        fill="#0F172A",
    )

    phases = [
        (50, 180, "#FEF3C7", "#B45309", "0 Proposal", "Problem + scope\nkiosk idea"),
        (300, 180, "#DBEAFE", "#1D4ED8", "1 API + kiosk", "FastAPI CRUD\nstudent submit"),
        (550, 180, "#E0E7FF", "#4338CA", "2 Professor AI", "Classify · cluster\ncards · actions"),
        (800, 180, "#D1FAE5", "#047857", "3 Ask Triage + TA", "3 agents · KB gate\nWebSocket live"),
        (1050, 180, "#A7F3D0", "#0F766E", "4 One app", "Login · courses\nrole per course"),
        (1300, 180, "#99F6E4", "#0F766E", "5 AUI + Canvas", "Catalog codes\nlaunch · materials"),
        (1550, 180, "#FFEDD5", "#C2410C", "6 This upgrade", "Identity · meetings\nTA+student · docs"),
    ]
    for x, y, fill, outline, title, body in phases:
        box = (x, y, x + 220, y + 200)
        rounded_box(draw, box, fill, outline, radius=16, width=3)
        center_text(draw, box, [title, *body.split("\n")], title_size=17, body_size=13)
    for x in (270, 520, 770, 1020, 1270, 1520):
        arrow(draw, (x, 280), (x + 30, 280), "#334155")

    bottom = (50, 440, 1750, 900)
    rounded_box(draw, bottom, "#FFFFFF", "#0F172A", radius=20, width=3)
    center_text(
        draw,
        bottom,
        [
            "Where we are now",
            "Packaged multi-role web product for AUI demos and FYP evaluation",
            "Community path locked: Canvas LTI (finish signatures) — not portal, not manual enrollment",
            "Agents next: more CSC-covered labels + richer course KB (see docs/agent_performance.md)",
            "Full narrative: docs/project_journey.md",
        ],
        title_size=24,
        body_size=17,
    )
    save(img, "project_journey.png")


def draw_platform_architecture() -> None:
    """Single-page OfficeHours platform architecture (all layers + flows)."""
    w, h = 2600, 1680
    img = Image.new("RGB", (w, h), "#F8FAFC")
    draw = ImageDraw.Draw(img)

    # Header
    draw.rectangle((0, 0, w, 110), fill="#0A4F34")
    draw.text(
        (48, 22),
        "OfficeHours Platform — Complete Architecture",
        fill="#F8FAFC",
        font=font(36, bold=True),
    )
    draw.text(
        (48, 72),
        "Peer help + AI study agent · Canvas LMS sync · role-based access · real-time Rooms",
        fill="#A7F3D0",
        font=font(17),
    )

    # Role legend (left rail)
    role_box = (30, 130, 250, 320)
    rounded_box(draw, role_box, "#FFFFFF", "#64748B", radius=14, width=2)
    center_text(
        draw,
        role_box,
        [
            "User roles",
            "Student → Agent + Rooms",
            "TA → Moderation + queue",
            "Professor → Sync + policy",
            "Role per course membership",
        ],
        title_size=16,
        body_size=13,
    )

    # ── Layer 1: Frontend ──────────────────────────────────────────────
    draw_layer_band(draw, 130, 360, "LAYER 1 · FRONTEND", "#FEF9C3", "#854D0E")
    frontend_boxes = [
        (
            (280, 170, 640, 330),
            "#FDE68A",
            "#B45309",
            [
                "Web Dashboard",
                "(Student view)",
                "Study Agent · Rooms",
                "Anonymous or named posts",
            ],
        ),
        (
            (680, 170, 1040, 330),
            "#FDE68A",
            "#B45309",
            [
                "Web Dashboard",
                "(TA view)",
                "Moderate Rooms",
                "Queue · Help Coach",
            ],
        ),
        (
            (1080, 170, 1440, 330),
            "#FDE68A",
            "#B45309",
            [
                "Web Dashboard",
                "(Professor view)",
                "Canvas sync · KB gate",
                "Set course boundaries",
            ],
        ),
        (
            (1480, 170, 1840, 330),
            "#FEF3C7",
            "#D97706",
            [
                "Canvas LMS",
                "Integration Point",
                "OAuth / LTI launch",
                "Course + role handoff",
            ],
        ),
    ]
    for box, fill, outline, lines in frontend_boxes:
        rounded_box(draw, box, fill, outline, radius=16, width=2)
        center_text(draw, box, lines, title_size=17, body_size=13)

    draw.text(
        (1880, 200),
        "officehours-app :5180",
        fill="#92400E",
        font=font(14, bold=True),
    )
    draw.text(
        (1880, 228),
        "Unified SPA · REST + WebSocket",
        fill="#78350F",
        font=font(13),
    )

    # ── Layer 2: API & Auth ────────────────────────────────────────────
    draw_layer_band(draw, 380, 560, "LAYER 2 · API & AUTHENTICATION", "#DBEAFE", "#1E40AF")
    api_boxes = [
        (
            (280, 420, 780, 540),
            "#BFDBFE",
            "#1D4ED8",
            [
                "API Gateway / Server",
                "FastAPI :8000",
                "/requests · /agent · /help-room",
                "/knowledge · /canvas · /ta",
            ],
        ),
        (
            (820, 420, 1420, 540),
            "#93C5FD",
            "#1E3A8A",
            [
                "Authentication & Authorization",
                "AUI email login · Microsoft SSO",
                "RBAC: student · TA · professor",
                "Bearer sessions · course scope",
            ],
        ),
        (
            (1460, 420, 1960, 540),
            "#BFDBFE",
            "#1D4ED8",
            [
                "WebSocket Server",
                "WS /ws · real-time hub",
                "Live Rooms + queue events",
                "TA / professor dashboards",
            ],
        ),
    ]
    for box, fill, outline, lines in api_boxes:
        rounded_box(draw, box, fill, outline, radius=16, width=2)
        center_text(draw, box, lines, title_size=16, body_size=13)

    # Frontend → API arrows
    for x in (460, 860, 1260):
        arrow(draw, (x, 330), (x, 420), "#334155", 2)
    arrow(draw, (1660, 330), (1100, 420), "#D97706", 2)
    label_text(draw, (1680, 350), "⑥ OAuth → role", color="#B45309", size=12, bold=True)

    # ── Layer 3: Core Services ─────────────────────────────────────────
    draw_layer_band(draw, 580, 860, "LAYER 3 · CORE SERVICES", "#D1FAE5", "#047857")
    service_boxes = [
        (
            (280, 620, 620, 820),
            "#A7F3D0",
            "#059669",
            [
                "Study Agent Service",
                "LLM answers from syllabus ONLY",
                "ISOLATED per course",
                "No other students' notes",
            ],
        ),
        (
            (660, 620, 1000, 820),
            "#6EE7B7",
            "#047857",
            [
                "Study Rooms Service",
                "P2P forum · chapters",
                "anonymity flag on posts",
                "problem · discussion · article",
            ],
        ),
        (
            (1040, 620, 1380, 820),
            "#A7F3D0",
            "#059669",
            [
                "Rating / Credibility",
                "Upvote · downvote · helpful",
                "Stack Overflow-style ranks",
                "Node Points · ROOMS score",
            ],
        ),
        (
            (1420, 620, 1760, 820),
            "#6EE7B7",
            "#047857",
            [
                "Module Sync Engine",
                "Pull Canvas modules",
                "→ Rooms chapter grid",
                "→ Study Agent context",
            ],
        ),
        (
            (1800, 620, 2140, 820),
            "#A7F3D0",
            "#059669",
            [
                "Moderation Service",
                "TA: flag / filter spam",
                "Professor: set boundaries",
                "Sensitive-topic guardrails",
            ],
        ),
    ]
    for box, fill, outline, lines in service_boxes:
        rounded_box(draw, box, fill, outline, radius=16, width=2)
        center_text(draw, box, lines, title_size=15, body_size=12)

    # API → services
    arrow(draw, (530, 540), (450, 620), "#334155", 2)
    arrow(draw, (1120, 540), (830, 620), "#334155", 2)
    arrow(draw, (1120, 540), (1210, 620), "#334155", 2)
    arrow(draw, (1710, 540), (1580, 620), "#334155", 2)
    arrow(draw, (1710, 540), (1970, 620), "#334155", 2)

    # Flow labels on service layer
    label_text(draw, (700, 585), "① post question", color="#065F46", size=12, bold=True)
    label_text(draw, (320, 585), "② ask agent", color="#065F46", size=12, bold=True)
    label_text(draw, (1100, 585), "③ rate answer", color="#065F46", size=12, bold=True)
    label_text(draw, (1480, 585), "⑤ professor sync", color="#065F46", size=12, bold=True)
    label_text(draw, (1860, 585), "④ TA moderate", color="#065F46", size=12, bold=True)

    # Isolation callout for Study Agent
    iso = (280, 830, 620, 900)
    rounded_box(draw, iso, "#ECFDF5", "#059669", radius=12, width=2)
    center_text(
        draw,
        iso,
        ["Course-isolated context", "Cannot access other courses or peer notes"],
        title_size=13,
        body_size=12,
        title_color="#047857",
    )

    # ── Layer 4: Data ────────────────────────────────────────────────────
    draw_layer_band(draw, 920, 1140, "LAYER 4 · DATA LAYER (SQLite / Postgres-ready)", "#EDE9FE", "#5B21B6")
    data_boxes = [
        (
            (280, 960, 600, 1100),
            "#DDD6FE",
            "#6D28D9",
            ["Course Database", "Synced from Canvas", "modules · metadata"],
        ),
        (
            (640, 960, 960, 1100),
            "#DDD6FE",
            "#6D28D9",
            ["User Database", "students · TAs · professors", "roles · permissions"],
        ),
        (
            (1000, 960, 1320, 1100),
            "#C4B5FD",
            "#5B21B6",
            ["Study Rooms Database", "posts · replies · votes", "anonymity flags"],
        ),
        (
            (1360, 960, 1680, 1100),
            "#DDD6FE",
            "#6D28D9",
            ["Study Agent Context Store", "professor-approved syllabus", "approved KB chunks only"],
        ),
        (
            (1720, 960, 2040, 1100),
            "#C4B5FD",
            "#5B21B6",
            ["User Profiles", "display name · student ID", "anonymous or named option"],
        ),
    ]
    for box, fill, outline, lines in data_boxes:
        rounded_box(draw, box, fill, outline, radius=14, width=2)
        center_text(draw, box, lines, title_size=14, body_size=12)

    # Service → database arrows (color-coded, minimal crossing)
    db_links = [
        ((450, 820), (440, 960), "#059669"),  # Study Agent → context store
        ((830, 820), (1160, 960), "#047857"),  # Rooms → rooms DB
        ((1210, 820), (1160, 960), "#047857"),  # Rating → rooms DB
        ((1580, 820), (440, 960), "#047857"),  # Sync → course DB
        ((1580, 820), (1520, 960), "#047857"),  # Sync → context store
        ((1970, 820), (1160, 960), "#047857"),  # Moderation → rooms DB
        ((1120, 540), (800, 960), "#1D4ED8"),  # Auth → user DB
        ((1120, 540), (1880, 960), "#1D4ED8"),  # Auth → profiles
    ]
    for start, end, color in db_links:
        arrow(draw, start, end, color, 2)

    # ── Layer 5: External ────────────────────────────────────────────────
    draw_layer_band(draw, 1160, 1340, "LAYER 5 · EXTERNAL INTEGRATIONS", "#F1F5F9", "#475569")
    ext_boxes = [
        (
            (400, 1200, 900, 1310),
            "#E2E8F0",
            "#334155",
            [
                "Canvas LMS",
                "OAuth / LTI · course sync",
                "user enrollment · modules API",
            ],
        ),
        (
            (980, 1200, 1480, 1310),
            "#FEE2E2",
            "#DC2626",
            [
                "LLM Provider",
                "Claude / GPT API",
                "Study Agent inference",
                "(external LLM optional)",
            ],
        ),
        (
            (1560, 1200, 2060, 1310),
            "#E0F2FE",
            "#0284C7",
            [
                "Email Service",
                "AUI authentication identity",
                "notifications (planned)",
            ],
        ),
    ]
    for box, fill, outline, lines in ext_boxes:
        rounded_box(draw, box, fill, outline, radius=14, width=2)
        center_text(draw, box, lines, title_size=15, body_size=13)

    # External ↔ platform
    arrow(draw, (650, 1200), (1660, 330), "#475569", 2)
    arrow(draw, (650, 1200), (1580, 620), "#475569", 2)
    arrow(draw, (650, 1200), (440, 960), "#475569", 2)
    label_text(draw, (700, 1175), "Canvas sync + OAuth", color="#334155", size=12, bold=True)

    arrow(draw, (450, 820), (1230, 1200), "#DC2626", 2)
    label_text(draw, (820, 1120), "② queries syllabus only", color="#B91C1C", size=12, bold=True)

    arrow(draw, (1120, 540), (1810, 1200), "#0284C7", 2)
    label_text(draw, (1500, 1155), "AUI email identity", color="#0369A1", size=12, bold=True)

    # ── Key highlights footer ────────────────────────────────────────────
    footer = (30, 1360, 2570, 1650)
    rounded_box(draw, footer, "#FFFFFF", "#0F172A", radius=18, width=3)
    draw.text((52, 1380), "Key architecture highlights", fill="#0F172A", font=font(20, bold=True))

    highlights = [
        ("✓", "Study Agent isolated from peer help and other courses — syllabus context store only"),
        ("✓", "Study Rooms support anonymity flag; TA moderation authority; professor policy boundaries"),
        ("✓", "Real-time WebSocket for live Rooms and staff dashboards"),
        ("✓", "Canvas is external dependency for auth handoff, enrollment, and module sync"),
        ("✓", "Rating/credibility system feeds Stack Overflow-style reputation in Rooms"),
        ("✓", "Each service owns distinct data concerns (course · users · rooms · KB context · profiles)"),
    ]
    y = 1420
    for mark, text in highlights:
        draw.text((60, y), mark, fill="#059669", font=font(16, bold=True))
        draw.text((90, y), text, fill="#334155", font=font(14))
        y += 36

    # Data flow legend (right side of footer)
    flow_box = (1480, 1380, 2540, 1630)
    rounded_box(draw, flow_box, "#F0FDF4", "#059669", radius=14, width=2)
    draw.text((1500, 1395), "Numbered data flows", fill="#047857", font=font(17, bold=True))
    flows = [
        "① Student posts question → Study Rooms Service → Rooms DB",
        "② Student asks Study Agent → Context Store (syllabus only) → LLM → answer",
        "③ Student upvotes/rates → Rating/Credibility → Rooms DB",
        "④ TA moderates Rooms → Moderation Service filters content",
        "⑤ Professor syncs Canvas → Module Sync → chapters + agent context",
        "⑥ Canvas OAuth/LTI → Auth Service → role assignment (student/TA/professor)",
    ]
    fy = 1435
    for line in flows:
        draw.text((1510, fy), line, fill="#1E293B", font=font(13))
        fy += 30

    save(img, "platform_architecture.png")


if __name__ == "__main__":
    draw_platform_architecture()
    draw_architecture()
    draw_workflow()
    draw_oracle_agents()
    draw_product_deployment()
    draw_erd()
    draw_canvas_enrollment()
    draw_project_journey()
