#!/usr/bin/env python3
"""
build_defense.py — Populate Sophia Abssi's Capstone Defense PPTX for OfficeHours AI.

Fixes silent blank output:
  - Recurses into Group shapes
  - Creates styled runs when paragraph.runs is empty
  - Logs every write; raises RuntimeError if zero shapes updated

STRICT RULES:
  1. Never create blank-layout content slides — clone existing slides + copy <p:timing>.
  2. Never assign shape.text = "..." (wipes fonts). Edit runs[0] or add_run() with style.
  3. Content grounded in officehours-ai (FastAPI, officehours-app, Ask Triage, Help Coach,
     Study Agent, Pedagogy Agent, CourseMembership RBAC, LTI 1.3, local ML vs gated Gemini).

Run:

    pip install python-pptx
    python scripts/build_defense.py

Overrides:

    set OFFICEHOURS_DEFENSE_INPUT=C:\\path\\to\\template.pptx
    set OFFICEHOURS_DEFENSE_OUTPUT=C:\\path\\to\\out.pptx
"""

from __future__ import annotations

import copy
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.util import Pt

# ---------------------------------------------------------------------------
# Exact paths (Windows defaults; override via env for local testing)
# ---------------------------------------------------------------------------
INPUT_PATH = Path(
    os.environ.get(
        "OFFICEHOURS_DEFENSE_INPUT",
        r"C:\Users\pc\Downloads\Capstone_Defense_Presentation_Sophia_Abssi_min.pptx",
    )
)
OUTPUT_PATH = Path(
    os.environ.get(
        "OFFICEHOURS_DEFENSE_OUTPUT",
        r"C:\Users\pc\Downloads\Capstone_Defense_FINAL.pptx",
    )
)

# Explicit style used ONLY when a paragraph has zero runs (template empty).
NEW_RUN_FONT = "Calibri"
NEW_RUN_SIZE_PT = 16
NEW_RUN_COLOR = RGBColor(0xF8, 0xFA, 0xFC)  # #F8FAFC — readable on dark slides

PRODUCT_SHORT = "OfficeHours AI — Campus Help Desk"
PRODUCT_LONG = (
    "OfficeHours AI: Bridging the academic help-seeking gap — "
    "a multi-persona AI and peer learning ecosystem"
)
DEFENSE_DATE = "FALL 2026 | 09 December 2026"
HEADER = PRODUCT_SHORT

# Real product facts (from README + backend/app + docs/glossary.md)
# Auth: User + CourseMembership + AuthSession + get_current_user (no CallerContext symbol).
# Support desk = TA Live Queue + Help Coach. Knowledge gate = professor Material stamp.
# Learning agents = Ask Triage, Help Coach, Study Agent, Pedagogy Agent.


# ===================================================================
# Write ledger — every mutation is logged; zero writes = hard fail
# ===================================================================

@dataclass
class WriteLedger:
    count: int = 0
    lines: list[str] = field(default_factory=list)

    def record(self, slide_no: int, shape_label: str, text: str) -> None:
        self.count += 1
        preview = (text or "").replace("\n", " ").strip()
        if len(preview) > 40:
            preview = preview[:40] + "..."
        elif not preview:
            preview = "(empty)"
        line = f'[Slide {slide_no} | Shape {shape_label}] -> Wrote: "{preview}"'
        self.lines.append(line)
        print(line)


LEDGER = WriteLedger()


# ===================================================================
# Shape walking (including groups) + formatting-safe text writes
# ===================================================================

def walk_shapes(shapes, prefix: str = "") -> Iterator[tuple[str, object]]:
    """Yield (path_label, shape) for every shape, descending into groups."""
    for i, shape in enumerate(shapes):
        name = getattr(shape, "name", None) or f"shape{i}"
        label = f"{prefix}{i}:{name}"
        yield label, shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk_shapes(shape.shapes, prefix=f"{label}/")


def iter_text_shapes(slide) -> Iterator[tuple[str, object]]:
    """Every shape (incl. nested) that exposes a text frame."""
    for label, shape in walk_shapes(slide.shapes):
        if getattr(shape, "has_text_frame", False):
            yield label, shape


def _style_new_run(run, *, size_pt: float = NEW_RUN_SIZE_PT) -> None:
    """Apply crisp light text for newly created runs (empty-run case)."""
    run.font.name = NEW_RUN_FONT
    run.font.size = Pt(size_pt)
    run.font.color.rgb = NEW_RUN_COLOR
    run.font.bold = False


