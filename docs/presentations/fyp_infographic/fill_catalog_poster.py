#!/usr/bin/env python3
"""Fill the official SSE 14.5×19 catalog poster. Placement stays on the template."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT_DOCX = HERE / "OfficeHours_AI_Catalog_Poster.docx"
OUT_PDF = HERE / "OfficeHours_AI_Catalog_Poster.pdf"
FIGS = HERE / "figures"

# Already-structured official poster (same dashed cells as every SSE FYP).
BASE_REF = "8ffaa4e:docs/presentations/OfficeHours_AI_Capstone_Poster.docx"

REPLACEMENTS = {
    "OfficeHours AI: Multi-Role Campus Office-Hours Triage with Local NLP and Canvas Integration":
        "OfficeHours AI: Campus Help Desk that Triages Asks and Quotes Only Professor-Stamped Answers",
    "Student Name(s): Sophia Abssi   |   Degree: B.Sc. Computer Science (SSE)   |   Project Type:  ☑ Software Development   ☐ Research-Based":
        "Student Name(s): Sophia Abssi   |   Degree: B.S. AI and Robotization (SSE)   |   Project Type:  ☑ Software Development   ☐ Research-Based",
    "Supervisor: TBD (Supervisor)   |   Co-Supervisor / Client: AUI Canvas LMS   |   Stage: Early Proposal   |   Date: Sep 2026":
        "Supervisor: Dr. Oumaima Hourrane   |   Co-Supervisor / Client: AUI Canvas LMS   |   Stage: Early Proposal   |   Date: Sep 2026",
    "Finals-week ask overload. OfficeHours AI triages asks, staffs TAs, and stamps Study Agent answers—local NLP, Canvas-first.":
        "Office hours break two ways: staff hear the same stuck point five times, and quiet students will not put a name on a public channel. OfficeHours is one Canvas-linked desk that triages the ask and lets a professor stamp the only text an agent may quote.",
    "Context / application area: AUI courses; students, TAs, professors at peak support demand":
        "Context / application area: AUI courses at peak demand — students, TAs, and professors.",
    "Proposed idea: React + FastAPI: Ask Triage, Help Coach, stamped Study Agent, Rooms, Canvas LTI":
        "Proposed idea: One web app — Quiet ask, Ask Triage, Help Coach, stamped Study Agent, Rooms, Canvas login.",
    "Expected contribution: Course-scoped triage, dual-TA staffing, KB stamp, demo→live Canvas path":
        "Expected contribution: Less repeat load, a private way to ask, and faculty-controlled AI answers.",
    "Lower ask barriers and repeat load while faculty stay the gate on AI answers.":
        "Cut repeat load and ask friction without letting a chatbot invent the syllabus.",
    "Problem statement / research question: How can office hours cut repeat load without unconstrained AI?":
        "Problem statement / research question: How can campus office hours route asks and still keep professors as the gate on AI answers?",
    "Stakeholders / intended users: Students (Quiet ask, Rooms); TAs (queue, Help Coach); Professors (KB stamp)":
        "Stakeholders / intended users: Students (Quiet ask, Rooms, Study Agent); TAs (desk, Help Coach); Professors (clusters, stamp, Canvas).",
    "Evidence, scope &amp; constraints: Silver/synthetic labels; local ML; live Canvas needs IT + HTTPS; no scraping":
        "Evidence, scope &amp; constraints: Local models by default; live Canvas needs campus credentials; no portal scrape; no open chatbot.",
    "LMS inboxes and Piazza/Ed lack local triage, dual-TA match, and a stamp gate.":
        "Inbox, Piazza/Ed, and tutoring chatbots do not combine a private ask, a triaged TA queue, and a stamp before student-facing AI.",
    "Existing work / alternatives: LMS inbox; Piazza/Ed; tutoring chatbots; FAQ bots without a stamp or dual-TA queue":
        "Existing work / alternatives: LMS inbox; Piazza/Ed; FAQ bots; unconstrained campus chatbots.",
    "Gap / unmet need: No Quiet ask + MiniLM triage + dual-TA staffing + professor stamp before student AI":
        "Gap / unmet need: No Quiet receipt + local triage + dual-TA match + professor stamp before an agent quotes.",
    "Proposed innovation: Ask Triage + Help Coach + stamped Study Agent in one Canvas-linked app":
        "Proposed innovation: Those four capabilities in one Canvas-linked product.",
    "Three objectives mapped to demo acceptance and one live Canvas checklist.":
        "Three objectives a recruiter can check on the demo and one live Canvas checklist.",
    "Objective 1: Triage and route asks to the right TA / help mode":
        "Objective 1: Route the ask to the right TA / help mode",
    "Routing quality (holdout + demo)":
        "Holdout quality + live demo walkthrough",
    "Usable demo triage; cite holdouts carefully":
        "Usable demo triage; cite lab scores as lab, not campus",
    "Objective 2: Keep Study Agent answers professor-gated":
        "Objective 2: Keep Study Agent answers professor-gated",
    "Refuse unapproved / missing KB":
        "Refuse unstamped or weakly matched notes",
    "0 unauthorized Study Agent quotes":
        "0 unauthorized Study Agent quotes",
    "Objective 3: Enable a Canvas-first campus deploy path":
        "Objective 3: Open a Canvas-first campus deploy path",
    "LTI + module sync on one test course":
        "Campus login + module sync on one test course",
    "Live checklist pass on one AUI course":
        "Live checklist pass on one AUI course",
    "Clients → FastAPI → Ask Triage / Help Coach / stamped Study Agent → SQL + Canvas LTI.":
        "Students, TAs, and professors share one web app. The API owns the queue and stamps. Canvas is the campus door.",
    "Software: React SPA; FastAPI; SQLite→Postgres; WebSockets; Quiet-ask privacy.":
        "Software: React web app; FastAPI; SQLite now, Postgres when hosted; live queue; Quiet-ask privacy.",
    "Models: MiniLM + LogReg + RAG joblibs; Strategist client-side until live grades.":
        "Models: MiniLM vectors, logistic classifiers, cosine lookup, planner tables. No hosted chatbot on the user path.",
    "Demo path is implemented; live Canvas is gated on IT credentials.":
        "A three-seat demo is planned for Oct–Nov 2026. Live Canvas is scheduled for Dec 2026, once campus credentials arrive.",
    "Key requirements: Multi-role auth; Ask Triage; TA queue + Help Coach; KB stamp; Rooms; LTI/REST":
        "Key requirements: Roles; Ask Triage; TA desk + Help Coach; professor stamp; Rooms; Canvas login and sync.",
    "Planned phases: (1) triage+roles (2) TA/KB gate (3) Rooms+demo (4) LTI live (5) Postgres/grades":
        "Planned phases: (1) roles + triage  (2) TA / stamp  (3) Rooms + demo  (4) live Canvas  (5) hosted database.",
    "Dependencies: Canvas LTI key + API token; optional Entra; HTTPS; one AUI test course":
        "Dependencies: Canvas launch key, API token, HTTPS, one AUI test course.",
    "Local NLP + professor gate fits campus integrity better than open LLM tutoring.":
        "Local models plus a professor stamp fit campus integrity better than an open tutoring bot.",
    "Proposed methodology: Iterative prototyping with CI (backend + officehours-app)":
        "Proposed methodology: Iterative product build, automated tests, and three-seat demos.",
    "Technologies / methods: FastAPI, React/Vite/Tailwind, SQLAlchemy, MiniLM, scikit-learn, WebSockets, LTI 1.3":
        "Technologies / methods: React, FastAPI, MiniLM, scikit-learn, Canvas LTI 1.3.",
    "Data / resources: Silver/synthetic asks; gold-label TA lab; demo Canvas mirror; live modules when enabled":
        "Data / resources: Synthetic and silver asks; curated gold file; local Canvas mirror until live modules.",
    "Reproducibility / management: GitHub CI; docs/; train scripts; reports/; OFFICEHOURS_DEMO toggle":
        "Reproducibility / management: GitHub, documentation, train scripts, and evaluation reports.",
    "Tests, holdouts, gold-label lab, role walkthroughs, live Canvas checklist — no final campus claims.":
        "Lab checks, a gold-label file, three-seat walkthroughs, and a live Canvas checklist. No campus-quality claim here.",
    "Validation approach: pytest; holdouts; gold-label TA lab; role walkthroughs; live Canvas checklist":
        "Validation approach: Automated tests; holdouts; gold-label lab; student / TA / professor walkthrough; live checklist.",
    "Comparison / reference: LMS inbox/forum baseline; demo triage + 0 unauthorized quotes + one live course":
        "Comparison / reference: Inbox / forum baseline. Accept if demo triage works, the agent never quotes unstamped text, and one course can launch.",
    "Planned metrics: Routing quality (cite carefully); KB refusal; LTI success; latency; task completion":
        "Planned metrics: Lab accuracy / F1 (honesty table); stamp refusal; Canvas launch success; walkthrough completion.",
    "Planned deliverables: Prototype; Ask Triage joblibs; diagrams; demo script; live checklist; Capstone report":
        "Planned deliverables: Running product; trained models; diagrams; demo script; live checklist; Capstone report.",
    "Feasible as staged demo→live. Main risk is campus credential latency.":
        "Feasible as a planned demo in Oct–Nov 2026 and live when campus credentials arrive in Dec 2026. The risk is campus keys, not missing code.",
    "Required resources: Laptop; GitHub; SQLite→Postgres; Canvas LTI/token; optional Entra; no GPU for MiniLM":
        "Required resources: Laptop, GitHub, SQLite then Postgres, Canvas key and token. No GPU required for the demo.",
    "Main feasibility concern / risk: IT delay on LTI/API/Entra; Strategist grades blocked until a live grade token":
        "Main feasibility concern / risk: IT delay on the Canvas launch key and API token.",
    "Mitigation / fallback: Demo Canvas mirror; one-course live stage; Postgres at go-live; Strategist stays client-side":
        "Mitigation / fallback: Local Canvas mirror for showcase; one-course live stage; Postgres at go-live.",
    "Privacy, security, and responsible AI are in scope for campus help.":
        "Privacy, security, and responsible AI are in scope for a campus help product.",
    "Privacy / human participants: Quiet asks; course-scoped data; minimize PII; role auth; term retention":
        "Privacy / human participants: Quiet asks hide the name from classmates; course-scoped data; minimize identifiers.",
    "Cybersecurity / legal / standards: Auth+CORS; HTTPS; no scraping; Canvas LTI 1.3; least-privilege tokens":
        "Cybersecurity / legal / standards: Role login; HTTPS for live; no scrape; Canvas LTI 1.3; least-privilege token.",
    "AI use plan: Local Ask Triage + Help Coach; Study Agent quotes stamped KB only; external LLM off":
        "AI use plan: Local Ask Triage and Help Coach; Study Agent quotes stamped notes only; hosted LLM stays off unless approved.",
    "AI system risks if applicable: Label bias; triage miss→TA; stamp gate vs hallucination; course-auth limits misuse":
        "AI system risks if applicable: Label bias and misses go to a human TA; the stamp blocks an invented syllabus.",
    "Expected contribution if successful — no unverified campus performance claims.":
        "What this Capstone aims to add — no unverified campus performance claims.",
    "Expected technical / research contribution: Gated local-NLP office-hours triage with dual-TA staffing and stamped Study Agent":
        "Expected technical / research contribution: A gated local-NLP office-hours desk with dual-TA routing and a professor-controlled agent.",
    "Potential value / impact: Safer faculty-controlled AI help; transferable to other LMS schools":
        "Potential value / impact: Safer campus AI help, and a pattern other LMS schools can copy.",
    "Expected limitations / boundaries: Not SIS; not live-grade Strategist yet; not multilingual ChatGPT tutoring":
        "Expected limitations / boundaries: Not a student-information system; not live-grade planning yet; not a multilingual chatbot.",
    "[1] AUI finals-week office-hours need.   [2] Piazza / Ed Q&amp;A.   [3] Canvas LTI 1.3; MiniLM; scikit-learn.":
        "[1] Piazza; Ed Discussion (forum baseline).   [2] IMS Global, Learning Tools Interoperability 1.3.   [3] Reimers &amp; Gurevych, Sentence-BERT; Pedregosa et al., scikit-learn.",
}

MEDIA = {
    "image1.png": FIGS / "qr.png",
    "image3.png": FIGS / "SLOT_gap.png",
    "image4.png": FIGS / "SLOT_architecture.png",
    "image5.png": FIGS / "SLOT_roadmap.png",
    "image6.png": FIGS / "SLOT_pipeline.png",
    "image7.png": FIGS / "SLOT_evaluation.png",
}


def _extract_base(work: Path) -> None:
    work.mkdir(parents=True, exist_ok=True)
    raw = subprocess.check_output(["git", "show", BASE_REF], cwd=ROOT)
    tmp = work / "_base.docx"
    tmp.write_bytes(raw)
    with zipfile.ZipFile(tmp) as z:
        z.extractall(work)


def fill() -> Path:
    from build_catalog_figures import build_all

    build_all()
    work = HERE / "_catalog_work"
    if work.exists():
        shutil.rmtree(work)
    _extract_base(work)

    xml_path = work / "word" / "document.xml"
    xml = xml_path.read_text(encoding="utf-8")
    missing = [old for old in REPLACEMENTS if old not in xml]
    if missing:
        raise SystemExit("Missing template strings:\n" + "\n".join(missing[:8]))
    for old, new in REPLACEMENTS.items():
        xml = xml.replace(old, new, 1)
    xml_path.write_text(xml, encoding="utf-8")

    for name, src in MEDIA.items():
        dest = work / "word" / "media" / name
        if not src.exists():
            raise SystemExit(f"missing figure {src}")
        shutil.copyfile(src, dest)

    if OUT_DOCX.exists():
        OUT_DOCX.unlink()
    with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(work.rglob("*")):
            if path.is_file() and path.name != "_base.docx":
                z.write(path, path.relative_to(work).as_posix())
    shutil.rmtree(work)
    return OUT_DOCX


def export_pdf(docx: Path) -> Path:
    subprocess.check_call(
        [
            "soffice",
            "--headless",
            "--nologo",
            "--nofirststartwizard",
            "--convert-to",
            "pdf",
            "--outdir",
            str(HERE),
            str(docx),
        ],
        timeout=60,
    )
    return OUT_PDF


if __name__ == "__main__":
    docx = fill()
    pdf = export_pdf(docx)
    print(docx)
    print(pdf)
