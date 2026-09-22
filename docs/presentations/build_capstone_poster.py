#!/usr/bin/env python3
"""Fill the official SSE Capstone poster template and embed technical figures."""

from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
TPL = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "CSC_Capstone_Early_Stage_Proposal_Poster_Template__1__f6a3.docx"
)
OUT_DIR = Path(__file__).resolve().parent
FIG_DIR = OUT_DIR / "poster_figures"
REPO_URL = "https://github.com/abssisophia9-hub/officehours-ai"

GREEN = "#006633"
GREEN_DK = "#004B2B"
INK = "#1A211F"
MUTED = "#3E4744"
LINE = "#9AA6A1"
PAPER = "#FFFFFF"
SAND = "#F4F7F5"
GOLD = "#FFF6D8"
BLUE = "#E7F0FF"
MINT = "#E4F6EE"
PEACH = "#FFE8D4"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    )
    return ImageFont.truetype(path, size)


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=LINE, radius=14, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_w(draw, s, f):
    b = draw.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


def draw_center(draw, box, lines, title_size=18, body_size=13, title=INK, body=MUTED):
    x0, y0, x1, y1 = box
    tf, bf = font(title_size, True), font(body_size)
    heights = []
    for i, line in enumerate(lines):
        f = tf if i == 0 else bf
        heights.append(text_w(draw, line, f)[1])
    total = sum(heights) + 4 * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) // 2
    for i, line in enumerate(lines):
        f = tf if i == 0 else bf
        color = title if i == 0 else body
        w, h = text_w(draw, line, f)
        draw.text((x0 + (x1 - x0 - w) // 2, y), line, fill=color, font=f)
        y += h + 4


def arrow_h(draw, x0, y, x1, color=GREEN_DK):
    draw.line([(x0, y), (x1 - 10, y)], fill=color, width=3)
    draw.polygon([(x1, y), (x1 - 12, y - 6), (x1 - 12, y + 6)], fill=color)


def save(img: Image.Image, name: str) -> Path:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    path = FIG_DIR / name
    img.save(path, "PNG")
    return path


def fig_gap() -> Path:
    w, h = 1180, 300
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 36), fill=GREEN)
    d.text((16, 8), "Gap map  ·  existing campus help vs OfficeHours AI", fill="white", font=font(16, True))

    headers = ["Capability", "LMS inbox / Piazza / chatbot", "OfficeHours AI (proposed)"]
    rows = [
        ("Routing", "Manual, first-come, or untyped", "Ask Triage: MiniLM + LogisticRegression"),
        ("TA staffing", "No dual-TA match / queue model", "Matcher + queue penalty + dual-TA roster"),
        ("Student AI", "Unconstrained LLM / FAQ dump", "Study Agent quotes only stamped KB"),
        ("Ask barrier", "Public post or email only", "Quiet ask → private My asks reply"),
    ]
    cols = [210, 470, 500]
    y = 48
    x = 0
    hf, rf, bf = font(13, True), font(13), font(13, True)
    for i, head in enumerate(headers):
        fill = GREEN_DK if i == 2 else SAND
        color = "white" if i == 2 else INK
        d.rectangle((x, y, x + cols[i], y + 32), fill=fill, outline=LINE)
        d.text((x + 8, y + 8), head, fill=color, font=hf)
        x += cols[i]
    y = 80
    for r, row in enumerate(rows):
        x = 0
        bg = PAPER if r % 2 == 0 else SAND
        for i, cell in enumerate(row):
            d.rectangle((x, y, x + cols[i], y + 50), fill=MINT if i == 2 else bg, outline=LINE)
            f = bf if i == 0 or i == 2 else rf
            d.text((x + 8, y + 16), cell, fill=INK, font=f)
            x += cols[i]
        y += 50
    return save(img, "fig_gap.png")