def set_paragraph_text(paragraph, text: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> None:
    """
    Write into a paragraph without wiping fonts.

    - If runs exist: update runs[0].text, clear extra runs, KEEP existing style.
    - If runs empty: add_run(), apply explicit #F8FAFC Calibri styling, set text.
    """
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
    shape_label: str,
    size_pt: float = NEW_RUN_SIZE_PT,
) -> bool:
    """Replace all paragraphs in a text frame; log the write."""
    if shape is None or not getattr(shape, "has_text_frame", False):
        return False

    tf = shape.text_frame
    lines = (text if text is not None else "").split("\n")
    if not lines:
        lines = [""]

    # Ensure at least one paragraph exists
    if not tf.paragraphs:
        # text_frame always has paragraphs[0] in python-pptx — defensive
        return False

    while len(tf.paragraphs) < len(lines):
        tf.add_paragraph()

    for i, para in enumerate(tf.paragraphs):
        if i < len(lines):
            set_paragraph_text(para, lines[i], size_pt=size_pt)
        else:
            set_paragraph_text(para, "", size_pt=size_pt)

    LEDGER.record(slide_no, shape_label, text)
    return True


def shape_text(shape) -> str:
    if not getattr(shape, "has_text_frame", False):
        return ""
    return shape.text_frame.text or ""


# ---- match helpers (always recurse into groups) ----

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
    for label, shape in iter_text_shapes(slide):
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
        hits.append((label, shape))
    return hits


