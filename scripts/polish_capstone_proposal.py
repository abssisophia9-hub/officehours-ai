#!/usr/bin/env python3
"""Rewrite proposal table cells and thin sections in place.

Keeps the official CSC Word template (styles, headers, table grid, page size).
Only paragraph text inside existing cells / body paragraphs is replaced.
Writes by swapping text inside the original document.xml so Word prefixes stay intact.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XMLNS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
ET.register_namespace("w", XMLNS["w"])
ET.register_namespace(
    "r", "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)

DOCX = Path("CSC_Capstone_Project_Proposal_Sophia.docx")


def cell_text(tc) -> str:
    return "".join(t.text or "" for t in tc.iter(f"{W}t")).strip()


def para_text(p) -> str:
    return "".join(t.text or "" for t in p.iter(f"{W}t")).strip()


def set_runs_text(container, text: str) -> None:
    """Write text into the first existing run; drop extra <w:t> nodes."""
    texts = list(container.iter(f"{W}t"))
    if not texts:
        p = container.find(f"{W}p")
        if p is None:
            p = ET.SubElement(container, f"{W}p")
        r = ET.SubElement(p, f"{W}r")
        t = ET.SubElement(r, f"{W}t")
        if text.startswith(" ") or text.endswith(" "):
            t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = text
        return
    first = texts[0]
    if text.startswith(" ") or text.endswith(" "):
        first.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    first.text = text
    for extra in texts[1:]:
        extra.text = ""


def set_cell(tc, text: str) -> None:
    paragraphs = tc.findall(f"{W}p")
    if not paragraphs:
        set_runs_text(tc, text)
        return
    set_runs_text(paragraphs[0], text)
    for extra in paragraphs[1:]:
        for t in extra.iter(f"{W}t"):
            t.text = ""


def row_cells(tr):
    return tr.findall(f"{W}tc")


def table_fingerprint(tbl) -> str:
    rows = tbl.findall(f"{W}tr")
    if not rows:
        return ""
    header = " | ".join(cell_text(tc) for tc in row_cells(rows[0]))
    return f"{len(rows)}::{header[:80]}"


LIFECYCLE = {
    "1. Problem Definition & Background": (
        "Define the AUI finals-week overload problem and the research question. "
        "The concept is triage: organize incoming academic asks before they become "
        "scattered emails, so staff see one structured ticket instead of the same "
        "question five times.",
        "Write the research question: can Ask Triage reduce repeated staff load and "
        "raise student comfort without replacing office hours? Freeze the product as "
        "one React app (frontend/officehours-app, port 5180) plus one FastAPI process "
        "(backend/, port 8000). Role is course_memberships.role (student / TA / "
        "professor) on a course_id, not a global account type. Keep out of scope: "
        "physical kiosk, barcode/NFC, and scraping canvas.aui.ma. Specify Quiet ask: "
        "created_by_user_id is stored, but GET /requests/{id}/status never returns "
        "the asker’s name.",
    ),
    "2. Investigation / Requirements": (
        "Lock evidence, baselines, and campus constraints so the project does not "
        "claim live AUI transcripts it does not have, and so Canvas LTI 1.3 is the "
        "enrollment path rather than a second password site.",
        "Compare Canvas inbox/tickets, FIFO queues, ungated RAG chatbots, and the "
        "old three web shells. Freeze: LTI 1.3 OIDC + RS256 JWKS (lti13.py); optional "
        "Microsoft Entra @aui.ma; OFFICEHOURS_DEMO for seeded accounts; "
        "OFFICEHOURS_ALLOW_EXTERNAL_LLM=false on the assessed intake path. Freeze "
        "lab data already in the repo: Analyzer stratified CV ~84.6% (n=156); "
        "Matcher silver holdout ~87.5% (n=32); curated gold n=80 (Analyzer acc 0.75, "
        "Matcher acc 0.79). Those are lab numbers, not campus human_gold.",
    ),
    "3. Technical Design / Research Design": (
        "Design one login, per-course RBAC, Ask Triage at POST /requests/, a "
        "professor knowledge-base gate before any Study Agent answer, and a live TA "
        "queue over WebSocket /ws.",
        "Specify SQLAlchemy tables: users, courses, course_memberships, "
        "auth_sessions, requests (text, category, cluster_id, assigned_ta, "
        "student_hint, help_mode, work_status, created_by_user_id), "
        "knowledge_entries (pending_review → approved/rejected), help_posts, "
        "notifications. Specify the four tools: MiniLM (all-MiniLM-L6-v2) embeds "
        "text; scikit-learn LogisticRegression joblibs pick a class; cosine "
        "similarity retrieves the nearest stamped note; fixed tables fill wait, "
        "difficulty, and planner cards. Ask Triage = Analyzer → Matcher → "
        "Synthesizer. Help Coach is POST /ta/assist/ (draft_reply, socratic, "
        "refresh_teaching, rewrite_reply). Study Agent is POST /agent/ask and "
        "refuses below similarity 0.42. Clustering shares cluster_id at cosine ≥ 0.72.",
    ),
    "4. Development / Experimentation": (
        "Build the running loop from Quiet ask to TA Help Coach to professor stamp "
        "to Study Agent answer, plus Rooms and Canvas launch, in this repository.",
        "Ship routers auth, requests, ta, knowledge, help-room, canvas, lti, "
        "realtime. Train with train_classifier.py, train_matcher.py, "
        "train_synthesizer.py → backend/models/*.joblib. On submit: classify, "
        "assign TA, retrieve a hint, write cluster_id, seed a pending KB draft, "
        "push triage.* on /ws. Staffing: claim → in_progress → reply or group "
        "meeting. Professor approve/reject KB. Canvas POST /canvas/launch JIT "
        "provision; sync_course_materials copies modules/files into pending KB. "
        "Rooms: Problem/Discussion/Article, Hilbert ŵ. Revision Strategist is a "
        "local formula (weight × gap to 85%) until Canvas grades exist. Demo "
        "password aui-demo. Hardening: rate_limit.py, upload magic, LTI nonce.",
    ),
    "5. Validation & Evaluation": (
        "Show whether the built system meets the objectives using pytest and lab "
        "model scores, with an honesty table rather than a live AUI accuracy claim.",
        "Run backend pytest (Quiet-ask redaction, KB refuse-unapproved, dual-TA "
        "matcher, Canvas launch, upload/security). Report Analyzer CV ~84.6% "
        "(n=156), Matcher silver ~87.5%, gold held-out Analyzer ~75% / Matcher ~79% "
        "(n=80, not campus human_gold). Walk through s.elidrissi Quiet ask on "
        "CSC 2302 → WebSocket to a.chen → Help Coach → a.benali stamp → "
        "/agent/ask quotes that stamp only. If examiners require human labels, "
        "run docs/gold_label_lab.md (target ≥40 human_gold).",
    ),
    "6. Finalization & Communication": (
        "Package a supervisor-runnable demo and a campus hand-off so Dr. Hourrane, "
        "Innovation Day, and AUI IT inspect the same product.",
        "Deliver docs/defense_crib.md, system_architecture.md, SECURITY.md, "
        "glossary.md, and the official SSE poster. Launch with "
        "./scripts/run_product.sh (OFFICEHOURS_DEMO=true; Sara / Alice / Benali). "
        "Community hand-off: OFFICEHOURS_DEMO=false, DATABASE_URL Postgres, Canvas "
        "LTI key + API token, Microsoft SSO only after IT client_id. Repo "
        "github.com/abssisophia9-hub/officehours-ai. URLs http://127.0.0.1:5180 "
        "and http://127.0.0.1:8000/docs.",
    ),
}


DIFF = {
    "Performance / Accuracy": (
        "Manual inbox sorting, FIFO queues, or campus chatbots with no held-out "
        "triage score. A generic bot can answer, but nobody can say how often it "
        "picks the right category or the right TA.",
        "What we provide: Ask Triage at POST /requests/. Analyzer "
        "(MiniLM + request_classifier.joblib) writes category, urgency, difficulty, "
        "and minutes. Matcher writes assigned_ta / alternative_ta from this course’s "
        "roster and queue depth. Synthesizer copies a student_hint from stamped KB "
        "or the teaching bank. Reports live in reports/final_report/.",
        "Lab evidence instead of an unevaluated bot: Analyzer CV ~84.6% (n=156); "
        "Matcher silver holdout ~87.5% (n=32); curated gold n=80 (Analyzer acc 0.75 "
        "/ macro-F1 0.66; Matcher acc 0.79 / macro-F1 0.78). Cite as lab, not campus "
        "quality. Same saved joblib + same text → same label.",
    ),
    "Cost / Complexity": (
        "Paid Claude/OpenAI on every student click, plus three disconnected "
        "frontends (kiosk, TA dashboard, professor dashboard).",
        "What we provide: one React SPA and one FastAPI process. Assessed intake "
        "uses local MiniLM + scikit-learn (no hosted LLM). SQLite at "
        "backend/officehours.db; Postgres via DATABASE_URL when hosted. Rate limit "
        "and WebSocket hub stay in that process.",
        "No per-ask API bill on the assessed path. Campus operations stay one "
        "origin plus one database. External LLM stays off "
        "(OFFICEHOURS_ALLOW_EXTERNAL_LLM=false) unless a later bake-off is approved.",
    ),
    "Usability / Accessibility": (
        "Separate dashboards per role, and every ask requires a visible name.",
        "What we provide: one login + course picker. Role is per course "
        "(Alice is TA on CSC 2302 and student elsewhere). Quiet ask hides the name "
        "on the queue and on status-by-code; created_by_user_id still lets Sara "
        "open My asks. Named Rooms are the classmate forum. Help mode is message, "
        "face_to_face, or online_meeting.",
        "One tool to learn. Students who will not ask under their name still get a "
        "receipt code. Staff still see a structured ticket.",
    ),
    "Scalability / Efficiency": (
        "Polling dashboards and one-TA FIFO queues. Repeated rotations questions "
        "are answered five times.",
        "What we provide: WebSocket /ws pushes triage.* and queue events to that "
        "course only. Clustering (MiniLM, cosine ≥ 0.72) shares cluster_id. "
        "Professor planner cards then suggest group_session (≥3 similar), faq (2), "
        "or one_to_one (sensitive/urgent). Approving a card copies meeting_title / "
        "when / place onto every linked ask.",
        "Live desks without refresh. One shared review instead of N identical 1:1s "
        "when the same topic repeats.",
    ),
    "Security / Reliability": (
        "Ad-hoc campus scripts, unsigned Canvas buttons, or sessions that are just "
        "an email in the browser.",
        "What we provide: PBKDF2-HMAC-SHA256 passwords; opaque session tokens; "
        "access_control.py checks membership on every course route; LTI 1.3 JWT "
        "verified against Canvas JWKS; in-process rate limit on /auth/login, "
        "/requests/, /agent/ask; upload magic-byte checks; pytest on Quiet-ask "
        "redaction and unsigned-launch 404 when demo is off.",
        "A stolen token cannot see another course. A Quiet receipt cannot leak a "
        "name. Demo impersonation routes disappear when OFFICEHOURS_DEMO=false.",
    ),
    "Context-specific factor": (
        "Manual CSV enrollment or scraping the AUI portal / SIS.",
        "What we provide: Canvas LTI 1.3 launch (/lti/login → /lti/launch) maps "
        "Learner / TeachingAssistant / Instructor onto course_memberships. Canvas "
        "REST (CANVAS_BASE_URL + token) copies modules/files into knowledge_entries "
        "as pending_review. OFFICEHOURS_DEMO=true uses a local mirror and seeded "
        "Sara / Alice / Benali accounts.",
        "Students open OfficeHours from inside the Canvas course, already signed "
        "in. IT supplies a developer key and token; we do not scrape portal HTML.",
    ),
}


SUCCESS = {
    "Working multi-role product (Obj. 1)": (
        "Evidence: frontend/officehours-app on :5180 calling FastAPI on :8000. "
        "Login + course picker. Workspaces /student, /ta, /professor. Seeded "
        "accounts s.elidrissi@aui.ma (student), a.chen@aui.ma (TA on CSC 2302), "
        "a.benali@aui.ma (professor). Password aui-demo.",
        "Accepted when a supervisor can: Sara Quiet-ask on CSC 2302; Alice claim "
        "and Help Coach; Benali stamp a KB draft; all three without changing "
        "accounts’ global role — only the course picker.",
    ),
    "Ask Triage quality (Obj. 2)": (
        "Evidence: reports/final_report/classifier_evaluation.json, "
        "matcher_evaluation.json, gold_label_evaluation.json, plus "
        "backend/models/*.joblib. Concepts measured: category accuracy / macro-F1 "
        "(Analyzer) and assigned-TA accuracy / macro-F1 (Matcher).",
        "Accepted when those files are in the repo with an honesty note: CV n=156 "
        "is synthetic/curated; Matcher holdout is silver demo names; gold n=80 is "
        "curated, not a section lab. Do not cite them as live AUI quality. "
        "Optional upgrade: ≥40 human_gold rows (docs/gold_label_lab.md).",
    ),
    "Complete triage loop (Obj. 3)": (
        "Evidence: one walkthrough that hits every gate. POST /requests/ writes "
        "the ask + pending knowledge_entries row. POST /ta/assist/ stays on the "
        "TA screen. Professor sets knowledge status to approved. POST /agent/ask "
        "copies that stamp or returns should_seek_help below cosine 0.42. Rooms "
        "use Canvas/demo chapters. Revision Strategist is the local grade-gap "
        "page until Canvas grades exist.",
        "Accepted when the Study Agent quotes only approved rows; an unstamped "
        "draft is refused; Rooms show a chapter grid in demo mode; Canvas "
        "unsigned /canvas-demo is hidden when OFFICEHOURS_DEMO=false.",
    ),
    "Engineering reliability and privacy (Obj. 4)": (
        "Evidence: backend pytest; CI on backend + officehours-app; "
        "docs/SECURITY.md. Checks: Quiet status redaction, membership 403, rate "
        "limit, LTI bad-issuer reject, unsigned launch 404 off-demo.",
        "Accepted when backend tests pass, the product app builds, and a Quiet "
        "status lookup never includes student_name or email. A failed Canvas "
        "launch must not invent a session.",
    ),
}


DELIVERABLES = {
    "Deliverable 1: Product application": (
        "What we provide: the unified React/Vite/Tailwind app "
        "(frontend/officehours-app). Screens: opening story, login, course "
        "picker, Quiet/Identify ask, My asks, Study Agent, Rooms, classmate "
        "notes, Revision Strategist, TA desk + Help Coach, professor clusters / "
        "KB stamp / review insights. Accepted when Sara, Alice, and Benali flows "
        "run end-to-end on CSC 2302 from ./scripts/run_product.sh."
    ),
    "Deliverable 2: Backend platform": (
        "What we provide: FastAPI app.main:app. Routes: /auth, /requests "
        "(Ask Triage), /ta (claim, assist, reply), /knowledge (stamp), /agent/ask "
        "(Study Agent), /help-room (Rooms), /actions/recommendations (planner "
        "cards), /lti/* and /canvas (launch + sync), /ws (course-scoped hub), "
        "/analytics. Persistence: SQLAlchemy, SQLite default, Postgres via "
        "DATABASE_URL. Accepted when backend pytest passes."
    ),
    "Deliverable 3: Trained models and evaluation reports": (
        "What we provide: request_classifier.joblib (Analyzer category), "
        "matcher_classifier.joblib (demo-TA names; live matching uses tag overlap "
        "+ queue), synthesizer_ranker.joblib (hint style), "
        "learning_style_classifier.joblib. Reports: classifier / matcher / gold "
        "JSON+MD under reports/final_report/. Accepted when each report states "
        "n, accuracy, macro-F1, and data class (synthetic / silver / curated gold)."
    ),
    "Deliverable 4: Documentation and defense pack": (
        "What we provide: docs/product_overview.md, glossary.md, "
        "system_architecture.md, ai_nlp_design.md, training_data.md, "
        "defense_crib.md, gold_label_lab.md, SECURITY.md, ops_scale.md. Accepted "
        "when Dr. Hourrane can run the crib demo and read what each agent is "
        "(classifier vs retrieval vs rule table) without inventing a chatbot."
    ),
    "Deliverable 5: Demo and deployment assets": (
        "What we provide: ./scripts/run_product.sh (OFFICEHOURS_DEMO=true), "
        "official SSE poster, Swagger at /docs, and the community checklist: "
        "demo off, Canvas LTI key + API token, HTTPS CORS, Postgres, keep "
        "external LLM off and rate limit on. Accepted when those steps are "
        "written and the demo script boots :5180 + :8000."
    ),
}


TIMELINE = {
    "1. Definition & Background": (
        "Output: frozen research question, in/out-of-scope list, Quiet-ask PII "
        "rule (store id, never show name on status), and this CSC proposal for "
        "Dr. Hourrane (EGR 4402).",
        "Sep 01, 2026",
        "Oct 01, 2026",
        "Milestone 1: supervisor-approved problem, product vision, and this "
        "proposal. Evidence: signed scope + repo docs/proposal.md / this .docx.",
    ),
    "2. Investigation / Requirements": (
        "Output: related-work comparison (Canvas tickets, RAG tutors, FIFO "
        "queues, hosted chatbots); locked LTI 1.3 + OFFICEHOURS_DEMO contract; "
        "locked training files (labeled_requests*.csv, matcher silver, gold n=80).",
        "Sep 15, 2026",
        "Oct 06, 2026",
        "Requirements notes in docs/; related-work section of this proposal; "
        "evaluation files present under reports/final_report/.",
    ),
    "3. Design / Research Design": (
        "Output: ERD (users–memberships–requests–knowledge_entries); API "
        "contracts POST /requests/, /ta/assist/, /agent/ask, /ws; UI map "
        "/student /ta /professor; agent behavior (joblib vs retrieval vs rules).",
        "Sep 20, 2026",
        "Oct 06, 2026",
        "Milestone 2 design freeze: diagrams/ + architecture doc + this table’s "
        "technical design row implemented as written APIs.",
    ),
    "4. Development / Experimentation": (
        "Output: running routers, joblib artifacts, Ask Triage on submit, Rooms, "
        "Canvas launch/sync, Revision Strategist page, WebSocket hub, demo seeds "
        "(Sara/Alice/Benali, CSC 2302).",
        "Oct 06, 2026",
        "Nov 11, 2026",
        "Milestone 3: Quiet ask → TA Help Coach → professor stamp → Study Agent "
        "quote-or-refuse works in OFFICEHOURS_DEMO=true.",
    ),
    "5. Validation & Evaluation": (
        "Output: pytest suite; classifier/matcher/gold JSON; Quiet-ask E2E on "
        "CSC 2302; CI green on backend + officehours-app; honesty notes in the "
        "evaluation files.",
        "Nov 11, 2026",
        "Dec 01, 2026",
        "Passing tests in CI; evaluation JSON/MD under reports/; walkthrough "
        "logged in docs/fyp_evidence.md.",
    ),
    "6. Finalization & Communication": (
        "Output: defense_crib.md, official SSE poster, run_product.sh, "
        "LTI/Postgres handover (ops_scale.md, SECURITY.md), live demo :5180.",
        "Dec 01, 2026",
        "Dec 09, 2026",
        "Milestone 4: defense pack + Innovation Day poster + community deploy "
        "checklist ready.",
    ),
}


RESOURCES = {
    "Developer workstation or cloud VM": (
        "Purpose: edit the React/FastAPI app, train MiniLM+LogReg joblibs "
        "(train_classifier.py etc.), run pytest, and host the local demo "
        "(:5180 + :8000).",
        "Availability: personal laptop. Optional cloud VM only if local RAM is "
        "too small for sentence-transformers (tests use "
        "OFFICEHOURS_CLUSTERING_BACKEND=lexical to skip the model download).",
    ),
    "GitHub repository and CI": (
        "Purpose: version control, regression on backend tests + officehours-app "
        "build, and the documentation pack examiners read.",
        "Availability: github.com/abssisophia9-hub/officehours-ai. CI does not "
        "build the archived kiosk/TA/professor shells.",
    ),
    "Python 3.12 and Node.js toolchains": (
        "Purpose: backend/venv (FastAPI, SQLAlchemy, scikit-learn, "
        "sentence-transformers) and frontend/officehours-app (Vite, React 19, "
        "Tailwind).",
        "Availability: open source; venv created in setup. System package "
        "python3.12-venv is required to create it.",
    ),
    "Canvas LMS with LTI 1.3 keys": (
        "Purpose: signed launch so a student opens OfficeHours from inside the "
        "Canvas course already authenticated, and REST sync of modules/files "
        "into pending knowledge_entries.",
        "Availability: AUI IT must issue an LTI 1.3 developer key and a Canvas "
        "API token. Until then OFFICEHOURS_DEMO=true uses the local mirror and "
        "unsigned simulator (hidden when demo is off).",
    ),
}


BUDGET = {
    "Software stack": (
        "--",
        "0",
        "0",
        "React, Vite, Tailwind, FastAPI, SQLAlchemy, sentence-transformers "
        "(MiniLM), scikit-learn, pytest. No paid OpenAI/Claude call on the "
        "assessed intake path.",
    ),
    "Optional cloud compute": (
        "1",
        "0-500",
        "0-500",
        "Only if the laptop cannot load MiniLM for a live demo. Tests do not "
        "need this (lexical clustering).",
    ),
    "Innovation Day poster printing (36 x 24)": (
        "1",
        "150-400",
        "150-400",
        "Physical print of the official SSE 14.5×19 in early-stage poster "
        "(docs/presentations/).",
    ),
    "Estimated total": (
        "",
        "",
        "0-900",
        "Core software work is 0 MAD. Optional print + VM only.",
    ),
}


RISKS = {
    "Canvas / IT credentials delayed": (
        "Medium",
        "High",
        "Concept at risk: live Canvas launch and live module sync. Fallback: "
        "OFFICEHOURS_DEMO=true, local module mirror, unsigned /canvas-demo "
        "(404 when demo is off). Mitigation: ready IT email in "
        "docs/session_log_opening_auth_canvas.md (LTI key + API token + Entra "
        "client id). Defense claim stays: code exists; campus credentials do not.",
    ),
    "Model metrics over-claimed versus real AUI student text": (
        "Medium",
        "High",
        "Concept at risk: calling lab CV “campus quality.” Mitigation: honesty "
        "table in the evaluation reports (synthetic / silver / curated gold). "
        "Fallback: run gold_label_lab.md (≥40 human_gold from one section). Do "
        "not turn on a hosted LLM for the defense unless she approves that "
        "question text leaves the machine.",
    ),
    "Scope creep into hardware kiosk, extra agents, or multi-campus deployment": (
        "Medium",
        "High",
        "Concept at risk: the product becomes three archived frontends or a "
        "chatbot. Mitigation: freeze the loop — Ask Triage, Help Coach, KB "
        "stamp, Study Agent refuse, Rooms, Canvas path. Out of scope stays "
        "kiosk :5173–5175, NFC/barcode, portal scrape, four backend services.",
    ),
    "Privacy leak on Quiet asks": (
        "Medium",
        "High",
        "Concept at risk: a receipt or classmate list shows the asker’s name. "
        "Mitigation: GET /requests/{id}/status strips identity; GET /requests/ "
        "for classmates never lists Quiet rows; tests lock both. Fallback: "
        "docs/SECURITY.md checklist before any public URL.",
    ),
}


ETHICS = {
    "Human participants / user studies": (
        "Does the project collect data from or test with people? What "
        "consent/approval is required?",
        "Optional walkthroughs/surveys with classmates and TAs use informed "
        "consent and are not linked to grades. A legacy pilot (n=8 students, "
        "n=4 professors) already exists. Any new gold-label lab (TAs marking "
        "gold_category / gold_assigned_ta) uses the same consent. Demo accounts "
        "are fictional (Sara, Alice, Benali).",
    ),
    "Privacy & personal data": (
        "What personal/sensitive data are collected or processed? How will "
        "access, storage, minimization, and retention be handled?",
        "Processed: email, optional student_id, ask text, course membership, "
        "session token. Quiet ask: name hidden on staff queue and status; "
        "created_by_user_id kept for My asks only. Sensitive categories "
        "(integrity, grading, accommodation, retake, emotional) are blocked "
        "from Rooms and routed privately. Demo DB is synthetic. Retention is "
        "course-term, not a permanent archive. PII stays out of application logs "
        "where possible.",
    ),
    "Cybersecurity": (
        "What security threats or misuse cases are relevant? What safeguards "
        "and testing are planned?",
        "Threats: stolen session, cross-course IDOR, prompt injection into "
        "/agent/ask, malicious PDF/DOCX upload, unsigned Canvas impersonation. "
        "Safeguards: membership checks, rate limits, professor stamp before any "
        "Study Agent quote, upload magic-byte validation, LTI JWT/JWKS, demo "
        "routes off when OFFICEHOURS_DEMO=false. Tests cover Quiet redaction "
        "and unsigned-launch 404.",
    ),
    "Legal / regulatory / licensing": (
        "Are there sector-specific rules, software licenses, data licenses, "
        "copyright, or API terms to consider?",
        "Canvas LTI/API terms and Microsoft Entra terms apply once IT issues "
        "keys. Core stack is open source (MIT/BSD/Apache as packaged). We do "
        "not scrape the AUI portal. Training CSVs are synthetic/curated, not "
        "real student mail. Stamped KB is professor-authored course material.",
    ),
    "Engineering / technical standards": (
        "Identify standards, protocols, or best-practice guidelines relevant "
        "to the work.",
        "HTTP/JSON REST; WebSocket /ws; Canvas LTI 1.3 (OIDC + JWT RS256 / "
        "JWKS); optional OIDC to Entra; PBKDF2 sessions; OWASP-style hardening "
        "in docs/SECURITY.md (authz, rate limit, upload, error texts without "
        "stack traces).",
    ),
    "Responsible use of AI tools": (
        "If AI tools are used for coding, research, writing, design, or "
        "analysis, explain how outputs will be verified, attributed where "
        "required, and used transparently.",
        "Assistants may speed coding or drafting. Critical logic is reviewed "
        "and covered by pytest. Claims in this proposal cite repository "
        "evidence (evaluation JSON, tests, docs), not generated prose alone. "
        "The product’s assessed agents are classifiers and retrieval, not a "
        "hidden ChatGPT call.",
    ),
    "AI system risks (if applicable)": (
        "Consider bias, hallucination, explainability, data provenance, model "
        "limitations, user oversight, and failure modes.",
        "Risks: wrong category, wrong TA, a fluent but unsound hint, Study "
        "Agent inventing a syllabus. Controls: published lab metrics with "
        "limits; Matcher on a live course uses tag+queue not the demo-name "
        "joblib; Synthesizer/Study Agent copy stored stamped text or refuse "
        "(0.42); Help Coach never publishes; professor stamp is the gate; "
        "staff can override every label. Failure mode: unclassifiable text → "
        "category uncategorized, still reaches a TA.",
    ),
    "Environmental / accessibility considerations": (
        "Where relevant, consider energy/resource use, accessibility, "
        "inclusion, and deployment context.",
        "Local MiniLM (~tens of MB) avoids a hosted-LLM energy/cost bill on "
        "the assessed path. Quiet Mode is the inclusion feature for students "
        "who will not ask under their name. UI is English (AUI instruction), "
        "with role labels and a status receipt that does not require a second "
        "login. Contrast and readable type are part of the product app theme.",
    ),
}


PARAS = {
    "OfficeHours AI is a packaged, multi-role campus web application that reduces faculty and TA communication overload during high-demand periods such as finals week. Students can submit either Quiet (privacy-preserving) or identified asks and choose a preferred help mode: message, face-to-face, or online. The system uses an Ask Triage pipeline--Analyzer, Matcher, and Synthesizer--to classify requests, group repeated topics, recommend appropriate TA/professor support, and draft teaching guidance from approved materials. The AI does not replace office hours or human interaction; it supports decision-making so professors and TAs can respond faster, more fairly, and with better context. TAs work through a live WebSocket queue with Help Coach assistance, while professors approve knowledge-base drafts before the Study Agent can answer from them. Canvas LTI 1.3 and materials sync support future campus deployment, and demo mode provides walkthrough accounts for evaluation. Success will be measured through automated tests, model evaluation reports, privacy checks, end-to-end product walkthroughs, and clear documentation of deployment readiness and limitations.": (
        "OfficeHours AI is one campus web product: a React 19 / Vite / Tailwind app "
        "(port 5180) talking to one FastAPI process (port 8000) over REST, plus a "
        "course-scoped WebSocket at /ws for live queue events. Students submit an "
        "ask as Quiet (name hidden) or identified, and pick help_mode = message, "
        "face_to_face, or online_meeting. On POST /requests/, Ask Triage runs "
        "three local specialists. Analyzer (MiniLM + request_classifier.joblib) "
        "writes category, urgency, difficulty, and estimated minutes. Matcher "
        "writes assigned_ta and alternative_ta from this course’s TA memberships "
        "and queue depth. Synthesizer retrieves the nearest professor-approved "
        "note (or teaching-bank row) by cosine similarity and copies a "
        "student_hint — it does not write a new paragraph. Clustering shares "
        "cluster_id when cosine ≥ 0.72 so repeated topics sit together. TAs work "
        "a live desk and may call Help Coach (POST /ta/assist/), whose draft "
        "stays on the TA screen until the TA sends it. Professors stamp "
        "knowledge_entries; only status=approved rows may be quoted by the Study "
        "Agent (POST /agent/ask), which refuses below similarity 0.42. Canvas "
        "LTI 1.3 is the campus launch path; OFFICEHOURS_DEMO=true seeds Sara / "
        "Alice / Benali for evaluation. Success is a demoable loop, passing "
        "tests, published lab metrics with honesty notes, and a documented "
        "community hand-off — not a claim that the lab F1 is live AUI quality."
    ),
    "Can an AI-assisted office-hours triage system reduce faculty communication overload and improve student comfort in seeking academic help during peak academic periods? Operationally, finals week often creates repeated conceptual questions, long waits, scattered messages, and underused approved answers, while some students avoid asking when their identity feels too exposed.": (
        "Research question: Can a course-scoped office-hours triage system reduce "
        "repeated faculty/TA load and raise student comfort in asking, without "
        "replacing the human session? Operationally, finals week produces the "
        "same conceptual ask many times (e.g. red-black rotations), long waits "
        "in email/Canvas inbox, and unused FAQ text that never reaches the next "
        "student. Some students will not submit if the form forces a name. The "
        "system under test therefore has to (1) structure each ask, (2) cluster "
        "repeats, (3) route a TA, (4) offer a Quiet receipt, and (5) let a "
        "professor stamp the only text an agent may later quote."
    ),
    "At Al Akhawayn University, office hours and Canvas are central to undergraduate academic support. Existing LMS tools organize courses and materials, but they do not triage live academic requests, recommend TA staffing, cluster repeated questions, or enforce professor approval before an agent answers from course content. OfficeHours AI builds on prior campus prototype ideas by moving toward one unified product: a single app, role-per-course access, privacy-aware request intake, and a Canvas-ready deployment path.": (
        "At Al Akhawayn University (SSE, American-style undergraduate curriculum), "
        "Canvas and scheduled office hours are the official support channels. "
        "Canvas already stores modules, files, grades, and an inbox; it does not "
        "classify a live conceptual ask, assign a TA by expertise and queue, "
        "group five rotations questions into one cluster, or require a professor "
        "stamp before a software agent quotes the syllabus. OfficeHours AI sits "
        "beside Canvas as a launchable LTI tool: memberships come from the "
        "launch (Learner / TA / Instructor), materials sync into pending KB "
        "rows, and the product app is the desk. Motivation: keep office hours "
        "human, and make the queue and the approved answers machine-readable."
    ),
    "The intended users are AUI students, TAs, and professors. Students benefit from Quiet/identified asks, Rooms, and an approved Study Agent. TAs benefit from a live queue and Help Coach support. Professors benefit from clustered topics, review insights, knowledge-base approval, and Canvas sync. Secondary beneficiaries include SSE teaching support, AUI IT for future LMS integration, FYP examiners, and peer campuses evaluating responsible AI-assisted office-hours systems.": (
        "Primary users, role per course: (1) Students — Quiet or identified ask, "
        "status-by-code, Study Agent on stamped notes only, named Rooms, "
        "classmate notes, Revision Strategist page. (2) TAs — staff on a course "
        "they already completed, not classmates in that section; live queue, "
        "claim, Help Coach, optional group meeting. (3) Professors — cluster "
        "command center, planner cards (group review / FAQ / 1:1), KB stamp, "
        "Canvas sync, review insights. Same login can be TA on CSC 2302 and "
        "student on MTH 1304. Secondary: SSE teaching support, AUI IT (LTI + "
        "Entra), examiners, peer campuses."
    ),
    "In scope: a unified React/FastAPI product; Ask Triage using local models; Help Coach; Study Agent with professor knowledge-base approval; Rooms for classmate support; peer notes; WebSocket queues; Canvas launch/sync and LTI 1.3 path; demo/community deployment modes; automated tests; and defense documentation. Out of scope: physical kiosk, barcode, or NFC hardware; claims of live AUI longitudinal accuracy without human-labeled data; and production Microsoft SSO without IT credentials. Constraints include the FYP schedule, local compute for sentence-transformer models, privacy for Quiet asks, and dependence on Canvas/IT for full campus rollout.": (
        "In scope: one React SPA + one FastAPI process; SQLite (demo) / Postgres "
        "(host); Ask Triage (Analyzer/Matcher/Synthesizer joblibs + retrieval); "
        "clustering; Help Coach; professor-gated Study Agent; Rooms; peer notes; "
        "planner cards / group meetings; WebSocket /ws; Canvas LTI 1.3 + REST "
        "sync; OFFICEHOURS_DEMO vs community; pytest; defense docs. Out of "
        "scope: kiosk/NFC/barcode hardware; archived frontends on :5173–5175 as "
        "the product; portal/SIS scrape; a hosted LLM on the assessed intake "
        "path; claiming gold n=80 as campus quality; Microsoft SSO in production "
        "before IT issues client_id/secret. Constraints: FYP calendar, laptop "
        "compute for MiniLM, Quiet-ask privacy, IT for live Canvas."
    ),
    "Related work spans four main areas: (1) LMS/Canvas office-hours and help-desk plugins, which track requests but usually lack course-scoped AI triage and professor-gated retrieval; (2) academic question-answering and RAG tutors, which may answer from uncurated sources without a human publication gate; (3) queue-management and TA-assignment systems, which often rely on FIFO rules rather than semantic clustering or staffing recommendations; and (4) campus chatbot pilots, which may depend on external prompted LLMs. OfficeHours AI builds on these ideas while focusing on AUI-specific role-per-course semantics, privacy-preserving asks, locally evaluated models, and a single deployable workflow.": (
        "Related work, and what this product adds. (1) LMS / Canvas inbox and "
        "office-hours plugins — they store tickets and files; they do not run "
        "Analyzer→Matcher→Synthesizer or require a stamp before an agent quotes "
        "a note. (2) Academic RAG / tutors (including hosted GPT/Claude wrappers) "
        "— they generate answers from a corpus; without a professor publication "
        "gate they can invent a syllabus. OfficeHours retrieval copies stamped "
        "text or refuses. (3) Queue / helpdesk products — FIFO or single-assignee "
        "rules; they do not embed asks or suggest group_session when cluster "
        "size ≥ 3. (4) Campus chatbot pilots — usually one prompted LLM with "
        "web tools; hard to score on category/TA F1 for a capstone. We keep "
        "local, measured classifiers on intake and a human stamp on anything "
        "students read from an agent."
    ),
    "Existing solutions often fall into one of three categories: they manage queues without intelligent triage, answer students without professor control of approved knowledge, or use opaque external LLMs that are difficult to evaluate responsibly in an assessed capstone project. The need is for a campus-ready system that combines privacy-preserving intake, local Ask Triage, TA assistance, professor knowledge-base control, peer support, and Canvas integration with transparent evaluation.": (
        "The gap is not “no messaging tool.” Canvas inbox, email, and generic "
        "bots already exist. The gap is a campus-ready loop that (a) structures "
        "an ask (category, urgency, TA, hint) with published lab scores, (b) "
        "hides identity on Quiet asks, (c) lets a TA claim and use Help Coach "
        "without publishing to students, (d) lets a professor stamp the only "
        "paragraphs an agent may quote, (e) clusters repeats into one group "
        "meeting, and (f) launches from Canvas LTI instead of a second password "
        "site. OfficeHours AI is that loop, evaluated with tests and honesty "
        "notes — not a new embedding algorithm."
    ),
    "The core contribution is the design and implementation of OfficeHours AI: a multi-role campus office-hours triage application with (i) custom Ask Triage agents for analysis, matching, and synthesis; (ii) Help Coach for TA support during sessions; (iii) a professor-gated Study Agent; (iv) Rooms and review insights for repeated topics; and (v) Canvas launch/materials integration. The innovation is meaningful system integration and context-specific adaptation for AUI, not a claim of inventing embeddings, classifiers, or LTI.": (
        "Contribution (what we actually ship): (i) Ask Triage — three local "
        "specialists on submit (classifier + roster match + retrieval hint); "
        "(ii) Help Coach — four TA-only templates on the same retrieval; "
        "(iii) Study Agent — cosine search over approved KB, refuse < 0.42; "
        "(iv) Rooms + professor review insights — named classmate forum with "
        "Canvas-module chapters, plus cluster planner cards; (v) Canvas LTI 1.3 "
        "launch and REST materials sync into pending_review. Innovation is the "
        "AUI integration (role-per-course, Quiet ask, professor stamp, LTI), "
        "not inventing MiniLM, logistic regression, or LTI 1.3."
    ),
    "The methodology follows iterative software prototyping with continuous evaluation. The architecture uses a React 19 + Vite + Tailwind single-page application, a FastAPI/Uvicorn backend, SQLAlchemy persistence with SQLite by default and a PostgreSQL path for deployment, and a WebSocket hub for live queues. The Ask Triage pipeline uses local sentence-transformer embeddings and scikit-learn classifiers to analyze, route, and summarize requests. Help Coach supports TAs during sessions, while the Study Agent is restricted to professor-approved knowledge-base entries. Data sources include synthetic and curated training examples, silver labels for matcher development, held-out gold-label items where available, and demo course seeds. The development process is: implement features, train/evaluate models, run integration tests, harden the demo, and document assumptions and limitations.": (
        "Method: iterative software prototyping with a fixed evaluation contract. "
        "Stack: React 19 + Vite + Tailwind (SPA, :5180); FastAPI/Uvicorn (:8000); "
        "SQLAlchemy + SQLite (officehours.db) or Postgres (DATABASE_URL); "
        "in-process WebSocket hub (realtime/hub.py). AI layer — four tools, not "
        "a chatbot. MiniLM (all-MiniLM-L6-v2) embeds a sentence. Logistic "
        "regression joblibs pick a class (Analyzer category; demo Matcher names; "
        "style ranker). Cosine similarity retrieves the nearest stored paragraph. "
        "Fixed tables fill wait/difficulty and planner actions (1:1 / FAQ / "
        "group_session). Training data: labeled_requests*.csv (~156 Analyzer "
        "rows, synthetic/curated); matcher silver pairs to demo TAs; teaching-bank "
        "CSVs; gold n=80 curated; Alice demo pass n=20 (cite as demo-TA, not a "
        "section lab). Process: implement the route → train/eval the joblib → "
        "pytest the privacy/KB/LTI gates → document limits. Hosted OpenAI/Claude "
        "is not on the assessed path; a later bake-off would be a separate, "
        "supervised change."
    ),
    "Evaluation combines software, model, privacy, and product evidence: (1) functional, integration, and security tests for authentication, triage, TA staffing, knowledge-base approval, Rooms, Canvas launch, and uploads; (2) Analyzer cross-validation and Matcher holdout reports; (3) gold-label evaluation on curated held-out office-hours-style items; (4) manual walkthroughs from Quiet ask to TA Help Coach, professor approval, and Study Agent answer; (5) privacy checks confirming that Quiet asks do not expose identity through status flows; and (6) a deployment checklist for Canvas LTI. Baselines include non-triaged queues, separate dashboards, and ungated chatbot behavior. Acceptance requires a demoable end-to-end product, passing tests, transparent metrics, and honest limits on synthetic/silver/gold data.": (
        "Evaluation has four layers, each with a named artifact. (1) Software: "
        "backend pytest on auth, Quiet redaction, Ask Triage fields, TA claim, "
        "KB approve/refuse, Rooms, LTI/Canvas launch, uploads, rate limit. "
        "(2) Models: classifier_evaluation.json (stratified CV, n=156), "
        "matcher_evaluation.json (silver holdout), gold_label_evaluation.json "
        "(n=80 curated). Report accuracy and macro-F1; never relabel silver as "
        "gold. (3) Product walkthrough: Sara Quiet ask → Alice Help Coach → "
        "Benali stamp → Study Agent quote-or-refuse; Rooms chapter pick. "
        "(4) Deploy checklist: OFFICEHOURS_DEMO, LTI key, Canvas token, HTTPS "
        "CORS, Postgres, LLM flag off. Baselines (qualitative): inbox/FIFO, "
        "three old shells, ungated chatbot. Acceptance: demoable loop, green "
        "tests, honesty notes — not a live-campus F1."
    ),
}


def apply_lifecycle(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 3:
            continue
        key = cell_text(cells[0])
        if key in LIFECYCLE:
            purpose, acts = LIFECYCLE[key]
            set_cell(cells[1], purpose)
            set_cell(cells[2], acts)
            n += 1
    return n


def apply_diff(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 4:
            continue
        key = cell_text(cells[0])
        if key in DIFF:
            a, b, c = DIFF[key]
            set_cell(cells[1], a)
            set_cell(cells[2], b)
            set_cell(cells[3], c)
            n += 1
    return n


def apply_success(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 3:
            continue
        key = cell_text(cells[0])
        if key in SUCCESS:
            m, t = SUCCESS[key]
            set_cell(cells[1], m)
            set_cell(cells[2], t)
            n += 1
    return n


def apply_deliverables(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 2:
            continue
        key = cell_text(cells[0])
        if key in DELIVERABLES:
            set_cell(cells[1], DELIVERABLES[key])
            n += 1
    return n


def apply_timeline(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 5:
            continue
        key = cell_text(cells[0])
        if key in TIMELINE:
            tasks, start, end, ev = TIMELINE[key]
            set_cell(cells[1], tasks)
            set_cell(cells[2], start)
            set_cell(cells[3], end)
            set_cell(cells[4], ev)
            n += 1
    return n


def apply_resources(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 3:
            continue
        key = cell_text(cells[0])
        if key in RESOURCES:
            purpose, src = RESOURCES[key]
            set_cell(cells[1], purpose)
            set_cell(cells[2], src)
            n += 1
    return n


def apply_budget(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 5:
            continue
        key = cell_text(cells[0])
        if key in BUDGET:
            q, u, tot, just = BUDGET[key]
            set_cell(cells[1], q)
            set_cell(cells[2], u)
            set_cell(cells[3], tot)
            set_cell(cells[4], just)
            n += 1
    return n


def apply_risks(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 4:
            continue
        key = cell_text(cells[0])
        if key in RISKS:
            lik, imp, mit = RISKS[key]
            set_cell(cells[1], lik)
            set_cell(cells[2], imp)
            set_cell(cells[3], mit)
            n += 1
    return n


def apply_ethics(tbl) -> int:
    n = 0
    for tr in tbl.findall(f"{W}tr")[1:]:
        cells = row_cells(tr)
        if len(cells) < 3:
            continue
        key = cell_text(cells[0])
        if key in ETHICS:
            q, resp = ETHICS[key]
            set_cell(cells[1], q)
            set_cell(cells[2], resp)
            n += 1
    return n


def apply_project_type(tbl) -> int:
    rows = tbl.findall(f"{W}tr")
    if len(rows) < 2:
        return 0
    cells = row_cells(rows[1])
    if not cells:
        return 0
    set_cell(
        cells[0],
        "Software development project: one React SPA (port 5180) + one FastAPI "
        "process (port 8000). AI on the assessed path is local MiniLM embeddings "
        "+ scikit-learn classifiers and retrieval over professor-stamped notes — "
        "not a hosted ChatGPT/Claude call, and not a hardware kiosk.",
    )
    return 1


HANDLERS = {
    "Phase | Purpose | Activities": apply_lifecycle,
    "Criterion | Existing Work / Baseline | Proposed Approach | Expected Improvement / Difference": apply_diff,
    "Objective / Claim | Metric or Evidence | Target / Acceptance Criterion": apply_success,
    "Deliverable | Description / Acceptance Condition": apply_deliverables,
    "Phase / Milestone | Major Tasks / Output | Start | End | Evidence of Completion": apply_timeline,
    "Resource | Purpose | Availability / Source": apply_resources,
    "Item | Quantity | Unit Cost (MAD) | Total (MAD) | Justification": apply_budget,
    "Potential Risk | Likelihood | Impact | Mitigation / Fallback": apply_risks,
    "Consideration | Guiding Question | Project Response": apply_ethics,
}


def apply_paragraphs(body) -> int:
    n = 0
    for p in body.findall(f"{W}p"):
        key = para_text(p)
        if key in PARAS:
            set_runs_text(p, PARAS[key])
            n += 1
    return n


def main() -> int:
    if not DOCX.exists():
        print("missing", DOCX, file=sys.stderr)
        return 1
    with ZipFile(DOCX) as zf:
        xml = zf.read("word/document.xml")
        others = {name: zf.read(name) for name in zf.namelist() if name != "word/document.xml"}

    root = ET.fromstring(xml)
    body = root.find(f"{W}body")
    original_runs = [node.text or "" for node in root.iter(f"{W}t")]
    counts: dict[str, int] = {}
    for tbl in body.findall(f"{W}tbl"):
        rows = tbl.findall(f"{W}tr")
        header = " | ".join(cell_text(tc) for tc in row_cells(rows[0])) if rows else ""
        if header.startswith("Software Development Project") or header.startswith(
            "Web application"
        ):
            counts["project_type"] = apply_project_type(tbl)
            continue
        # project type table is 2 rows, first cell is the type name
        if len(rows) == 2 and "Software Development" in cell_text(row_cells(rows[0])[0]):
            counts["project_type"] = apply_project_type(tbl)
            continue
        for prefix, fn in HANDLERS.items():
            if header.startswith(prefix.split(" | ")[0]) and prefix.split(" | ")[1] in header:
                counts[fn.__name__] = fn(tbl)
                break
        else:
            if header.startswith("Software Development"):
                counts["project_type"] = apply_project_type(tbl)

    counts["paragraphs"] = apply_paragraphs(body)

    # Also catch Project Type if header row is a single merged cell
    if "project_type" not in counts:
        for tbl in body.findall(f"{W}tbl"):
            blob = " ".join(cell_text(tc) for tr in tbl.findall(f"{W}tr") for tc in row_cells(tr))
            if "locally trained custom agents" in blob or "Software Development Project" in blob:
                if apply_project_type(tbl):
                    counts["project_type"] = 1

    # Do not re-serialize with ElementTree. It renames Word prefixes
    # (wpc, mc, cx, …) to ns1/ns2, and Microsoft Word then reports
    # "unreadable content" and offers to repair the file.
    raw = xml.decode("utf-8")
    pairs: list[tuple[str, str]] = []
    for node, old in zip(root.iter(f"{W}t"), original_runs):
        new = node.text or ""
        if old and old != new:
            pairs.append((old, new))
    pairs.sort(key=lambda item: len(item[0]), reverse=True)

    def xml_escape(value: str) -> str:
        return (
            value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )

    for old, new in pairs:
        if old not in raw:
            print("WARNING missing original text:", old[:80], file=sys.stderr)
            continue
        raw = raw.replace(old, xml_escape(new), 1)
    new_xml = raw.encode("utf-8")
    tmp = DOCX.with_suffix(".docx.tmp")
    with ZipFile(tmp, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("word/document.xml", new_xml)
        for name, data in others.items():
            zf.writestr(name, data)
    tmp.replace(DOCX)
    print("updated", DOCX)
    print("counts", counts)
    missing = [name for name, fn in (
        ("lifecycle", "apply_lifecycle"),
        ("diff", "apply_diff"),
        ("success", "apply_success"),
        ("deliverables", "apply_deliverables"),
        ("timeline", "apply_timeline"),
        ("resources", "apply_resources"),
        ("budget", "apply_budget"),
        ("risks", "apply_risks"),
        ("ethics", "apply_ethics"),
    ) if counts.get(fn, 0) == 0]
    if missing:
        print("WARNING unmatched tables:", missing)
        return 2
    if counts.get("paragraphs", 0) < 8:
        print("WARNING few paragraphs replaced", counts.get("paragraphs"))
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