def fig_architecture() -> Path:
    w, h = 1180, 310
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 32), fill=GREEN)
    d.text((14, 7), "Proposed architecture  ·  unified app + local Ask Triage + Canvas LTI", fill="white", font=font(15, True))

    boxes = [
        (16, 46, 384, 148, GOLD, ["officehours-app :5180", "React / Vite / Tailwind", "Student · TA · Professor"]),
        (406, 46, 774, 148, BLUE, ["FastAPI :8000", "Auth · requests · ta · lti", "WebSocket  ·  SQLite→Postgres"]),
        (796, 46, 1164, 148, MINT, ["Canvas LMS (AUI)", "LTI 1.3 + REST modules", "Materials → KB  ·  no scrape"]),
    ]
    for x0, y0, x1, y1, fill, lines in boxes:
        rounded(d, (x0, y0, x1, y1), fill, GREEN_DK, 14)
        draw_center(d, (x0, y0, x1, y1), lines, 15, 12)
    arrow_h(d, 384, 97, 406)
    arrow_h(d, 774, 97, 796)

    agents = [
        (16, 164, 300, 294, GOLD, ["Analyzer", "MiniLM + LogReg", "request_classifier.joblib"]),
        (322, 164, 606, 294, BLUE, ["Matcher", "TA + queue blend", "matcher_classifier.joblib"]),
        (628, 164, 912, 294, MINT, ["Synthesizer", "Approved-KB RAG", "synthesizer_ranker.joblib"]),
        (934, 164, 1164, 294, PEACH, ["Professor stamp", "Only stamped KB", "reaches Study Agent"]),
    ]
    for x0, y0, x1, y1, fill, lines in agents:
        rounded(d, (x0, y0, x1, y1), fill, GREEN_DK, 14)
        draw_center(d, (x0, y0, x1, y1), lines, 14, 12)
    return save(img, "fig_architecture.png")