def write_exact(slide, slide_no: int, old: str, new: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> int:
    n = 0
    for label, shape in find_shapes(slide, exact=old):
        if write_shape(shape, new, slide_no=slide_no, shape_label=label, size_pt=size_pt):
            n += 1
    return n


def write_contains(slide, slide_no: int, fragment: str, new: str, *, size_pt: float = NEW_RUN_SIZE_PT) -> int:
    n = 0
    for label, shape in find_shapes(slide, contains=fragment):
        if write_shape(shape, new, slide_no=slide_no, shape_label=label, size_pt=size_pt):
            n += 1
    return n


def write_first(
    slide,
    slide_no: int,
    text: str,
    *,
    exact: str | None = None,
    contains: str | None = None,
    name_contains: str | None = None,
    empty_only: bool = False,
    name_startswith: tuple[str, ...] | None = None,
    size_pt: float = NEW_RUN_SIZE_PT,
) -> bool:
    hits = find_shapes(
        slide,
        exact=exact,
        contains=contains,
        name_contains=name_contains,
        empty_only=empty_only,
        name_startswith=name_startswith,
    )
    if not hits:
        return False
    label, shape = hits[0]
    return write_shape(shape, text, slide_no=slide_no, shape_label=label, size_pt=size_pt)


def write_nth_empty(
    slide,
    slide_no: int,
    text: str,
    *,
    nth: int = 0,
    name_startswith: tuple[str, ...] = ("TextBox", "Rounded Rectangle", "Rectangle: Rounded"),
    size_pt: float = NEW_RUN_SIZE_PT,
) -> bool:
    """Fill the nth empty text box matching name prefixes (skips slide numbers)."""
    empties = []
    for label, shape in iter_text_shapes(slide):
        name = getattr(shape, "name", "") or ""
        if "slide number" in name.lower():
            continue
        if not any(name.startswith(p) for p in name_startswith):
            continue
        if shape_text(shape).strip():
            continue
        empties.append((label, shape))
    if nth >= len(empties):
        return False
    label, shape = empties[nth]
    return write_shape(shape, text, slide_no=slide_no, shape_label=label, size_pt=size_pt)


def write_all_named(
    slide,
    slide_no: int,
    name_contains: str,
    text: str,
    *,
    size_pt: float = NEW_RUN_SIZE_PT,
) -> int:
    n = 0
    for label, shape in find_shapes(slide, name_contains=name_contains):
        if write_shape(shape, text, slide_no=slide_no, shape_label=label, size_pt=size_pt):
            n += 1
    return n


# ===================================================================
# Slide clone with timing (never blank layout as content source)
# ===================================================================

NS_P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"


def duplicate_slide(prs: Presentation, source_index: int):
    """Clone an existing slide: deep-copy shapes + <p:timing> animations."""
    source = prs.slides[source_index]
    dest = prs.slides.add_slide(source.slide_layout)

    for shp in list(dest.shapes):
        el = shp._element
        el.getparent().remove(el)

    for shape in source.shapes:
        dest.shapes._spTree.insert_element_before(copy.deepcopy(shape._element), "p:extLst")

    src_timing = source._element.find(f"{NS_P}timing")
    if src_timing is not None:
        dst_timing = dest._element.find(f"{NS_P}timing")
        if dst_timing is not None:
            dest._element.remove(dst_timing)
        dest._element.append(copy.deepcopy(src_timing))

    return dest


def move_slide(prs: Presentation, old_index: int, new_index: int) -> None:
    sld_id_lst = prs.slides._sldIdLst  # pylint: disable=protected-access
    entries = list(sld_id_lst)
    entry = entries[old_index]
    sld_id_lst.remove(entry)
    insert_at = max(0, min(new_index, len(list(sld_id_lst))))
    sld_id_lst.insert(insert_at, entry)


# ===================================================================
# Per-slide content (codebase-grounded)
# ===================================================================

INTERNSHIP_TITLE = "AI-Driven Automation of Document Processing Workflows"


def scrub_and_headers(slide, slide_no: int) -> None:
    """Replace known internship chrome on every slide (group-safe)."""
    write_exact(slide, slide_no, INTERNSHIP_TITLE, HEADER, size_pt=14)
    write_contains(slide, slide_no, "Document Processing Workflows", HEADER, size_pt=14)
    write_exact(slide, slide_no, "CDG Capital Gestion", "OfficeHours AI", size_pt=16)
    write_contains(slide, slide_no, "FALL 2025", DEFENSE_DATE, size_pt=12)
    write_exact(slide, slide_no, "Table of content", "Agenda", size_pt=18)
    write_exact(slide, slide_no, "Table of Content", "Agenda", size_pt=18)


def fill_title(slide, slide_no: int) -> None:
    # Long title on cover (prefer exact old title, else TextBox with long text)
    if not write_exact(slide, slide_no, INTERNSHIP_TITLE, PRODUCT_LONG, size_pt=28):
        write_first(
            slide, slide_no, PRODUCT_LONG,
            name_contains="TextBox 6", size_pt=28,
        )
    # Also catch OfficeHours title already partially rewritten
    write_contains(slide, slide_no, "OfficeHours AI: Bridging", PRODUCT_LONG, size_pt=28)
    write_contains(slide, slide_no, "FALL 2025", DEFENSE_DATE, size_pt=14)
    write_contains(slide, slide_no, "FALL 2026", DEFENSE_DATE, size_pt=14)
    if not write_first(slide, slide_no, DEFENSE_DATE, contains="November", size_pt=14):
        write_first(slide, slide_no, DEFENSE_DATE, name_contains="TextBox 24", size_pt=14)


def fill_toc(slide, slide_no: int) -> None:
    write_contains(slide, slide_no, "OfficeHours AI: Bridging", PRODUCT_LONG, size_pt=18)
    write_exact(slide, slide_no, INTERNSHIP_TITLE, PRODUCT_LONG, size_pt=18)
    write_contains(slide, slide_no, "FALL 202", DEFENSE_DATE, size_pt=12)
    write_exact(slide, slide_no, "Table of content", "Agenda", size_pt=20)
    write_first(slide, slide_no, "Agenda", name_contains="TextBox 46", size_pt=20)
    write_exact(slide, slide_no, "Problem Statement & Motivation", "Problem & Motivation", size_pt=16)
    write_exact(slide, slide_no, "Introduction & Context", "Architecture & AI Surfaces", size_pt=16)
    write_exact(slide, slide_no, "CDG Capital Gestion", "OfficeHours AI", size_pt=16)
    # Fill TOC list items if still old labels
    write_first(slide, slide_no, "Problem & Motivation", contains="Problem Statement", size_pt=16)
    write_first(slide, slide_no, "Architecture & AI Surfaces", contains="Introduction", size_pt=16)


def fill_mission(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Mission and Role", "Mission and Roles", size_pt=22)
    write_first(slide, slide_no, "Mission and Roles", contains="Mission", size_pt=22)

    role_lines = [
        "Student: Quiet ask · Rooms · Study Agent\nPedagogy Agent · classmate notes · Inbox",
        "TA: Live Queue · claim · Help Coach\nReply required before resolve",
        "Professor: Material stamp · Insights · Team\nOnly approved KB reaches /agent/ask",
    ]
    # Prefer empty group children / text boxes for role cards
    filled = 0
    for label, shape in iter_text_shapes(slide):
        if filled >= len(role_lines):
            break
        name = getattr(shape, "name", "") or ""
        cur = shape_text(shape).strip()
        # Nested group text or empty mission cards
        if "/" in label or not cur:
            if "slide number" in name.lower() or name.startswith("Graphic"):
                continue
            if cur and cur not in {
                "Mission and Role",
                "Mission and Roles",
                "Table of Content",
                "Agenda",
                "Problem Statement & Motivation",
                "Introduction & Context",
                HEADER,
                INTERNSHIP_TITLE,
            }:
                # Skip breadcrumbs already rewritten
                if any(k in cur for k in ("Problem", "Introduction", "Agenda", "Table", "FALL")):
                    continue
            if not cur or "CDG" in cur or "financial" in cur.lower() or len(cur) < 3:
                if write_shape(shape, role_lines[filled], slide_no=slide_no, shape_label=label, size_pt=14):
                    filled += 1

    while filled < len(role_lines):
        if write_nth_empty(slide, slide_no, role_lines[filled], nth=0, size_pt=14):
            filled += 1
        else:
            break


def fill_intro(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Introduction & Context", "Introduction & Context", size_pt=22)
    write_exact(slide, slide_no, "CDG Capital Gestion", "Al Akhawayn University", size_pt=16)
    write_exact(slide, slide_no, "Manual Processing Challenges", "Campus Help-Seeking Gap", size_pt=18)
    body = (
        "AUI course help desk: one login, role per course via CourseMembership.\n"
        "Canvas-linked materials; FastAPI API :8000 + React SPA :5180.\n"
        "TAs are staff on courses they already took — not classmates."
    )
    # Replace long CDG blurb if present
    write_contains(slide, slide_no, "financial institution", body, size_pt=14)
    write_contains(slide, slide_no, "national investments", body, size_pt=14)
    if not write_contains(slide, slide_no, "CDG Capital Gestion is", body, size_pt=14):
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)


def fill_problem(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Problem Statement & Motivation", "Problem Statement & Motivation", size_pt=22)
    write_first(slide, slide_no, "Related Work", contains="Existing work", size_pt=14)
    write_first(slide, slide_no, "Related Work", contains="Literature", size_pt=14)
    bullets = (
        "TAs drown in repeat questions across channels\n"
        "Students fear asking openly — Quiet ask needed\n"
        "Unconstrained ChatGPT invents the syllabus\n"
        "No professor-gated course answers today"
    )
    # Prefer empty rounded rect / text box
    if not write_nth_empty(slide, slide_no, bullets, nth=0, size_pt=15):
        write_first(
            slide, slide_no, bullets,
            empty_only=True, name_startswith=("Rounded", "TextBox", "Rectangle"),
            size_pt=15,
        )


def fill_related(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Existing Work & Literature Review", "Existing Work & Literature", size_pt=22)
    write_contains(slide, slide_no, "Existing Work", "Existing Work & Literature", size_pt=22)
    write_exact(slide, slide_no, "Quick Walkthrough: Power Automate", "Gaps vs Piazza, Ed, ChatGPT", size_pt=18)
    body = (
        "Piazza/Ed: peer threads — no stamped agent gate\n"
        "Queue tools: staffing only — no Ask Triage ML\n"
        "Campus ChatGPT: unconstrained answers\n"
        "Our bet: classifiers + retrieval + professor stamp"
    )
    write_contains(slide, slide_no, "Power Automate", "Gaps vs Piazza, Ed, ChatGPT", size_pt=18)
    if not write_nth_empty(slide, slide_no, body, nth=0, size_pt=14):
        write_first(slide, slide_no, body, empty_only=True, name_contains="TextBox", size_pt=14)


def fill_solution(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Proposed Solution Overview", "Proposed Solution Overview", size_pt=22)
    write_contains(slide, slide_no, "Four-Flow", "Four AI Surfaces, One Product Gate", size_pt=18)
    write_contains(slide, slide_no, "Methodology", "Four AI Surfaces, One Product Gate", size_pt=18)
    write_first(
        slide, slide_no, "Four AI Surfaces, One Product Gate",
        contains="Methodology", size_pt=18,
    )

    cards = [
        "Ask Triage\nask_triage_service.py\nAnalyzer → Matcher → Synthesizer",
        "Help Coach\nhelp_coach_service.py\nTA mid-session · never publishes",
        "Study Agent\nkb_agent_service.py\nQuotes only stamped KB · refuse 0.42",
        "Pedagogy Agent\nrevision_service.py\nPOST /revision/plan focus path",
    ]
    # Fill rounded rectangles (empty or leftover)
    rects = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(cards):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=slide_no, shape_label=rects[i][0], size_pt=13)
        else:
            write_nth_empty(slide, slide_no, text, nth=0, size_pt=13)

    # Also fill empty group children that look like card labels
    for label, shape in iter_text_shapes(slide):
        if "/" not in label:
            continue
        cur = shape_text(shape).strip()
        if not cur and "TextBox" in (getattr(shape, "name", "") or ""):
            # leave — cards already filled via rounded rects
            pass


def fill_architecture(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "System Architecture", "System Architecture", size_pt=22)
    write_first(slide, slide_no, "System Architecture", contains="System Architecture", size_pt=22)
    body = (
        "FastAPI monolith — backend/app/main.py\n"
        "React+Vite SPA — frontend/officehours-app :5180\n"
        "API :8000 · WebSocket /ws · SQLite default / Postgres DATABASE_URL\n"
        "Routers: /auth /requests /ta /agent /lti /help-room /revision"
    )
    if not write_contains(slide, slide_no, "Avis", body, size_pt=14):
        if not write_contains(slide, slide_no, "OneDrive", body, size_pt=14):
            if not write_contains(slide, slide_no, "FastAPI", body, size_pt=14):
                write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)
                write_first(slide, slide_no, body, name_contains="TextBox 9", size_pt=14)


def fill_tech_stack(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Tech Stack", "Tech Stack", size_pt=22)
    write_first(slide, slide_no, "Tech Stack", exact="Tech Stack", size_pt=22)
    # If still "System Architecture" on a twin slide, leave architecture title alone —
    # tech slide title in template is "Tech Stack".
    body = (
        "Local ML: request_classifier / matcher / synthesizer .joblib\n"
        "Embeddings: all-MiniLM-L6-v2 (or lexical for tests/demo)\n"
        "Gemini/Claude gated: OFFICEHOURS_ALLOW_EXTERNAL_LLM + demo\n"
        "Auth: AuthSession bearer · Microsoft SSO · LTI 1.3 OIDC"
    )
    if not write_contains(slide, slide_no, "Avis", body, size_pt=14):
        if not write_contains(slide, slide_no, "OneDrive", body, size_pt=14):
            if not write_contains(slide, slide_no, "Local ML", body, size_pt=14):
                write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)


def fill_auth_lti(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "System Architecture", "Auth & Course Membership", size_pt=22)
    write_exact(slide, slide_no, "Tech Stack", "Auth & Course Membership", size_pt=22)
    write_first(slide, slide_no, "Auth & Course Membership", contains="Architecture", size_pt=22)
    write_first(slide, slide_no, "Auth & LTI 1.3", contains="Database Design", size_pt=14)
    body = (
        "User + CourseMembership role per course (student/ta/professor)\n"
        "get_current_user ← AuthSession bearer (session_tokens.py)\n"
        "require_course_role / require_course_member (access_control.py)\n"
        "LTI 1.3: /lti/login · /lti/launch · identity_from_claims"
    )
    if not write_contains(slide, slide_no, "Avis", body, size_pt=14):
        if not write_contains(slide, slide_no, "FastAPI", body, size_pt=14):
            if not write_contains(slide, slide_no, "CourseMembership", body, size_pt=14):
                if not write_contains(slide, slide_no, "OneDrive", body, size_pt=14):
                    write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)


def fill_workflow_triage(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Database Design & Core Workflows", "Workflow: Ask Triage", size_pt=20)
    write_first(slide, slide_no, "Workflow: Ask Triage", contains="Database Design", size_pt=20)
    body = (
        "POST /requests/ → run_ask_triage_pipeline\n"
        "Quiet ask: anonymous on classmate GET /requests/\n"
        "triage_* fields store Analyzer/Matcher/Synthesizer\n"
        "assign_cluster_id via sentence-transformers or lexical"
    )
    write_contains(slide, slide_no, "stockbroker", body, size_pt=14)
    write_contains(slide, slide_no, "sub-folders", body, size_pt=14)
    write_contains(slide, slide_no, "PDF", body, size_pt=14)
    if not write_contains(slide, slide_no, "ask_triage", body, size_pt=14):
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)

    steps = [
        "1 Submit ask\nmessage / F2F / online",
        "2 Analyzer\ncategory · urgency · tags",
        "3 Matcher\ncourse TA heuristic",
        "4 Synthesizer\nhint or seek-help",
    ]
    rects = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(steps):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=slide_no, shape_label=rects[i][0], size_pt=12)


def fill_workflow_ta(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Database Design & Core Workflows", "Workflow: TA Support Desk", size_pt=20)
    write_first(slide, slide_no, "Workflow: TA Support Desk", contains="Database Design", size_pt=20)
    body = (
        "POST /ta/claim/ — second TA cannot steal claim\n"
        "GET /ta/coach/ + POST /ta/assist/ Help Coach\n"
        "Teaching bank retrieval — not a trained coach model\n"
        "POST /ta/reply/ required before resolve (message mode)"
    )
    write_contains(slide, slide_no, "Extract key", body, size_pt=14)
    write_contains(slide, slide_no, "Excel", body, size_pt=14)
    write_contains(slide, slide_no, "multi-page", body, size_pt=14)
    if not write_contains(slide, slide_no, "Help Coach", body, size_pt=14):
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)

    steps = [
        "1 Claim ask\nwork_status claimed",
        "2 Help Coach\nbank + approved KB",
        "3 Reply student\nPOST /ta/reply/",
        "4 Resolve\nafter reply exists",
    ]
    rects = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(steps):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=slide_no, shape_label=rects[i][0], size_pt=12)


