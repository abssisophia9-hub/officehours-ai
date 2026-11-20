#!/usr/bin/env python3
"""
build_defense.py — Fill Sophia's EXISTING Capstone Defense template in place.

STRICT (do not violate):
  1. Open ONLY Capstone_Defense_Presentation_Sophia_Abssi_min.pptx via
     Presentation(r"C:\\Users\\pc\\Downloads\\..._min.pptx")
     — NEVER Presentation() with no arguments.
  2. NEVER call prs.slides.add_slide() — no blank layouts, no green/white cards,
     no new rectangles/backgrounds. Dark futuristic chrome stays untouched.
  3. Edit text inside existing shapes (including Group children).
     Prefer paragraph.runs[0].text; if runs empty, add_run() with #F8FAFC Calibri.
  4. Save ONLY to Capstone_Defense_MY_TEMPLATE_FILLED.pptx.

Run on the Windows machine that has the template:

    pip install python-pptx
    python scripts/build_defense.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Iterator

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Pt

TEMPLATE_PATH = r"C:\Users\pc\Downloads\Capstone_Defense_Presentation_Sophia_Abssi_min.pptx"
OUTPUT_PATH = r"C:\Users\pc\Downloads\Capstone_Defense_MY_TEMPLATE_FILLED.pptx"

NEW_RUN_FONT = "Calibri"
NEW_RUN_SIZE_PT = 16
NEW_RUN_COLOR = RGBColor(0xF8, 0xFA, 0xFC)  # #F8FAFC — readable on dark slides

PRODUCT_LONG = (
    "OfficeHours AI: Bridging the academic help-seeking gap — "
    "a multi-persona AI and peer learning ecosystem"
)
HEADER = "OfficeHours AI — Campus Help Desk"
DEFENSE_DATE = "FALL 2026 | 09 December 2026"
OLD_TITLE = "AI-Driven Automation of Document Processing Workflows"


@dataclass
class WriteLedger:
    count: int = 0

    def record(self, slide_no: int, shape_index: str, text: str) -> None:
        self.count += 1
        preview = (text or "").replace("\n", " ").strip()
        if len(preview) > 40:
            preview = preview[:40] + "..."
        elif not preview:
            preview = "(empty)"
        print(f'[Slide {slide_no} | Shape {shape_index}] -> Replaced with: "{preview}"')


LEDGER = WriteLedger()


def walk_shapes(shapes, prefix: str = "") -> Iterator[tuple[str, object]]:
    for i, shape in enumerate(shapes):
        path = f"{prefix}{i}" if not prefix else f"{prefix}/{i}"
        yield path, shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk_shapes(shape.shapes, prefix=path)


def iter_text_shapes(slide) -> Iterator[tuple[str, object]]:
    for path, shape in walk_shapes(slide.shapes):
        if getattr(shape, "has_text_frame", False):
            yield path, shape


def shape_text(shape) -> str:
    if not getattr(shape, "has_text_frame", False):
        return ""
    return shape.text_frame.text or ""


def _style_new_run(run, *, size_pt: float = NEW_RUN_SIZE_PT) -> None:
    run.font.name = NEW_RUN_FONT
    run.font.size = Pt(size_pt)
    run.font.color.rgb = NEW_RUN_COLOR


def set_paragraph_text(paragraph, text: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> None:
    if paragraph.runs:
        paragraph.runs[0].text = text
        for run in paragraph.runs[1:]:
            run.text = ""
    else:
        run = paragraph.add_run()
        _style_new_run(run, size_pt=size_pt)
        run.text = text


def write_shape(
    shape,
    text: str,
    *,
    slide_no: int,
    shape_index: str,
    size_pt: float = NEW_RUN_SIZE_PT,
) -> bool:
    if shape is None or not getattr(shape, "has_text_frame", False):
        return False
    tf = shape.text_frame
    lines = (text if text is not None else "").split("\n")
    if not lines:
        lines = [""]
    if not tf.paragraphs:
        return False
    while len(tf.paragraphs) < len(lines):
        tf.add_paragraph()
    for i, para in enumerate(tf.paragraphs):
        set_paragraph_text(para, lines[i] if i < len(lines) else "", size_pt=size_pt)
    LEDGER.record(slide_no, shape_index, text)
    return True


def find_shapes(
    slide,
    *,
    exact: str | None = None,
    contains: str | None = None,
    name_contains: str | None = None,
    empty_only: bool = False,
    name_startswith: tuple[str, ...] | None = None,
) -> list[tuple[str, object]]:
    hits: list[tuple[str, object]] = []
    for path, shape in iter_text_shapes(slide):
        cur = shape_text(shape).strip()
        name = getattr(shape, "name", "") or ""
        if empty_only and cur:
            continue
        if exact is not None and cur != exact.strip():
            continue
        if contains is not None and contains.lower() not in cur.lower():
            continue
        if name_contains is not None and name_contains.lower() not in name.lower():
            continue
        if name_startswith is not None and not any(name.startswith(p) for p in name_startswith):
            continue
        hits.append((path, shape))
    return hits


def write_exact(slide, slide_no: int, old: str, new: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> int:
    n = 0
    for path, shape in find_shapes(slide, exact=old):
        if write_shape(shape, new, slide_no=slide_no, shape_index=path, size_pt=size_pt):
            n += 1
    return n


def write_contains(slide, slide_no: int, fragment: str, new: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> int:
    n = 0
    for path, shape in find_shapes(slide, contains=fragment):
        if write_shape(shape, new, slide_no=slide_no, shape_index=path, size_pt=size_pt):
            n += 1
    return n


def write_nth_empty(
    slide,
    slide_no: int,
    text: str,
    *,
    nth: int = 0,
    name_startswith: tuple[str, ...] = ("TextBox", "Rounded Rectangle", "Rectangle: Rounded"),
    size_pt: float = NEW_RUN_SIZE_PT,
) -> bool:
    empties = []
    for path, shape in iter_text_shapes(slide):
        name = getattr(shape, "name", "") or ""
        if "slide number" in name.lower():
            continue
        if not any(name.startswith(p) for p in name_startswith):
            continue
        if shape_text(shape).strip():
            continue
        empties.append((path, shape))
    if nth >= len(empties):
        return False
    path, shape = empties[nth]
    return write_shape(shape, text, slide_no=slide_no, shape_index=path, size_pt=size_pt)


def write_index(slide, slide_no: int, index: int, text: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> bool:
    """Write by top-level shape_index from slide_map.json."""
    try:
        shape = slide.shapes[index]
    except (IndexError, KeyError):
        return False
    if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
        for path, child in walk_shapes(shape.shapes, prefix=str(index)):
            if getattr(child, "has_text_frame", False):
                return write_shape(child, text, slide_no=slide_no, shape_index=path, size_pt=size_pt)
        return False
    return write_shape(shape, text, slide_no=slide_no, shape_index=str(index), size_pt=size_pt)


def scrub_headers(slide, slide_no: int) -> None:
    write_exact(slide, slide_no, OLD_TITLE, HEADER, size_pt=14)
    write_contains(slide, slide_no, "Document Processing Workflows", HEADER, size_pt=14)
    write_exact(slide, slide_no, "CDG Capital Gestion", "OfficeHours AI", size_pt=16)
    write_contains(slide, slide_no, "FALL 2025", DEFENSE_DATE, size_pt=12)
    write_exact(slide, slide_no, "Table of content", "Agenda", size_pt=18)
    write_exact(slide, slide_no, "Table of Content", "Agenda", size_pt=18)


def fill_title(slide, n: int) -> None:
    write_exact(slide, n, OLD_TITLE, PRODUCT_LONG, size_pt=28)
    write_index(slide, n, 7, PRODUCT_LONG, size_pt=28)
    write_contains(slide, n, "FALL 2025", DEFENSE_DATE, size_pt=14)
    write_contains(slide, n, "FALL 2026", DEFENSE_DATE, size_pt=14)
    write_index(slide, n, 10, DEFENSE_DATE, size_pt=14)


def fill_toc(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, OLD_TITLE, PRODUCT_LONG, size_pt=18)
    write_index(slide, n, 8, PRODUCT_LONG, size_pt=18)
    write_index(slide, n, 11, DEFENSE_DATE, size_pt=12)
    write_exact(slide, n, "Table of content", "Agenda", size_pt=20)
    write_index(slide, n, 20, "Agenda", size_pt=20)
    write_exact(slide, n, "Problem Statement & Motivation", "Problem & Motivation", size_pt=16)
    write_index(slide, n, 21, "Problem & Motivation", size_pt=16)
    write_exact(slide, n, "Introduction & Context", "Architecture & AI Surfaces", size_pt=16)
    write_index(slide, n, 22, "Architecture & AI Surfaces", size_pt=16)
    write_exact(slide, n, "CDG Capital Gestion", "OfficeHours AI", size_pt=16)
    write_index(slide, n, 23, "OfficeHours AI", size_pt=16)


def fill_mission(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Mission and Role", "Mission and Roles", size_pt=22)
    write_index(slide, n, 27, "Mission and Roles", size_pt=22)
    roles = [
        "Student: Quiet ask · Rooms · Study Agent\nPedagogy Agent · notes · Inbox",
        "TA: Live Queue · claim · Help Coach\nReply required before resolve",
        "Professor: Material stamp · Insights · Team\nOnly approved KB → /agent/ask",
    ]
    filled = 0
    for path, shape in iter_text_shapes(slide):
        if filled >= len(roles):
            break
        name = getattr(shape, "name", "") or ""
        cur = shape_text(shape).strip()
        if "slide number" in name.lower() or name.startswith("Graphic"):
            continue
        if "/" in path or not cur:
            if cur and any(
                k in cur
                for k in ("Problem", "Introduction", "Agenda", "Table", "FALL", "Mission", HEADER, OLD_TITLE)
            ):
                continue
            if not cur or "CDG" in cur or "financial" in cur.lower():
                if write_shape(shape, roles[filled], slide_no=n, shape_index=path, size_pt=14):
                    filled += 1
    while filled < len(roles):
        if write_nth_empty(slide, n, roles[filled], nth=0, size_pt=14):
            filled += 1
        else:
            break


def fill_intro(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Introduction & Context", "Introduction & Context", size_pt=22)
    write_index(slide, n, 18, "Introduction & Context", size_pt=22)
    write_exact(slide, n, "Manual Processing Challenges", "Campus Help-Seeking Gap", size_pt=18)
    write_index(slide, n, 24, "Campus Help-Seeking Gap", size_pt=18)
    body = (
        "AUI course help desk: one login, role per course via CourseMembership.\n"
        "Canvas-linked materials; FastAPI :8000 + React SPA :5180.\n"
        "TAs are staff on courses they already took — not classmates."
    )
    write_contains(slide, n, "financial institution", body, size_pt=14)
    write_contains(slide, n, "national investments", body, size_pt=14)
    write_index(slide, n, 22, body, size_pt=14)
    write_nth_empty(slide, n, body, nth=0, size_pt=14)


def fill_problem(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Problem Statement & Motivation", "Problem Statement & Motivation", size_pt=22)
    write_index(slide, n, 18, "Problem Statement & Motivation", size_pt=22)
    bullets = (
        "TAs drown in repeat questions across channels\n"
        "Students fear asking openly — Quiet ask needed\n"
        "Unconstrained ChatGPT invents the syllabus\n"
        "No professor-gated course answers today"
    )
    write_index(slide, n, 19, bullets, size_pt=15)
    write_nth_empty(slide, n, bullets, nth=0, size_pt=15)


def fill_related(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Existing Work & Literature Review", "Existing Work & Literature", size_pt=22)
    write_index(slide, n, 18, "Existing Work & Literature", size_pt=22)
    write_exact(slide, n, "Quick Walkthrough: Power Automate", "Gaps vs Piazza, Ed, ChatGPT", size_pt=18)
    write_index(slide, n, 27, "Gaps vs Piazza, Ed, ChatGPT", size_pt=18)
    body = (
        "Piazza/Ed: peer threads — no stamped agent gate\n"
        "Queue tools: staffing only — no Ask Triage ML\n"
        "Campus ChatGPT: unconstrained answers\n"
        "Our bet: classifiers + retrieval + professor stamp"
    )
    write_index(slide, n, 19, body, size_pt=14)
    write_nth_empty(slide, n, body, nth=0, size_pt=14)


def fill_solution(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Proposed Solution Overview", "Proposed Solution Overview", size_pt=22)
    write_index(slide, n, 13, "Proposed Solution Overview", size_pt=22)
    write_contains(slide, n, "Four-Flow", "Four AI Surfaces, One Product Gate", size_pt=18)
    write_contains(slide, n, "Methodology", "Four AI Surfaces, One Product Gate", size_pt=18)
    write_index(slide, n, 26, "Four AI Surfaces, One Product Gate", size_pt=18)
    cards = [
        "Ask Triage\nask_triage_service.py\nAnalyzer → Matcher → Synthesizer",
        "Help Coach\nhelp_coach_service.py\nTA mid-session · never publishes",
        "Study Agent\nkb_agent_service.py\nQuotes stamped KB · refuse 0.42",
        "Pedagogy Agent\nrevision_service.py\nPOST /revision/plan",
    ]
    for idx, text in zip((27, 28, 29, 30), cards):
        write_index(slide, n, idx, text, size_pt=13)
    rects = [
        (path, shape)
        for path, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(cards):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=n, shape_index=rects[i][0], size_pt=13)


def fill_architecture(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "System Architecture", "System Architecture", size_pt=22)
    write_index(slide, n, 18, "System Architecture", size_pt=22)
    body = (
        "FastAPI monolith — backend/app/main.py\n"
        "React+Vite SPA — frontend/officehours-app :5180\n"
        "API :8000 · WebSocket /ws · SQLite / Postgres DATABASE_URL\n"
        "Routers: /auth /requests /ta /agent /lti /help-room /revision"
    )
    write_contains(slide, n, "Avis", body, size_pt=14)
    write_contains(slide, n, "OneDrive", body, size_pt=14)
    write_index(slide, n, 21, body, size_pt=14)
    write_nth_empty(slide, n, body, nth=0, size_pt=14)


def fill_tech_stack(slide, n: int) -> None:
    """Tech stack + auth/LTI (no extra slide — never add_slide)."""
    scrub_headers(slide, n)
    write_exact(slide, n, "Tech Stack", "Tech Stack & Auth", size_pt=22)
    write_index(slide, n, 18, "Tech Stack & Auth", size_pt=22)
    body = (
        "Local ML .joblib + all-MiniLM-L6-v2 (or lexical)\n"
        "Gemini gated: ALLOW_EXTERNAL_LLM + demo only\n"
        "Auth: CourseMembership + AuthSession + get_current_user\n"
        "LTI 1.3: /lti/login · /lti/launch · identity_from_claims"
    )
    write_contains(slide, n, "Avis", body, size_pt=14)
    write_contains(slide, n, "OneDrive", body, size_pt=14)
    write_index(slide, n, 21, body, size_pt=14)
    write_nth_empty(slide, n, body, nth=0, size_pt=14)


def fill_workflow_triage(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Database Design & Core Workflows", "Workflow: Ask Triage", size_pt=20)
    write_index(slide, n, 18, "Workflow: Ask Triage", size_pt=20)
    body = (
        "POST /requests/ → run_ask_triage_pipeline\n"
        "Quiet ask: anonymous on classmate GET /requests/\n"
        "triage_* fields store Analyzer/Matcher/Synthesizer\n"
        "assign_cluster_id via sentence-transformers or lexical"
    )
    write_contains(slide, n, "stockbroker", body, size_pt=14)
    write_contains(slide, n, "sub-folders", body, size_pt=14)
    write_index(slide, n, 30, body, size_pt=14)
    for idx, text in zip(
        (25, 26, 27, 28),
        [
            "1 Submit ask\nmessage / F2F / online",
            "2 Analyzer\ncategory · urgency · tags",
            "3 Matcher\ncourse TA heuristic",
            "4 Synthesizer\nhint or seek-help",
        ],
    ):
        write_index(slide, n, idx, text, size_pt=12)


def fill_workflow_ta(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Database Design & Core Workflows", "Workflow: TA Support Desk", size_pt=20)
    write_index(slide, n, 18, "Workflow: TA Support Desk", size_pt=20)
    body = (
        "POST /ta/claim/ — second TA cannot steal claim\n"
        "GET /ta/coach/ + POST /ta/assist/ Help Coach\n"
        "Teaching bank retrieval — not a trained coach model\n"
        "POST /ta/reply/ required before resolve (message mode)"
    )
    write_contains(slide, n, "Extract key", body, size_pt=14)
    write_contains(slide, n, "Excel", body, size_pt=14)
    write_index(slide, n, 31, body, size_pt=14)
    for idx, text in zip(
        (26, 27, 28, 29),
        [
            "1 Claim ask\nwork_status claimed",
            "2 Help Coach\nbank + approved KB",
            "3 Reply student\nPOST /ta/reply/",
            "4 Resolve\nafter reply exists",
        ],
    ):
        write_index(slide, n, idx, text, size_pt=12)


def fill_workflow_professor(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Database Design & Core Workflows", "Workflow: Knowledge Gate", size_pt=20)
    write_index(slide, n, 19, "Workflow: Knowledge Gate", size_pt=20)
    body = (
        "Ingest → knowledge_entries.status=pending_review\n"
        "Professor Material stamp before Study Agent quotes\n"
        "POST /agent/ask refuses similarity < 0.42\n"
        "External LLM off unless demo + allow gates"
    )
    write_contains(slide, n, "FAUX", body, size_pt=14)
    write_contains(slide, n, "VRAI", body, size_pt=14)
    write_contains(slide, n, "reference Excel", body, size_pt=14)
    write_index(slide, n, 36, body, size_pt=14)
    for idx, text in zip(
        (31, 32, 33, 34),
        [
            "1 Ingest\npending_review",
            "2 Stamp\napprove Material",
            "3 Study Agent\nretrieval only",
            "4 Refuse\nweak match 0.42",
        ],
    ):
        write_index(slide, n, idx, text, size_pt=12)


def fill_rooms(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Database Design & Core Workflows", "Rooms & Clustering", size_pt=20)
    write_index(slide, n, 18, "Rooms & Clustering", size_pt=20)
    write_exact(slide, n, "AI-Driven Data Attribute Automation", "Peer Rooms + Similar Asks", size_pt=18)
    write_index(slide, n, 34, "Peer Rooms + Similar Asks", size_pt=18)
    body = (
        "Rooms API /help-room/ — peer forum (not staff)\n"
        "Chapters from Canvas modules (demo syllabus if OFFICEHOURS_DEMO)\n"
        "Express Interest · points leaderboard\n"
        "Clusters group similar asks for shared meetings"
    )
    for path, shape in iter_text_shapes(slide):
        name = getattr(shape, "name", "") or ""
        if name.startswith("TextBox 9") and not shape_text(shape).strip():
            write_shape(shape, body, slide_no=n, shape_index=path, size_pt=14)
            break
    write_nth_empty(slide, n, body, nth=0, size_pt=14)


def fill_demo(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Live System Demonstration", "Live System Demonstration", size_pt=22)
    write_index(slide, n, 12, "Live System Demonstration", size_pt=22)
    write_exact(slide, n, "Before vs After", "Three Seats · One Login", size_pt=18)
    write_index(slide, n, 38, "Three Seats · One Login", size_pt=18)
    seats = [
        "Sara s.elidrissi@aui.ma\nQuiet ask · Ask Triage · Study refuse",
        "Alice a.chen@aui.ma\nClaim · Help Coach · reply",
        "Benali a.benali@aui.ma\nStamp Material · hit-rate",
        "Password aui-demo\n./scripts/run_product.sh :5180",
    ]
    for idx, text in zip((34, 35, 36, 37), seats):
        write_index(slide, n, idx, text, size_pt=12)


def fill_testing(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Testing, Performance & Evaluation", "Testing & Evaluation", size_pt=22)
    write_index(slide, n, 12, "Testing & Evaluation", size_pt=22)
    write_exact(slide, n, "Technical Skills & Soft Skills", "Citeable Eval Numbers", size_pt=16)
    write_exact(slide, n, "Technical Challenges", "Honest Framing", size_pt=16)
    metrics = (
        "Analyzer CV ~85% · n=156 curated holdout\n"
        "Matcher silver ~87% · demo-name consistency\n"
        "Alice gold n=20 · does not retrain .joblib\n"
        "Study Agent weak-match refuse threshold 0.42"
    )
    framing = (
        "Synthetic/curated — not campus quality\n"
        "Live Matcher = course-scoped heuristic\n"
        "CI: pytest backend + officehours-app build\n"
        "Next evidence: ≥40 human_gold / AUI section"
    )
    empties = [
        (path, shape)
        for path, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (getattr(shape, "name", "") or "").startswith(("TextBox", "Rounded"))
    ]
    if empties:
        write_shape(empties[0][1], metrics, slide_no=n, shape_index=empties[0][0], size_pt=13)
    if len(empties) > 1:
        write_shape(empties[1][1], framing, slide_no=n, shape_index=empties[1][0], size_pt=13)


def fill_challenges(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Technical Challenges & Lessons Learned", "Challenges & Lessons", size_pt=20)
    write_index(slide, n, 13, "Challenges & Lessons", size_pt=20)
    write_exact(slide, n, "Technical Chanllenges", "Technical Challenges", size_pt=16)
    write_exact(slide, n, "Technical Challenges", "Technical Challenges", size_pt=16)
    write_exact(slide, n, "Lessons Learned", "Lessons Learned", size_pt=16)
    challenges = (
        "IT creds missing: Entra + LTI key + Canvas token\n"
        "matcher_classifier.joblib ≠ live course roster\n"
        "LLM gate vs demo convenience tension\n"
        "Gold labels still seed/demo scale"
    )
    lessons = (
        "Professor Material stamp is the product\n"
        "Role lives on CourseMembership per course\n"
        "Local ML first; Gemini optional + gated\n"
        "One SPA (officehours-app) — not three URLs"
    )
    empties = [
        (path, shape)
        for path, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (getattr(shape, "name", "") or "").startswith(("TextBox", "Rounded"))
    ]
    if empties:
        write_shape(empties[0][1], challenges, slide_no=n, shape_index=empties[0][0], size_pt=13)
    if len(empties) > 1:
        write_shape(empties[1][1], lessons, slide_no=n, shape_index=empties[1][0], size_pt=13)


def fill_lessons(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Technical Challenges & Lessons Learned", "Challenges & Lessons", size_pt=20)
    write_exact(slide, n, "Lessons Learned", "Lessons Learned", size_pt=16)
    write_exact(slide, n, "Main challenges faced", "Main Challenges Faced", size_pt=16)
    write_index(slide, n, 23, "Lessons Learned", size_pt=16)
    write_index(slide, n, 30, "Main Challenges Faced", size_pt=16)
    lessons = (
        "Gate first — then optional Gemini/Claude\n"
        "TAs are staff, not classmates in-section\n"
        "Defense honesty: docs/defense_crib.md\n"
        "CI builds backend + product app only"
    )
    challenges = (
        "No live AUI Microsoft / Canvas modules yet\n"
        "Live Matcher is heuristic on real rosters\n"
        "Help Coach = 68-row bank, not a joblib\n"
        "Never ship unconstrained campus ChatGPT"
    )
    empties = [
        (path, shape)
        for path, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (getattr(shape, "name", "") or "").startswith(("TextBox", "Rounded"))
    ]
    if empties:
        write_shape(empties[0][1], lessons, slide_no=n, shape_index=empties[0][0], size_pt=13)
    write_contains(slide, n, "internship", challenges, size_pt=13)
    write_contains(slide, n, "low-code", challenges, size_pt=13)
    if len(empties) > 1:
        write_shape(empties[1][1], challenges, slide_no=n, shape_index=empties[1][0], size_pt=13)


def fill_future(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Conclusion, Limitations & Future Work", "Conclusion & Future Work", size_pt=20)
    write_index(slide, n, 11, "Conclusion & Future Work", size_pt=20)
    write_exact(slide, n, "Future Scaling Potential", "Future Work", size_pt=18)
    write_index(slide, n, 28, "Future Work", size_pt=18)
    body = (
        "AUI IT: Entra app + LTI developer key + Canvas token\n"
        "TA gold lab ≥40 human_gold rows / one section\n"
        "Postgres via DATABASE_URL when load grows\n"
        "Keep the professor gate — no free-form LLM"
    )
    empties = [
        (path, shape)
        for path, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
    ]
    if empties:
        write_shape(empties[0][1], body, slide_no=n, shape_index=empties[0][0], size_pt=14)


def fill_conclusion(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Conclusion", "Conclusion", size_pt=22)
    write_index(slide, n, 25, "Conclusion", size_pt=22)
    conclusion = (
        "OfficeHours is classifiers + retrieval + a professor gate — "
        "not a campus ChatGPT.\n"
        "Students ask earlier; TAs teach; professors stamp what Study Agent may quote."
    )
    write_contains(slide, n, "internship", conclusion, size_pt=15)
    write_contains(slide, n, "low-code", conclusion, size_pt=15)
    write_index(slide, n, 26, conclusion, size_pt=15)


def fill_thanks(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "THANK YOU SO MUCH", "THANK YOU", size_pt=28)
    write_index(slide, n, 11, "THANK YOU", size_pt=28)
    write_exact(slide, n, "THANK YOU FOR YOUR ATTENTION !", "THANK YOU FOR YOUR ATTENTION", size_pt=22)
    write_index(slide, n, 25, "THANK YOU FOR YOUR ATTENTION", size_pt=22)
    write_exact(slide, n, "Q/A & Thank you", "Q&A & Thank You", size_pt=14)


def fill_qa(slide, n: int) -> None:
    scrub_headers(slide, n)
    write_exact(slide, n, "Your questions are welcomed!", "Your questions are welcome!", size_pt=24)
    write_index(slide, n, 15, "Your questions are welcome!", size_pt=24)
    write_exact(slide, n, "Q/A & Thank you", "Q&A", size_pt=18)
    write_index(slide, n, 20, "Q&A", size_pt=18)


def renumber(prs: Presentation) -> None:
    for i, slide in enumerate(prs.slides, start=1):
        for path, shape in iter_text_shapes(slide):
            name = (getattr(shape, "name", "") or "").lower()
            if "slide number" in name:
                write_shape(shape, str(i), slide_no=i, shape_index=path, size_pt=12)


def build() -> None:
    global LEDGER
    LEDGER = WriteLedger()

    # REQUIRED: open the exact template — never Presentation() with no args
    prs = Presentation(r"C:\Users\pc\Downloads\Capstone_Defense_Presentation_Sophia_Abssi_min.pptx")

    assert len(prs.slides) > 0, "Template has zero slides — wrong or missing file"
    print(f"Opened template: {TEMPLATE_PATH}")
    print(f"slide_count={len(prs.slides)}")
    print(f"slide_width={prs.slide_width} EMUs")
    print(f"slide_height={prs.slide_height} EMUs")
    assert prs.slide_width > 0 and prs.slide_height > 0, "Invalid slide dimensions"
    if len(prs.slides) < 21:
        raise RuntimeError(f"Expected ≥21 slides in template, found {len(prs.slides)}")

    # Map all 21 template slides in place — NEVER prs.slides.add_slide()
    fillers = [
        fill_title,  # 1
        fill_toc,  # 2
        fill_mission,  # 3
        fill_intro,  # 4
        fill_problem,  # 5
        fill_related,  # 6
        fill_solution,  # 7
        fill_architecture,  # 8
        fill_tech_stack,  # 9 (includes Auth/LTI text — no new slide)
        fill_workflow_triage,  # 10
        fill_workflow_ta,  # 11
        fill_workflow_professor,  # 12
        fill_rooms,  # 13
        fill_demo,  # 14
        fill_testing,  # 15
        fill_challenges,  # 16
        fill_lessons,  # 17
        fill_future,  # 18
        fill_conclusion,  # 19
        fill_thanks,  # 20
        fill_qa,  # 21
    ]

    for idx, fn in enumerate(fillers):
        slide_no = idx + 1
        print(f"\n=== Slide {slide_no}: {fn.__name__} ===")
        fn(prs.slides[idx], slide_no)

    print("\n=== Final header scrub ===")
    for idx, slide in enumerate(prs.slides):
        scrub_headers(slide, idx + 1)

    print("\n=== Renumber ===")
    renumber(prs)

    if LEDGER.count == 0:
        raise RuntimeError("Zero shapes were updated!")

    # REQUIRED: save ONLY to this path
    prs.save(r"C:\Users\pc\Downloads\Capstone_Defense_MY_TEMPLATE_FILLED.pptx")
    print("\n===== SUMMARY =====")
    print(f"Shapes updated: {LEDGER.count}")
    print(f"Saved: {OUTPUT_PATH}")
    print(f"Slides: {len(prs.slides)} (same as template — no add_slide)")


if __name__ == "__main__":
    build()