def fig_roadmap() -> Path:
    w, h = 1180, 250
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 36), fill=GREEN)
    d.text((16, 8), "Work plan  ·  five staged phases  (demo → live Canvas)", fill="white", font=font(16, True))
    phases = [
        ("1", "Triage + roles", "Ask path, auth,\ncourse membership"),
        ("2", "TA + KB gate", "Queue, Help Coach,\nprofessor stamp"),
        ("3", "Rooms + demo", "Forum + local\nCanvas mirror"),
        ("4", "LTI live", "Signed LTI 1.3 +\nmodule sync"),
        ("5", "Scale path", "Postgres host +\nStrategist grades"),
    ]
    gap = 18
    bw = (w - 40 - gap * 4) // 5
    y0, y1 = 56, 230
    for i, (n, title, body) in enumerate(phases):
        x0 = 20 + i * (bw + gap)
        x1 = x0 + bw
        rounded(d, (x0, y0, x1, y1), SAND if i < 3 else GOLD, GREEN_DK, 16)
        d.ellipse((x0 + bw // 2 - 16, y0 + 12, x0 + bw // 2 + 16, y0 + 44), fill=GREEN)
        tw, th = text_w(d, n, font(16, True))
        d.text((x0 + bw // 2 - tw / 2, y0 + 16), n, fill="white", font=font(16, True))
        draw_center(d, (x0 + 8, y0 + 48, x1 - 8, y1 - 8), [title, *body.split("\n")], 15, 12)
        if i < 4:
            arrow_h(d, x1 + 1, (y0 + y1) // 2, x1 + gap - 1)
    return save(img, "fig_roadmap.png")


def fig_pipeline() -> Path:
    w, h = 1180, 230
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 36), fill=GREEN)
    d.text((16, 8), "Ask pipeline  ·  local models at intake  ·  professor stamp before student AI", fill="white", font=font(15, True))
    steps = [
        (GOLD, ["Ask", "Quiet / identified", "help mode"]),
        (BLUE, ["Analyzer", "category · urgency", "difficulty · ETA"]),
        (BLUE, ["Matcher", "primary / alt TA", "queue wait"]),
        (MINT, ["Synthesizer", "hint + approach", "or seek-help"]),
        (PEACH, ["TA desk", "queue + Help Coach", "claim / reply"]),
        (PEACH, ["Professor", "stamp / edit KB", "cluster review"]),
        (MINT, ["Study Agent", "approved KB only", "/agent/ask"]),
    ]
    gap = 8
    bw = (w - 24 - gap * 6) // 7
    for i, (fill, lines) in enumerate(steps):
        x0 = 12 + i * (bw + gap)
        rounded(d, (x0, 56, x0 + bw, 210), fill, GREEN_DK, 12)
        draw_center(d, (x0 + 4, 56, x0 + bw - 4, 210), lines, 14, 11)
        if i < 6:
            arrow_h(d, x0 + bw + 1, 133, x0 + bw + gap - 1)
    return save(img, "fig_pipeline.png")


def fig_evaluation() -> Path:
    w, h = 1180, 250
    img = Image.new("RGB", (w, h), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, w, 36), fill=GREEN)
    d.text((16, 8), "Evaluation framework  ·  no unverified campus performance claims", fill="white", font=font(15, True))
    cards = [
        (BLUE, ["pytest + CI", "API / auth / KB gate", "regression on demo path"]),
        (GOLD, ["Triage holdouts", "category / routing", "cite metrics carefully"]),
        (MINT, ["Gold-label TA lab", "human labels on asks", "docs/gold_label_lab.md"]),
        (PEACH, ["Role walkthroughs", "student · TA · professor", "task completion"]),
        (SAND, ["Live Canvas check", "LTI launch + sync", "one AUI test course"]),
    ]
    gap = 14
    bw = (w - 24 - gap * 4) // 5
    for i, (fill, lines) in enumerate(cards):
        x0 = 12 + i * (bw + gap)
        rounded(d, (x0, 56, x0 + bw, 230), fill, GREEN_DK, 14)
        draw_center(d, (x0 + 6, 56, x0 + bw - 6, 230), lines, 14, 12)
    return save(img, "fig_evaluation.png")


def fig_qr() -> Path:
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(REPO_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color=GREEN_DK, back_color="white").convert("RGB")
    img = img.resize((400, 400), Image.Resampling.NEAREST)
    return save(img, "fig_qr.png")


def inches_emu(inches: float) -> int:
    return int(inches * 914400)


def drawing_xml(rid: str, name: str, width_in: float, height_in: float, doc_id: int) -> str:
    cx, cy = inches_emu(width_in), inches_emu(height_in)
    return (
        f'<w:r><w:drawing><wp:inline xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        f'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<wp:extent cx="{cx}" cy="{cy}"/><wp:docPr id="{doc_id}" name="{name}"/>'
        f'<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
        f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        f'<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
        f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        f'<a:prstGeom prst="rect"/></pic:spPr></pic:pic></a:graphicData></a:graphic>'
        f"</wp:inline></w:drawing></w:r>"
    )


def figure_paragraph(rid: str, name: str, width_in: float, height_in: float, doc_id: int) -> str:
    return (
        '<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
        + drawing_xml(rid, name, width_in, height_in, doc_id)
        + "</w:p>"
    )


def fill_docx(figures: dict[str, Path]) -> Path:
    work = Path("/tmp/poster_professional")
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    with zipfile.ZipFile(TPL) as z:
        z.extractall(work)

    shutil.copyfile(figures["qr"], work / "word" / "media" / "image1.png")

    media = work / "word" / "media"
    # Display inches (keep one-page SSE template). Source PNGs stay high-res.
    rels = {
        "gap": ("rId11", "image3.png", figures["gap"], 6.15, 0.58, 3),
        "arch": ("rId12", "image4.png", figures["arch"], 6.15, 0.72, 4),
        "road": ("rId13", "image5.png", figures["road"], 6.15, 0.50, 5),
        "pipe": ("rId14", "image6.png", figures["pipe"], 6.15, 0.52, 6),
        "eval": ("rId15", "image7.png", figures["eval"], 6.15, 0.52, 7),
    }
    for _key, (rid, fname, src, *_rest) in rels.items():
        shutil.copyfile(src, media / fname)

    rels_path = work / "word" / "_rels" / "document.xml.rels"
    rel_xml = rels_path.read_text(encoding="utf-8")
    extras = "".join(
        f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{fname}"/>'
        for rid, fname, *_ in rels.values()
    )
    rel_xml = rel_xml.replace("</Relationships>", extras + "</Relationships>")
    rels_path.write_text(rel_xml, encoding="utf-8")

    xml_path = work / "word" / "document.xml"
    xml = xml_path.read_text(encoding="utf-8")

    once = {
        "[PROJECT TITLE: Clear, Specific, and Technically Descriptive]":
            "OfficeHours AI: Multi-Role Campus Office-Hours Triage with Local NLP and Canvas Integration",
        "Student Name(s): [Name(s)]   |   Degree: [Program]   |   Project Type:  ☐ Software Development   ☐ Research-Based":
            "Student Name(s): Sophia Abssi   |   Degree: B.Sc. Computer Science (SSE)   |   Project Type:  ☑ Software Development   ☐ Research-Based",
        "Supervisor: [Name]   |   Co-Supervisor / Client: [If applicable]   |   Stage: Early Proposal   |   Date: [Month Year]":
            "Supervisor: TBD (Capstone Supervisor)   |   Co-Supervisor / Client: AUI Canvas LMS   |   Stage: Early Proposal   |   Date: Sep 2026",
        "Replace with QR":
            "Repository",
        "Proposal • Repository • Supporting Material":
            "github.com/abssisophia9-hub/officehours-ai",

        "Use 3–4 concise sentences: the problem, why it matters, the proposed idea, and the expected contribution. Do not report final results.":
            "Finals-week ask overload floods email and Canvas. OfficeHours AI triages asks, staffs TAs, and lets professors stamp the only answers the Study Agent may quote—local NLP, Canvas-first, not an unconstrained chatbot.",
        "Context / application area: [Where, for whom, and why the problem matters]":
            "Context / application area: AUI courses; students, TAs, and professors during peak academic support demand.",
        "Proposed idea: [System, method, model, experiment, or prototype]":
            "Proposed idea: React SPA + FastAPI with Ask Triage, Help Coach, professor-stamped Study Agent, Rooms, and Canvas LTI 1.3 / REST sync.",
        "Expected contribution: [What the project aims to improve, investigate, or demonstrate]":
            "Expected contribution: Course-scoped triage, dual-TA staffing, KB approval gate, and a demo→live Canvas path.",

        "Define the need before the solution. Use evidence, stakeholder needs, or a research question to justify the project.":
            "Students need a lower barrier to ask; staff need less repeat load; faculty must remain the gate on AI-facing answers.",
        "Problem statement / research question: [1–2 precise sentences]":
            "Problem statement / research question: How can campus office hours cut repeat load and ask friction while keeping professors in control of AI answers?",
        "Stakeholders / intended users: [Who is affected or expected to benefit?]":
            "Stakeholders / intended users: Students (Quiet ask, Study Agent, Strategist, Rooms); TAs (Live Queue, Help Coach); Professors (Repeated Topics, KB stamp, Canvas sync).",
        "Evidence, scope &amp; constraints: [Need evidence and project boundaries]":
            "Evidence, scope &amp; constraints: Silver/synthetic FYP labels; local ML by default; live Canvas needs IT credentials + HTTPS. No portal scraping; no unconstrained LLM backend.",

        "Summarize the most relevant prior work and identify the gap the proposal will address.":
            "LMS inboxes and Piazza/Ed-style forums lack local triage ML, dual-TA matching, and a professor stamp before student-facing AI.",
        "Existing work / alternatives: [2–4 relevant studies, products, or approaches]":
            "Existing work / alternatives: LMS inboxes; Piazza/Ed; tutoring chatbots; FAQ bots without a KB stamp or dual-TA queue.",
        "Gap / unmet need: [What remains insufficient or unresolved?]":
            "Gap / unmet need: Quiet escalation + MiniLM/LogReg triage + dual-TA staffing + professor stamp before Study Agent quotes.",
        "Proposed innovation: [Planned adaptation, integration, method, or investigation]":
            "Proposed innovation: Ask Triage + Help Coach + stamped Study Agent in one Canvas-linked multi-role app.",

        "State 2–3 measurable objectives and how each will be evaluated. Targets may be preliminary.":
            "Three measurable objectives mapped to demo acceptance and one live Canvas checklist. Targets are preliminary.",
        "Objective 1: [intended outcome]":
            "Objective 1: Triage and route asks to the right TA / help mode",
        "Objective 2: [intended outcome]":
            "Objective 2: Keep Study Agent answers professor-gated",
        "Objective 3: [intended outcome]":
            "Objective 3: Enable a Canvas-first campus deploy path",

        "Show the proposed architecture or research design. Clearly label planned components and relationships.":
            "Clients → FastAPI → local Ask Triage / Help Coach / stamped Study Agent → SQL + Canvas LTI/REST.",
        "Software: planned architecture, modules, data flow, database/APIs, UI/UX, security.":
            "Software: React SPA; FastAPI (requests / ta / knowledge / lti / help-room); SQLite→Postgres; WebSockets; Quiet-ask privacy.",
        "Research: questions/hypotheses, variables, setup, algorithms/models, datasets.":
            "Models: MiniLM + LogisticRegression + RAG joblibs; cluster cosine 0.72; Strategist client-side until live grades.",

        "State the key requirements, planned phases, and dependencies needed to carry out the project.":
            "Demo path is implemented; live Canvas is gated on IT credentials.",
        "Key requirements: [functional/non-functional or research requirements]":
            "Key requirements: Multi-role auth; Ask Triage; TA queue + Help Coach; KB stamp; Rooms; LTI/REST; WebSockets.",
        "Planned phases: [3–5 development, setup, data, or experimentation steps]":
            "Planned phases: (1) triage+roles (2) TA/KB gate (3) Rooms+demo Canvas (4) LTI live (5) Postgres + Strategist grades.",
        "Dependencies: [data, hardware, tools, access, client input, approvals]":
            "Dependencies: Canvas LTI key + API token; optional Entra; HTTPS; one AUI test course.",

        "Summarize the planned technical approach and why it fits the problem. Prefer a flowchart to final-output screenshots.":
            "Local NLP + professor gate fits campus integrity better than unconstrained LLM tutoring. Pipeline figure at right.",
        "Proposed methodology: [Agile / iterative prototyping / experimental design / simulation / other]":
            "Proposed methodology: Iterative prototyping with CI (backend + officehours-app) and role walkthrough demos.",
        "Technologies / methods: [languages, frameworks, algorithms, models, protocols, hardware]":
            "Technologies / methods: FastAPI, React/Vite/Tailwind, SQLAlchemy, sentence-transformers (all-MiniLM-L6-v2), scikit-learn, WebSockets, Canvas LTI 1.3 + REST.",
        "Data / resources: [dataset, participants, APIs, cloud, lab equipment, computing resources]":
            "Data / resources: Silver/synthetic ask labels; gold-label TA lab; demo Canvas mirror; live course modules when IT enables.",
        "Reproducibility / management: [Git, documentation, experiment tracking, versioning]":
            "Reproducibility / management: GitHub CI; docs/ (architecture, NLP, ops); train scripts; reports/; OFFICEHOURS_DEMO toggle.",

        "Explain how the project will be evaluated after implementation. Specify methods, baselines, and evidence to collect; do not report final results.":
            "Mix automated tests, holdouts, a gold-label TA lab, role walkthroughs, and a live Canvas checklist. Do not report final campus results here.",
        "Validation approach: [tests, experiment, benchmark, usability, security, statistical analysis]":
            "Validation approach: pytest; triage holdouts; gold-label TA lab; student/TA/professor walkthroughs; live Canvas checklist.",
        "Comparison / reference: [baseline, prior work, requirement, control, or acceptance criterion]":
            "Comparison / reference: LMS inbox / forum baseline. Acceptance = usable demo triage + 0 unauthorized Study Agent quotes + one live course checklist.",
        "Planned metrics: [accuracy, F1, latency, reliability, energy, user score, significance, etc.]":
            "Planned metrics: Category/routing quality (cite carefully); KB-gate refusal; LTI launch success; triage-path latency; role-task completion.",

        "Planned deliverables: [prototype/system/model/dataset/experiment/repository/documentation/report/paper/demo]":
            "Planned deliverables: Multi-role prototype; Ask Triage joblibs; architecture diagrams; demo script; live Canvas checklist; Capstone report.",
        "Milestone 1: [Problem definition / requirements / literature]   →   [date]":
            "Milestone 1: Problem definition / requirements / literature   →   Sep 2026",
        "Milestone 2: [Design / development / experimentation]   →   [date]":
            "Milestone 2: Design / development / experimentation   →   Fall 2026",
        "Milestone 3: [Evaluation / refinement / finalization]   →   [date]":
            "Milestone 3: Evaluation / refinement / finalization   →   Capstone deadline",

        "Show that the proposal is realistic within the Capstone timeframe, available resources, and technical constraints.":
            "Feasible as staged demo→live. Main risk is campus credential latency, not missing application code.",
        "Required resources: [hardware, software, datasets, APIs, cloud, lab access, budget, external expertise]":
            "Required resources: Dev laptop; GitHub; SQLite→Postgres host; Canvas LTI key/token; optional Entra; no GPU required for MiniLM demo.",
        "Main feasibility concern / risk: [data, hardware, integration, approval, performance, schedule, cost]":
            "Main feasibility concern / risk: IT delay on LTI / API / Entra; Strategist grades blocked until a live grade token.",
        "Mitigation / fallback: [alternative dataset, simplified scope, backup method, staged integration, contingency]":
            "Mitigation / fallback: Local Canvas mirror for showcase; one-course live stage; Postgres at go-live; Strategist stays client-side until grades API.",

        "Identify relevant considerations early and state how they will be addressed during development or research. Justify “Not applicable” where needed.":
            "Privacy, security, and responsible AI are in scope for a campus help product.",
        "Privacy / human participants: [consent, data minimization, storage/access, retention, anonymization]":
            "Privacy / human participants: Quiet asks hide identity from staff; course-scoped data; minimize PII in logs; term-aligned retention.",
        "Cybersecurity / legal / standards: [anticipated threats, safeguards, licenses, sector rules, technical standards]":
            "Cybersecurity / legal / standards: Auth + CORS; HTTPS for live; no portal scraping; Canvas LTI 1.3; least-privilege API tokens.",
        "AI use plan: [where AI tools/models may be used and how outputs will be verified, documented, attributed, and supervised]":
            "AI use plan: Local Ask Triage + Help Coach; Study Agent quotes only professor-stamped KB; OFFICEHOURS_ALLOW_EXTERNAL_LLM=false; refuse weak KB.",
        "AI system risks if applicable: [bias, hallucination, provenance, explainability, failure modes, misuse]":
            "AI system risks if applicable: Label bias; triage miss → human TA path; hallucination mitigated by stamp gate; course auth limits misuse.",

        "Describe what the project is expected to contribute if successfully completed. Avoid conclusion language or unverified performance claims.":
            "Expected contribution if completed successfully—without unverified campus performance claims.",
        "Expected technical / research contribution: [What the project aims to add, improve, test, or demonstrate]":
            "Expected technical / research contribution: Demonstrate gated local-NLP office-hours triage with dual-TA staffing and a professor-controlled Study Agent.",
        "Potential value / impact: [Why it may matter for users, industry, research, society, or deployment]":
            "Potential value / impact: Safer faculty-controlled AI help for campus office hours; transferable pattern for other LMS schools.",
        "Expected limitations / boundaries: [What the current Capstone will not attempt to solve]":
            "Expected limitations / boundaries: Not an SIS replacement; not live-grade Strategist yet; not multilingual ChatGPT-style tutoring.",

        "[1] Problem / need source.   [2] Key related work.   [3] Method, standard, or dataset.   Use only the most relevant sources.":
            "[1] AUI finals-week office-hours need.   [2] Piazza / Ed Q&amp;A.   [3] Canvas LTI 1.3; MiniLM; scikit-learn.",
    }

    missing = []
    for old, new in once.items():
        if old not in xml:
            missing.append(old)
        else:
            xml = xml.replace(old, new)

    metrics = [
        "Category / routing quality (holdout + demo walkthrough)",
        "Refuse unapproved or missing KB; stamp required before quotes",
        "LTI launch + module sync on one AUI test course when IT enables",
    ]
    targets = [
        "Usable triage in demo; cite holdout metrics carefully",
        "0 unauthorized Study Agent quotes from pending KB",
        "Live checklist pass on one AUI test course",
    ]
    for m in metrics:
        xml = xml.replace("[e.g., F1, latency, usability]", m, 1)
    for t in targets:
        xml = xml.replace("[target / criterion]", t, 1)

    replacements = {
        '<w:t>OPTIONAL VISUAL: existing approaches vs. proposed direction • gap map • feature comparison</w:t>':
            "</w:r></w:p>" + figure_paragraph(*rels["gap"][:2], rels["gap"][3], rels["gap"][4], rels["gap"][5]) + "<w:p><w:pPr><w:spacing w:after=\"0\"/><w:jc w:val=\"center\"/></w:pPr><w:r><w:t>",
        # The above is messy. Do full paragraph replacements instead.
    }
    # Undo if I accidentally applied - I didn't apply yet. Do clean paragraph swaps.
    _ = replacements

    def swap_paragraph(old_inner_ts: list[str], fig_key: str):
        nonlocal xml
        rid, fname, src, wp, hp, doc_id = rels[fig_key]
        if len(old_inner_ts) == 1:
            old = (
                '<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
                '<w:r><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:color w:val="7A817E"/><w:sz w:val="16"/></w:rPr>'
                f"<w:t>{old_inner_ts[0]}</w:t></w:r></w:p>"
            )
        else:
            old = (
                '<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
                '<w:r><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:color w:val="7A817E"/><w:sz w:val="16"/></w:rPr>'
                f"<w:t>{old_inner_ts[0]}</w:t><w:br/><w:t>{old_inner_ts[1]}</w:t></w:r></w:p>"
            )
            # rPr is on the r, not after r open incorrectly - match actual XML
            old = (
                '<w:p><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
                '<w:r><w:rPr><w:rFonts w:ascii="Aptos" w:hAnsi="Aptos"/><w:b/><w:color w:val="7A817E"/><w:sz w:val="16"/></w:rPr>'
                f"<w:t>{old_inner_ts[0]}</w:t><w:br/><w:t>{old_inner_ts[1]}</w:t></w:r></w:p>"
            )
        new = figure_paragraph(rid, fname, wp, hp, doc_id)
        if old not in xml:
            # try without assuming exact rPr
            idx = xml.find(old_inner_ts[0])
            if idx < 0:
                missing.append("FIGURE " + old_inner_ts[0])
                return
            p_start = xml.rfind("<w:p>", 0, idx)
            p_end = xml.find("</w:p>", idx) + len("</w:p>")
            xml = xml[:p_start] + new + xml[p_end:]
        else:
            xml = xml.replace(old, new, 1)

    swap_paragraph(["OPTIONAL VISUAL: existing approaches vs. proposed direction • gap map • feature comparison"], "gap")
    swap_paragraph(["PROPOSED DESIGN FIGURE", "Conceptual architecture • research workflow • system model • planned hardware setup"], "arch")
    swap_paragraph(["PLANNED WORK / REQUIREMENTS VISUAL", "Requirement map • development roadmap • experiment setup • module plan"], "road")
    swap_paragraph(["PROPOSED PROCESS / PIPELINE", "Inputs → Planned Development / Processing / Experimentation → Expected Outputs"], "pipe")
    swap_paragraph(["PLANNED EVALUATION FRAMEWORK", "Test matrix • evaluation workflow • metric plan • benchmark design"], "eval")

    if missing:
        raise SystemExit("Unreplaced strings:\n" + "\n".join(missing))

    leftover = [x for x in re.findall(r"\[[^\]]+\]", xml) if x not in ("[1]", "[2]", "[3]")]
    leftover = [x for x in leftover if "intended outcome" in x or "e.g.," in x or "target / criterion" in x or x.startswith("[Where")]
    if leftover:
        raise SystemExit("Leftover placeholders: " + str(leftover))

    def shrink_sz(m):
        v = int(m.group(1))
        if 14 <= v <= 20:
            v = max(12, v - 1)
        return f'w:sz w:val="{v}"'

    xml, n = re.subn(r'w:sz w:val="(\d+)"', shrink_sz, xml)
    print("font shrinks", n)
    xml = xml.replace('w:after="80"', 'w:after="16"')
    xml = xml.replace('w:bottom="432"', 'w:bottom="200"')
    xml = xml.replace("</w:tbl><w:p/></w:tc></w:tr></w:tbl><w:sectPr", "</w:tbl></w:tc></w:tr></w:tbl><w:sectPr")
    xml_path.write_text(xml, encoding="utf-8")
    out = OUT_DIR / "OfficeHours_AI_Capstone_Poster.docx"
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(work.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(work).as_posix())

    with zipfile.ZipFile(out) as z:
        body = z.read("word/document.xml").decode()
        text = re.sub(r"</w:p>", "\n", body)
        text = re.sub(r"<[^>]+>", "", text)
        text = text.replace("&amp;", "&")
        text = re.sub(r"\n+", "\n", text).strip()
    (OUT_DIR / "OfficeHours_AI_Capstone_Poster_content.txt").write_text(text + "\n", encoding="utf-8")
    return out


def main() -> None:
    figures = {
        "gap": fig_gap(),
        "arch": fig_architecture(),
        "road": fig_roadmap(),
        "pipe": fig_pipeline(),
        "eval": fig_evaluation(),
        "qr": fig_qr(),
    }
    out = fill_docx(figures)
    print("Wrote", out)
    for k, p in figures.items():
        print(k, p, Image.open(p).size)


if __name__ == "__main__":
    main()