def fill_workflow_professor(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Database Design & Core Workflows", "Workflow: Knowledge Gate", size_pt=20)
    write_first(slide, slide_no, "Workflow: Knowledge Gate", contains="Database Design", size_pt=20)
    body = (
        "Ingest → knowledge_entries.status=pending_review\n"
        "Professor Material stamp before Study Agent quotes\n"
        "POST /agent/ask refuses similarity < 0.42\n"
        "External LLM off unless demo + allow gates"
    )
    write_contains(slide, slide_no, "FAUX", body, size_pt=14)
    write_contains(slide, slide_no, "VRAI", body, size_pt=14)
    write_contains(slide, slide_no, "comparison", body, size_pt=14)
    write_contains(slide, slide_no, "reference Excel", body, size_pt=14)
    if not write_contains(slide, slide_no, "pending_review", body, size_pt=14):
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)

    steps = [
        "1 Ingest\npending_review",
        "2 Stamp\napprove Material",
        "3 Study Agent\nretrieval only",
        "4 Refuse\nweak match 0.42",
    ]
    rects = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(steps):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=slide_no, shape_label=rects[i][0], size_pt=12)


def fill_rooms(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Database Design & Core Workflows", "Rooms & Clustering", size_pt=20)
    write_exact(slide, slide_no, "AI-Driven Data Attribute Automation", "Peer Rooms + Similar Asks", size_pt=18)
    write_first(slide, slide_no, "Rooms & Clustering", contains="Database Design", size_pt=20)
    write_first(slide, slide_no, "Peer Rooms + Similar Asks", contains="AI-Driven Data", size_pt=18)
    body = (
        "Rooms API /help-room/ — peer forum (not staff)\n"
        "Chapters from Canvas modules (demo syllabus if OFFICEHOURS_DEMO)\n"
        "Express Interest · points leaderboard\n"
        "Clusters group similar asks for shared meetings"
    )
    # Fill empty TextBox 9 shapes inside groups
    filled = False
    for label, shape in iter_text_shapes(slide):
        name = getattr(shape, "name", "") or ""
        if name.startswith("TextBox 9") and not shape_text(shape).strip():
            write_shape(shape, body, slide_no=slide_no, shape_label=label, size_pt=14)
            filled = True
            break
    if not filled:
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)


