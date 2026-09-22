#!/usr/bin/env python3
"""Fill SSE poster text (length-capped so it stays 1 page) and paste visuals into the dashed boxes."""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw

TPL = Path(
    "/home/ubuntu/.cursor/projects/workspace/uploads/"
    "CSC_Capstone_Early_Stage_Proposal_Poster_Template__1__f6a3.docx"
)
PRES = Path(__file__).resolve().parent
VIS = PRES / "poster_visuals"
WORK = Path("/tmp/poster_composite")
DPI = 150


def build_base() -> Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir()
    src = WORK / "src"
    src.mkdir()
    with zipfile.ZipFile(TPL) as z:
        z.extractall(src)
    shutil.copyfile(VIS / "V10_qr_square.png", src / "word" / "media" / "image1.png")
    xml_path = src / "word" / "document.xml"
    xml = xml_path.read_text(encoding="utf-8")

    # Keep replacements close to original lengths so the 2-column table stays on one page.
    once = {
        "[PROJECT TITLE: Clear, Specific, and Technically Descriptive]":
            "OfficeHours AI: Multi-Role Campus Office-Hours Triage with Local NLP and Canvas Integration",
        "[Name(s)]": "Sophia Abssi",
        "[Program]": "B.Sc. Computer Science (SSE)",
        "[Name]": "TBD (Supervisor)",
        "[If applicable]": "AUI Canvas LMS",
        "[Month Year]": "Sep 2026",
        "☐ Software Development": "☑ Software Development",
        "Replace with QR": "Repository",
        "Proposal • Repository • Supporting Material": "github.com/abssisophia9-hub/officehours-ai",
        "Use 3–4 concise sentences: the problem, why it matters, the proposed idea, and the expected contribution. Do not report final results.":
            "Finals-week ask overload. OfficeHours AI triages asks, staffs TAs, and stamps Study Agent answers—local NLP, Canvas-first.",
        "[Where, for whom, and why the problem matters]":
            "AUI courses; students, TAs, professors at peak support demand",
        "[System, method, model, experiment, or prototype]":
            "React + FastAPI: Ask Triage, Help Coach, stamped Study Agent, Rooms, Canvas LTI",
        "[What the project aims to improve, investigate, or demonstrate]":
            "Course-scoped triage, dual-TA staffing, KB stamp, demo→live Canvas path",
        "Define the need before the solution. Use evidence, stakeholder needs, or a research question to justify the project.":
            "Lower ask barriers and repeat load while faculty stay the gate on AI answers.",
        "[1–2 precise sentences]":
            "How can office hours cut repeat load without unconstrained AI?",
        "[Who is affected or expected to benefit?]":
            "Students (Quiet ask, Rooms); TAs (queue, Help Coach); Professors (KB stamp)",
        "[Need evidence and project boundaries]":
            "Silver/synthetic labels; local ML; live Canvas needs IT + HTTPS; no scraping",
        "Summarize the most relevant prior work and identify the gap the proposal will address.":
            "LMS inboxes and Piazza/Ed lack local triage, dual-TA match, and a stamp gate.",
        "[2–4 relevant studies, products, or approaches]":
            "LMS inbox; Piazza/Ed; tutoring chatbots; FAQ bots without a stamp or dual-TA queue",
        "[What remains insufficient or unresolved?]":
            "No Quiet ask + MiniLM triage + dual-TA staffing + professor stamp before student AI",
        "[Planned adaptation, integration, method, or investigation]":
            "Ask Triage + Help Coach + stamped Study Agent in one Canvas-linked app",
        "State 2–3 measurable objectives and how each will be evaluated. Targets may be preliminary.":
            "Three objectives mapped to demo acceptance and one live Canvas checklist.",
        "Objective 1: [intended outcome]": "Objective 1: Triage and route asks to the right TA / help mode",
        "Objective 2: [intended outcome]": "Objective 2: Keep Study Agent answers professor-gated",
        "Objective 3: [intended outcome]": "Objective 3: Enable a Canvas-first campus deploy path",
        "Show the proposed architecture or research design. Clearly label planned components and relationships.":
            "Clients → FastAPI → Ask Triage / Help Coach / stamped Study Agent → SQL + Canvas LTI.",
        "Software: planned architecture, modules, data flow, database/APIs, UI/UX, security.":
            "Software: React SPA; FastAPI; SQLite→Postgres; WebSockets; Quiet-ask privacy.",
        "Research: questions/hypotheses, variables, setup, algorithms/models, datasets.":
            "Models: MiniLM + LogReg + RAG joblibs; Strategist client-side until live grades.",
        "State the key requirements, planned phases, and dependencies needed to carry out the project.":
            "Demo path is implemented; live Canvas is gated on IT credentials.",
        "[functional/non-functional or research requirements]":
            "Multi-role auth; Ask Triage; TA queue + Help Coach; KB stamp; Rooms; LTI/REST",
        "[3–5 development, setup, data, or experimentation steps]":
            "(1) triage+roles (2) TA/KB gate (3) Rooms+demo (4) LTI live (5) Postgres/grades",
        "[data, hardware, tools, access, client input, approvals]":
            "Canvas LTI key + API token; optional Entra; HTTPS; one AUI test course",
        "Summarize the planned technical approach and why it fits the problem. Prefer a flowchart to final-output screenshots.":
            "Local NLP + professor gate fits campus integrity better than open LLM tutoring.",
        "[Agile / iterative prototyping / experimental design / simulation / other]":
            "Iterative prototyping with CI (backend + officehours-app)",
        "[languages, frameworks, algorithms, models, protocols, hardware]":
            "FastAPI, React/Vite/Tailwind, SQLAlchemy, MiniLM, scikit-learn, WebSockets, LTI 1.3",
        "[dataset, participants, APIs, cloud, lab equipment, computing resources]":
            "Silver/synthetic asks; gold-label TA lab; demo Canvas mirror; live modules when enabled",
        "[Git, documentation, experiment tracking, versioning]":
            "GitHub CI; docs/; train scripts; reports/; OFFICEHOURS_DEMO toggle",
        "Explain how the project will be evaluated after implementation. Specify methods, baselines, and evidence to collect; do not report final results.":
            "Tests, holdouts, gold-label lab, role walkthroughs, live Canvas checklist — no final campus claims.",
        "[tests, experiment, benchmark, usability, security, statistical analysis]":
            "pytest; holdouts; gold-label TA lab; role walkthroughs; live Canvas checklist",
        "[baseline, prior work, requirement, control, or acceptance criterion]":
            "LMS inbox/forum baseline; demo triage + 0 unauthorized quotes + one live course",
        "[accuracy, F1, latency, reliability, energy, user score, significance, etc.]":
            "Routing quality (cite carefully); KB refusal; LTI success; latency; task completion",
        "[prototype/system/model/dataset/experiment/repository/documentation/report/paper/demo]":
            "Prototype; Ask Triage joblibs; diagrams; demo script; live checklist; Capstone report",
        "[Problem definition / requirements / literature]   →   [date]":
            "Problem / requirements / literature   →   Sep 2026",
        "[Design / development / experimentation]   →   [date]":
            "Design / development / experimentation   →   Fall 2026",
        "[Evaluation / refinement / finalization]   →   [date]":
            "Evaluation / refinement / finalization   →   Capstone deadline",
        "Show that the proposal is realistic within the Capstone timeframe, available resources, and technical constraints.":
            "Feasible as staged demo→live. Main risk is campus credential latency.",
        "[hardware, software, datasets, APIs, cloud, lab access, budget, external expertise]":
            "Laptop; GitHub; SQLite→Postgres; Canvas LTI/token; optional Entra; no GPU for MiniLM",
        "[data, hardware, integration, approval, performance, schedule, cost]":
            "IT delay on LTI/API/Entra; Strategist grades blocked until a live grade token",
        "[alternative dataset, simplified scope, backup method, staged integration, contingency]":
            "Demo Canvas mirror; one-course live stage; Postgres at go-live; Strategist stays client-side",
        "Identify relevant considerations early and state how they will be addressed during development or research. Justify “Not applicable” where needed.":
            "Privacy, security, and responsible AI are in scope for campus help.",
        "[consent, data minimization, storage/access, retention, anonymization]":
            "Quiet asks; course-scoped data; minimize PII; role auth; term retention",
        "[anticipated threats, safeguards, licenses, sector rules, technical standards]":
            "Auth+CORS; HTTPS; no scraping; Canvas LTI 1.3; least-privilege tokens",
        "[where AI tools/models may be used and how outputs will be verified, documented, attributed, and supervised]":
            "Local Ask Triage + Help Coach; Study Agent quotes stamped KB only; external LLM off",
        "[bias, hallucination, provenance, explainability, failure modes, misuse]":
            "Label bias; triage miss→TA; stamp gate vs hallucination; course-auth limits misuse",
        "Describe what the project is expected to contribute if successfully completed. Avoid conclusion language or unverified performance claims.":
            "Expected contribution if successful — no unverified campus performance claims.",
        "[What the project aims to add, improve, test, or demonstrate]":
            "Gated local-NLP office-hours triage with dual-TA staffing and stamped Study Agent",
        "[Why it may matter for users, industry, research, society, or deployment]":
            "Safer faculty-controlled AI help; transferable to other LMS schools",
        "[What the current Capstone will not attempt to solve]":
            "Not SIS; not live-grade Strategist yet; not multilingual ChatGPT tutoring",
        "[1] Problem / need source.   [2] Key related work.   [3] Method, standard, or dataset.   Use only the most relevant sources.":
            "[1] AUI finals-week office-hours need.   [2] Piazza / Ed Q&amp;A.   [3] Canvas LTI 1.3; MiniLM; scikit-learn.",
    }
    missing = [k for k in once if k not in xml]
    if missing:
        raise SystemExit("missing keys:\n" + "\n".join(missing))
    for o, n in once.items():
        xml = xml.replace(o, n)
    xml = xml.replace("[e.g., F1, latency, usability]", "Routing quality (holdout + demo)", 1)
    xml = xml.replace("[e.g., F1, latency, usability]", "Refuse unapproved / missing KB", 1)
    xml = xml.replace("[e.g., F1, latency, usability]", "LTI + module sync on one test course", 1)
    xml = xml.replace("[target / criterion]", "Usable demo triage; cite holdouts carefully", 1)
    xml = xml.replace("[target / criterion]", "0 unauthorized Study Agent quotes", 1)
    xml = xml.replace("[target / criterion]", "Live checklist pass on one AUI course", 1)

    def shrink(m):
        v = int(m.group(1))
        if 14 <= v <= 20:
            v = max(12, v - 1)
        return f'w:sz w:val="{v}"'

    xml = re.sub(r'w:sz w:val="(\d+)"', shrink, xml)
    xml = xml.replace('w:after="80"', 'w:after="20"')
    xml_path.write_text(xml, encoding="utf-8")

    docx = WORK / "base.docx"
    with zipfile.ZipFile(docx, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(src.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(src).as_posix())
    shutil.copyfile(docx, PRES / "OfficeHours_AI_Capstone_Poster.docx")
    return docx


def rasterize(docx: Path) -> Path:
    subprocess.check_call(
        ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(WORK), str(docx)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    info = subprocess.check_output(["pdfinfo", str(WORK / "base.pdf")], text=True)
    print(info)
    if "Pages:           1" not in info:
        raise SystemExit("base poster is not 1 page")
    subprocess.check_call(["pdftoppm", "-png", "-r", str(DPI), str(WORK / "base.pdf"), str(WORK / "base")])
    return WORK / "base-1.png"


def crop_v_header(img: Image.Image) -> Image.Image:
    img = img.convert("RGB")
    if img.width >= 1000:
        r, g, b = img.getpixel((20, 20))
        if g > 70 and r < 50:
            return img.crop((0, 110, img.width, img.height))
    return img


def fit(fig: Image.Image, tw: int, th: int) -> Image.Image:
    fig = crop_v_header(fig)
    ratio = min(tw / fig.width, th / fig.height)
    return fig.resize((max(1, int(fig.width * ratio)), max(1, int(fig.height * ratio))), Image.Resampling.LANCZOS)


def find_dashed_boxes(page: Image.Image) -> list[tuple[int, int, int, int]]:
    """Find large pale rectangles with gray dashed borders."""
    w, h = page.size
    rgb = page.convert("RGB")
    px = rgb.load()

    def gray_border(x, y):
        r, g, b = px[x, y]
        avg = (r + g + b) / 3
        return 150 <= avg <= 205 and abs(r - g) < 20 and abs(g - b) < 20

    # horizontal gray runs
    runs = []
    for y in range(0, h, 2):
        x = 0
        while x < w:
            if gray_border(x, y):
                x0 = x
                while x < w and gray_border(x, y):
                    x += 1
                if x - x0 > w * 0.22:
                    runs.append((y, x0, x))
            x += 1

    # cluster y's into box top/bottom pairs
    boxes = []
    used = [False] * len(runs)
    for i, (y1, a1, b1) in enumerate(runs):
        if used[i]:
            continue
        # find a later run with similar x range = bottom
        for j in range(i + 1, len(runs)):
            y2, a2, b2 = runs[j]
            if used[j]:
                continue
            if abs(a1 - a2) < 30 and abs(b1 - b2) < 30 and 70 < (y2 - y1) < 420:
                x0, x1 = min(a1, a2), max(b1, b2)
                boxes.append((x0, y1, x1, y2))
                used[i] = used[j] = True
                break

    # unique, largest first, drop overlaps
    boxes = sorted(set(boxes), key=lambda b: (b[1], b[0]))
    cleaned = []
    for b in boxes:
        if any(abs(b[1] - c[1]) < 25 and abs(b[0] - c[0]) < 25 for c in cleaned):
            continue
        cleaned.append(b)
    print("detected boxes", len(cleaned), cleaned)
    return cleaned


def compose(page_png: Path) -> Path:
    page = Image.open(page_png).convert("RGB")
    scale = DPI / 72.0

    def box_pts(x0, y0, x1, y1):
        return (
            int(x0 * scale),
            int(y0 * scale),
            int(x1 * scale),
            int(y1 * scale),
        )

    # Caption anchors from pdftotext -bbox on the official 1044x1368pt template.
    # Each tuple is the dashed cell that holds that caption.
    assigned = [
        (box_pts(46, 492, 512, 578), VIS / "V04_gap_map.png"),
        (box_pts(46, 948, 512, 1088), VIS / "V01_architecture.png"),
        (box_pts(46, 1184, 512, 1308), VIS / "V07_roadmap.png"),
        (box_pts(532, 298, 998, 408), VIS / "V03_pipeline.png"),
        (box_pts(532, 578, 998, 688), VIS / "V08_evaluation.png"),
    ]

    draw = ImageDraw.Draw(page)
    for box, fig_path in assigned:
        x0, y0, x1, y1 = box
        pad = 8
        tw, th = x1 - x0 - pad * 2, y1 - y0 - pad * 2
        fitted = fit(Image.open(fig_path), tw, th)
        draw.rectangle((x0 + 4, y0 + 4, x1 - 4, y1 - 4), fill=(255, 255, 255))
        px = x0 + (x1 - x0 - fitted.width) // 2
        py = y0 + (y1 - y0 - fitted.height) // 2
        page.paste(fitted, (px, py))
        print("placed", fig_path.name, box, fitted.size)

    out_png = PRES / "OfficeHours_AI_Capstone_Poster_filled.png"
    out_pdf = PRES / "OfficeHours_AI_Capstone_Poster.pdf"
    page.save(out_png, "PNG")
    page.save(out_pdf, "PDF", resolution=DPI)
    art = Path("/opt/cursor/artifacts")
    shutil.copyfile(out_png, art / "OfficeHours_AI_Capstone_Poster_filled.png")
    shutil.copyfile(out_pdf, art / "OfficeHours_AI_Capstone_Poster.pdf")
    return out_png


def main() -> None:
    docx = build_base()
    png = rasterize(docx)
    out = compose(png)
    print("WROTE", out)


if __name__ == "__main__":
    main()