def fill_demo(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Live System Demonstration", "Live System Demonstration", size_pt=22)
    write_exact(slide, slide_no, "Before vs After", "Three Seats · One Login", size_pt=18)
    write_first(slide, slide_no, "Three Seats · One Login", contains="Before", size_pt=18)
    seats = [
        "Sara s.elidrissi@aui.ma\nQuiet ask · Ask Triage · Study refuse",
        "Alice a.chen@aui.ma\nClaim · Help Coach · reply",
        "Benali a.benali@aui.ma\nStamp Material · hit-rate",
        "Password aui-demo\n./scripts/run_product.sh :5180",
    ]
    rects = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if (getattr(shape, "name", "") or "").startswith("Rounded Rectangle")
    ]
    for i, text in enumerate(seats):
        if i < len(rects):
            write_shape(rects[i][1], text, slide_no=slide_no, shape_label=rects[i][0], size_pt=12)
        else:
            write_nth_empty(slide, slide_no, text, nth=0, size_pt=12)


def fill_testing(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Testing, Performance & Evaluation", "Testing & Evaluation", size_pt=22)
    write_first(slide, slide_no, "Testing & Evaluation", contains="Testing, Performance", size_pt=22)
    write_exact(slide, slide_no, "Technical Skills & Soft Skills", "Citeable Eval Numbers", size_pt=16)
    write_exact(slide, slide_no, "Technical Challenges", "Honest Framing", size_pt=16)
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
    write_first(slide, slide_no, "Citeable Eval Numbers", contains="Technical Skills", size_pt=16)
    # Empty text boxes for metrics bodies
    empties = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (
            (getattr(shape, "name", "") or "").startswith("TextBox")
            or (getattr(shape, "name", "") or "").startswith("Rounded")
        )
    ]
    if len(empties) >= 1:
        write_shape(empties[0][1], metrics, slide_no=slide_no, shape_label=empties[0][0], size_pt=13)
    if len(empties) >= 2:
        write_shape(empties[1][1], framing, slide_no=slide_no, shape_label=empties[1][0], size_pt=13)
    if len(empties) < 1:
        write_nth_empty(slide, slide_no, metrics, nth=0, size_pt=13)


def fill_challenges(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Technical Challenges & Lessons Learned", "Challenges & Lessons", size_pt=20)
    write_contains(slide, slide_no, "Technical Challenges & Lessons", "Challenges & Lessons", size_pt=20)
    write_exact(slide, slide_no, "Technical Chanllenges", "Technical Challenges", size_pt=16)
    write_exact(slide, slide_no, "Technical Challenges", "Technical Challenges", size_pt=16)
    write_exact(slide, slide_no, "Lessons Learned", "Lessons Learned", size_pt=16)
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
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (getattr(shape, "name", "") or "").startswith(("TextBox", "Rounded"))
    ]
    if empties:
        write_shape(empties[0][1], challenges, slide_no=slide_no, shape_label=empties[0][0], size_pt=13)
    if len(empties) > 1:
        write_shape(empties[1][1], lessons, slide_no=slide_no, shape_label=empties[1][0], size_pt=13)
    # Group children that still hold internship leftovers
    write_contains(slide, slide_no, "internship", lessons, size_pt=13)


def fill_lessons(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Technical Challenges & Lessons Learned", "Challenges & Lessons", size_pt=20)
    write_exact(slide, slide_no, "Lessons Learned", "Lessons Learned", size_pt=16)
    write_exact(slide, slide_no, "Main challenges faced", "Main Challenges Faced", size_pt=16)
    write_first(slide, slide_no, "Main Challenges Faced", contains="challenges faced", size_pt=16)
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
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
        and (getattr(shape, "name", "") or "").startswith(("TextBox", "Rounded"))
    ]
    if empties:
        write_shape(empties[0][1], lessons, slide_no=slide_no, shape_label=empties[0][0], size_pt=13)
    write_contains(slide, slide_no, "internship", challenges, size_pt=13)
    write_contains(slide, slide_no, "low-code", challenges, size_pt=13)
    if len(empties) > 1:
        write_shape(empties[1][1], challenges, slide_no=slide_no, shape_label=empties[1][0], size_pt=13)


def fill_future(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Conclusion, Limitations & Future Work", "Conclusion & Future Work", size_pt=20)
    write_exact(slide, slide_no, "Future Scaling Potential", "Future Work", size_pt=18)
    write_first(slide, slide_no, "Future Work", contains="Future Scaling", size_pt=18)
    body = (
        "AUI IT: Entra app + LTI developer key + Canvas token\n"
        "TA gold lab ≥40 human_gold rows / one section\n"
        "Postgres via DATABASE_URL when load grows\n"
        "Keep the professor gate — no free-form LLM"
    )
    empties = [
        (label, shape)
        for label, shape in iter_text_shapes(slide)
        if not shape_text(shape).strip()
        and "slide number" not in (getattr(shape, "name", "") or "").lower()
    ]
    if empties:
        write_shape(empties[0][1], body, slide_no=slide_no, shape_label=empties[0][0], size_pt=14)
    else:
        write_nth_empty(slide, slide_no, body, nth=0, size_pt=14)


def fill_conclusion(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Conclusion", "Conclusion", size_pt=22)
    conclusion = (
        "OfficeHours is classifiers + retrieval + a professor gate — "
        "not a campus ChatGPT.\n"
        "Students ask earlier; TAs teach; professors stamp what Study Agent may quote."
    )
    write_contains(slide, slide_no, "internship", conclusion, size_pt=15)
    write_contains(slide, slide_no, "low-code", conclusion, size_pt=15)
    write_contains(slide, slide_no, "bridging AI", conclusion, size_pt=15)
    # Long conclusion TextBox on template
    for label, shape in iter_text_shapes(slide):
        cur = shape_text(shape)
        if len(cur) > 80 and ("internship" in cur.lower() or "Conclusion" not in cur or "taught" in cur.lower()):
            if "FALL" in cur or cur.strip() in {HEADER, INTERNSHIP_TITLE}:
                continue
            if "taught me" in cur.lower() or "efficient" in cur.lower() or len(cur) > 100:
                write_shape(shape, conclusion, slide_no=slide_no, shape_label=label, size_pt=15)
                break


def fill_thanks(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "THANK YOU SO MUCH", "THANK YOU", size_pt=28)
    write_exact(slide, slide_no, "THANK YOU FOR YOUR ATTENTION !", "THANK YOU FOR YOUR ATTENTION", size_pt=22)
    write_contains(slide, slide_no, "THANK YOU", "THANK YOU FOR YOUR ATTENTION", size_pt=22)
    write_exact(slide, slide_no, "Q/A & Thank you", "Q&A & Thank You", size_pt=14)


def fill_qa(slide, slide_no: int) -> None:
    scrub_and_headers(slide, slide_no)
    write_exact(slide, slide_no, "Your questions are welcomed!", "Your questions are welcome!", size_pt=24)
    write_contains(slide, slide_no, "questions are welcome", "Your questions are welcome!", size_pt=24)
    write_exact(slide, slide_no, "Q/A & Thank you", "Q&A", size_pt=18)
    write_first(slide, slide_no, "Q&A", contains="Q/A", size_pt=18)


def renumber(prs: Presentation) -> None:
    for i, slide in enumerate(prs.slides, start=1):
        for label, shape in iter_text_shapes(slide):
            name = (getattr(shape, "name", "") or "").lower()
            if "slide number" in name:
                write_shape(shape, str(i), slide_no=i, shape_label=label, size_pt=12)


# ===================================================================
# Orchestration
# ===================================================================

def print_clone_map() -> None:
    print(
        """
CLONE / EDIT MAP
================
Edit in place [0..20]; clone [7] Architecture → Auth & LTI (insert after Tech Stack).

  [0]  Title              → OfficeHours long title + FALL 2026
  [1]  TOC                → Agenda
  [2]  Mission            → Student / TA / Professor roles
  [3]  Intro              → AUI CourseMembership context
  [4]  Problem            → Repeat asks / ChatGPT / no gate
  [5]  Related work       → Piazza/Ed/ChatGPT gaps
  [6]  Solution (4 cards) → Ask Triage / Help Coach / Study / Pedagogy
  [7]  Architecture       → FastAPI + SPA + routers
  [8]  Tech stack         → .joblib ML, embeddings, gated Gemini, LTI
  NEW  Auth & LTI         ← CLONE of [7] (shapes + p:timing)
  [9+] Workflows          → Triage / TA desk / Knowledge gate / Rooms
  Demo → Testing → Challenges → Lessons → Future → Conclusion → Thanks → Q&A
"""
    )


def build() -> Path:
    global LEDGER
    LEDGER = WriteLedger()

    if not INPUT_PATH.exists():
        print(f"ERROR: template not found:\n  {INPUT_PATH}", file=sys.stderr)
        print(
            "Place Capstone_Defense_Presentation_Sophia_Abssi_min.pptx at that path,\n"
            "or set OFFICEHOURS_DEFENSE_INPUT.",
            file=sys.stderr,
        )
        sys.exit(1)

    prs = Presentation(str(INPUT_PATH))
    n = len(prs.slides)
    if n < 21:
        raise RuntimeError(f"Expected ≥21 slides in template, found {n}")

    print(f"Loaded template with {n} slides from:\n  {INPUT_PATH}")

    # Extend: clone System Architecture (index 7) for Auth & LTI
    print("Cloning slide index 7 (System Architecture) → Auth & LTI")
    duplicate_slide(prs, 7)
    move_slide(prs, len(prs.slides) - 1, 9)
    print(f"  Total slides now: {len(prs.slides)}")

    fillers = [
        fill_title,
        fill_toc,
        fill_mission,
        fill_intro,
        fill_problem,
        fill_related,
        fill_solution,
        fill_architecture,
        fill_tech_stack,
        fill_auth_lti,
        fill_workflow_triage,
        fill_workflow_ta,
        fill_workflow_professor,
        fill_rooms,
        fill_demo,
        fill_testing,
        fill_challenges,
        fill_lessons,
        fill_future,
        fill_conclusion,
        fill_thanks,
        fill_qa,
    ]

    for idx, fn in enumerate(fillers):
        if idx >= len(prs.slides):
            print(f"WARN: missing slide index {idx}", file=sys.stderr)
            continue
        slide_no = idx + 1
        print(f"\n=== Filling slide {slide_no}: {fn.__name__} ===")
        fn(prs.slides[idx], slide_no)

    # Final pass: rewrite any remaining internship title headers
    print("\n=== Final header scrub ===")
    for idx, slide in enumerate(prs.slides):
        scrub_and_headers(slide, idx + 1)

    print("\n=== Renumber ===")
    renumber(prs)

    if LEDGER.count == 0:
        raise RuntimeError("Zero shapes were updated!")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PATH))

    print(f"\n===== SUMMARY =====")
    print(f"Shapes updated: {LEDGER.count}")
    print(f"Wrote: {OUTPUT_PATH}")
    print(f"Slides: {len(prs.slides)} (21 template + 1 Auth/LTI clone)")
    return OUTPUT_PATH


if __name__ == "__main__":
    if "--map" in sys.argv:
        print_clone_map()
        sys.exit(0)
    print_clone_map()
    build()
