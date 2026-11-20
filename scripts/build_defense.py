#!/usr/bin/env python3
"""
build_defense.py — Populate Sophia Abssi's Capstone Defense PPTX for OfficeHours AI.

STRICT RULES (enforced in this script):
  1. Never create blank slides. Extra slides are deep-clones of an existing template slide
     (shapes + <p:timing> animations copied).
  2. Never assign shape.text = "..." (wipes fonts). Always edit paragraph.runs[0].text
     and clear extra runs in that paragraph.
  3. Content is grounded in the officehours-ai codebase (FastAPI monolith, React+Vite SPA,
     Ask Triage, Help Coach, Study Agent, Pedagogy Agent, CourseMembership RBAC, LTI 1.3,
     local ML vs gated Gemini).

Run on the machine that has the template (Windows paths below):

    pip install python-pptx
    python build_defense.py

Optional overrides:

    set OFFICEHOURS_DEFENSE_INPUT=C:\\path\\to\\template.pptx
    set OFFICEHOURS_DEFENSE_OUTPUT=C:\\path\\to\\out.pptx
"""

from __future__ import annotations

import copy
import os
import sys
from pathlib import Path

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE

# ---------------------------------------------------------------------------
# Exact paths required by the defense build (override via env if needed)
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

PRODUCT_SHORT = "OfficeHours AI — Campus Help Desk"
PRODUCT_LONG = (
    "OfficeHours AI: Bridging the academic help-seeking gap — "
    "a multi-persona AI and peer learning ecosystem"
)
DEFENSE_DATE = "FALL 2026 | 09 December 2026"

# Running header on almost every slide (TextBox 6)
HEADER = PRODUCT_SHORT


# ===================================================================
# Low-level helpers — formatting-safe text + slide clone with timing
# ===================================================================

def _clear_extra_runs(paragraph) -> None:
    """Keep runs[0]; blank any additional runs so styling on run 0 survives."""
    for run in paragraph.runs[1:]:
        run.text = ""


def set_paragraph_text(paragraph, text: str) -> None:
    """Write into paragraph.runs[0] only — never wipe font via paragraph.text."""
    if paragraph.runs:
        paragraph.runs[0].text = text
        _clear_extra_runs(paragraph)
    else:
        run = paragraph.add_run()
        run.text = text


def set_shape_text(shape, text: str) -> bool:
    """
    Replace shape text while preserving the first run's font/size/color.
    Multi-line input uses existing paragraphs when possible; adds paragraphs
    only when the shape already has fewer paragraphs than lines needed.
    """
    if shape is None or not getattr(shape, "has_text_frame", False):
        return False
    tf = shape.text_frame
    lines = text.split("\n") if text is not None else [""]
    if not lines:
        lines = [""]

    # Ensure we have at least one paragraph
    if not tf.paragraphs:
        return False

    # Grow paragraph count if needed (new paras inherit slide defaults;
    # unavoidable when the template box had fewer lines).
    while len(tf.paragraphs) < len(lines):
        tf.add_paragraph()

    for i, para in enumerate(tf.paragraphs):
        if i < len(lines):
            set_paragraph_text(para, lines[i])
        else:
            # Blank leftover paragraphs without deleting XML (keeps spacing).
            set_paragraph_text(para, "")
    return True


def walk_shapes(shapes):
    """Yield every shape, descending into groups."""
    for shape in shapes:
        yield shape
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from walk_shapes(shape.shapes)


def shape_at(slide, index: int):
    """Return shape by template slide_map shape_index, or None."""
    try:
        return slide.shapes[index]
    except (IndexError, KeyError):
        return None


def set_by_index(slide, index: int, text: str) -> bool:
    return set_shape_text(shape_at(slide, index), text)


def find_by_exact_text(slide, exact: str):
    """First text shape whose full text (stripped) equals `exact`."""
    needle = (exact or "").strip()
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        if (shape.text_frame.text or "").strip() == needle:
            return shape
    return None


def replace_exact(slide, old: str, new: str) -> bool:
    shape = find_by_exact_text(slide, old)
    if shape is None:
        return False
    return set_shape_text(shape, new)


def replace_all_exact(slide, mapping: dict[str, str]) -> int:
    hits = 0
    for old, new in mapping.items():
        if replace_exact(slide, old, new):
            hits += 1
    return hits


def replace_contains(slide, fragment: str, new: str) -> int:
    """Replace every text frame whose text contains `fragment` (once each)."""
    hits = 0
    frag = fragment.lower()
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = shape.text_frame.text or ""
        if frag in cur.lower():
            if set_shape_text(shape, new):
                hits += 1
    return hits


def set_header_everywhere(prs, header: str = HEADER) -> None:
    """Update the shared product title TextBox 6 (or matching old titles)."""
    for slide in prs.slides:
        # Prefer index 8 when it looks like the running header (most slides).
        # Skip the title slide's long product name at index 7.
        for idx in (8, 13, 12):
            shp = shape_at(slide, idx)
            if shp is None or not shp.has_text_frame:
                continue
            cur = (shp.text_frame.text or "").strip()
            if (
                "Document Processing" in cur
                or cur == "AI-Driven Automation of Document Processing Workflows"
                or cur == HEADER
                or (cur.startswith("OfficeHours AI —") and cur != PRODUCT_LONG)
            ):
                set_shape_text(shp, header)
                break
        replace_exact(slide, "AI-Driven Automation of Document Processing Workflows", header)


def scrub_internship_leftovers(prs: Presentation) -> None:
    """Replace any remaining CDG / Power Automate / Avis copy with OfficeHours lines."""
    replacements = {
        "CDG Capital Gestion": "OfficeHours AI",
        "Quick Walkthrough: Power Automate": "Gaps vs Piazza, Ed, ChatGPT",
        "Manual Processing Challenges": "Campus Help-Seeking Gap",
        "AI-Driven Data Attribute Automation": "Peer Rooms + Similar Asks",
        "Before vs After": "Three Seats · One Login",
        "Technical Chanllenges": "Technical Challenges",
        "Future Scaling Potential": "Future Work",
        "THANK YOU SO MUCH": "THANK YOU",
        "THANK YOU FOR YOUR ATTENTION !": "THANK YOU FOR YOUR ATTENTION",
        "Your questions are welcomed!": "Your questions are welcome!",
        "Q/A & Thank you": "Q&A",
        "Table of content": "Agenda",
        "Table of Content": "Agenda",
    }
    avis_body = (
        "FastAPI monolith — backend/app/main.py\n"
        "React+Vite SPA — officehours-app :5180\n"
        "Local ML triage · gated Gemini · LTI 1.3\n"
        "Professor stamp before Study Agent quotes"
    )
    for slide in prs.slides:
        replace_all_exact(slide, replacements)
        for shape in walk_shapes(slide.shapes):
            if not shape.has_text_frame:
                continue
            cur = shape.text_frame.text or ""
            low = cur.lower()
            if "avis" in low or "onedrive" in low or "stockbroker" in low or "faux" in low:
                set_shape_text(shape, avis_body)
            elif "internship" in low or "low-code" in low:
                set_shape_text(
                    shape,
                    "OfficeHours is classifiers + retrieval + a professor gate — "
                    "not a campus ChatGPT.\n"
                    "Students ask earlier; TAs teach; professors stamp what the agent may quote.",
                )


def duplicate_slide(prs: Presentation, source_index: int):
    """
    Clone an existing slide (NOT a blank layout).

    - Uses the source slide's layout via add_slide (required by python-pptx to
      allocate a slide part), then strips layout placeholders and deep-copies
      every shape from the source so backgrounds/fonts stay identical.
    - Deep-copies <p:timing> so PowerPoint animations survive.
    """
    source = prs.slides[source_index]
    # Use the SAME layout object the source uses — never a blank layout choice.
    dest = prs.slides.add_slide(source.slide_layout)

    # Remove shapes that arrived from the layout placeholders.
    for shp in list(dest.shapes):
        el = shp._element
        el.getparent().remove(el)

    # Deep-copy all shapes from the source slide tree (skip timing/extLst later).
    for shape in source.shapes:
        dest.shapes._spTree.insert_element_before(copy.deepcopy(shape._element), "p:extLst")

    # Copy animation timing XML if present.
    src_timing = source._element.find(
        "{http://schemas.openxmlformats.org/presentationml/2006/main}timing"
    )
    if src_timing is not None:
        # Drop any empty timing the new slide may have, then append clone.
        dst_timing = dest._element.find(
            "{http://schemas.openxmlformats.org/presentationml/2006/main}timing"
        )
        if dst_timing is not None:
            dest._element.remove(dst_timing)
        dest._element.append(copy.deepcopy(src_timing))

    return dest


def move_slide(prs: Presentation, old_index: int, new_index: int) -> None:
    """Reorder slides by moving the sldIdLst entry."""
    sld_id_lst = prs.slides._sldIdLst  # pylint: disable=protected-access
    entries = list(sld_id_lst)
    entry = entries[old_index]
    sld_id_lst.remove(entry)
    # After remove, indices >= old_index shift left.
    insert_at = new_index if new_index < old_index else new_index
    # Clamp
    insert_at = max(0, min(insert_at, len(list(sld_id_lst))))
    sld_id_lst.insert(insert_at, entry)


def renumber_slides(prs: Presentation) -> None:
    """Best-effort update of visible slide-number placeholders."""
    for i, slide in enumerate(prs.slides, start=1):
        for shape in walk_shapes(slide.shapes):
            name = (getattr(shape, "name", "") or "").lower()
            if "slide number" in name and shape.has_text_frame:
                set_shape_text(shape, str(i))


# ===================================================================
# Clone map (documented for the defense narrative)
#
# Template indices are 0-based. Existing slides 0–20 are rewritten in place.
# Extra technical slides are cloned from the listed source, then filled.
# ===================================================================
#
# | Final role                         | Action              | Why this template slide      |
# |------------------------------------|---------------------|------------------------------|
# | 1  Title                           | edit slide 0        | Hero title + date            |
# | 2  Agenda / TOC                    | edit slide 1        | TOC list layout              |
# | 3  Mission & roles                 | edit slide 2        | Mission card groups          |
# | 4  Introduction & context          | edit slide 3        | Body + image intro           |
# | 5  Problem & motivation            | edit slide 4        | Problem section chrome       |
# | 6  Related work                    | edit slide 5        | Literature / walkthrough     |
# | 7  Solution overview (4 surfaces)  | edit slide 6        | Four rounded-rect pipeline   |
# | 8  System architecture             | edit slide 7        | Architecture body + figure   |
# | 9  Tech stack                      | edit slide 8        | Tech stack twin of arch      |
# |10  Auth & LTI (NEW)                | CLONE slide 7       | Same body layout as arch     |
# |11  Ask Triage workflow             | edit slide 9        | Four-step workflow cards     |
# |12  TA desk + Help Coach            | edit slide 10       | Four-step workflow cards     |
# |13  Professor gate + Study Agent    | edit slide 11       | Four-step / compare layout   |
# |14  Rooms + clustering              | edit slide 12       | Multi-group workflow         |
# |15  Live demonstration              | edit slide 13       | Demo / before-after + video  |
# |16  Testing & evaluation            | edit slide 14       | Metrics / skills layout      |
# |17  Challenges                      | edit slide 15       | Challenges + lessons split   |
# |18  Lessons learned                 | edit slide 16       | Lessons twin                 |
# |19  Future work                     | edit slide 17       | Future / scaling             |
# |20  Conclusion                      | edit slide 18       | Conclusion prose             |
# |21  Thank you                       | edit slide 19       | Thank-you                    |
# |22  Q&A                             | edit slide 20       | Q&A closer                   |
#


def fill_title(slide) -> None:
    set_by_index(slide, 7, PRODUCT_LONG)
    set_by_index(slide, 10, DEFENSE_DATE)


def fill_toc(slide) -> None:
    set_by_index(slide, 8, PRODUCT_LONG)
    set_by_index(slide, 11, DEFENSE_DATE)
    set_by_index(slide, 20, "Agenda")
    set_by_index(slide, 21, "Problem & Motivation")
    set_by_index(slide, 22, "Architecture & AI Surfaces")
    set_by_index(slide, 23, "OfficeHours AI")
    # Rounded rect / empty boxes — leave chrome


def fill_mission(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 12, "Table of Contents")
    set_by_index(slide, 13, "Problem & Motivation")
    set_by_index(slide, 14, "Introduction & Context")
    set_by_index(slide, 18, "Agenda")
    set_by_index(slide, 26, DEFENSE_DATE)
    set_by_index(slide, 27, "Mission and Roles")
    # Mission card groups — replace known internship labels if present
    replace_all_exact(
        slide,
        {
            "Mission and Role": "Mission and Roles",
            "CDG Capital Gestion": "Al Akhawayn University",
        },
    )
    # Try to seed group text boxes with role bullets (short)
    role_snippets = [
        "Student: Quiet ask, Rooms, Study Agent",
        "TA: Live queue, claim, Help Coach",
        "Professor: Stamp KB, Insights, Team",
    ]
    filled = 0
    for shape in walk_shapes(slide.shapes):
        if shape.shape_type != MSO_SHAPE_TYPE.GROUP:
            continue
        for child in walk_shapes(shape.shapes):
            if not child.has_text_frame:
                continue
            cur = (child.text_frame.text or "").strip()
            # Fill empty or leftover internship blurbs inside groups
            if not cur or "CDG" in cur or "financial" in cur.lower() or "mission" in cur.lower():
                if filled < len(role_snippets):
                    set_shape_text(child, role_snippets[filled])
                    filled += 1


def fill_intro(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 12, "OfficeHours AI")
    set_by_index(slide, 13, "Problem Statement")
    set_by_index(slide, 14, "Introduction")
    set_by_index(slide, 18, "Introduction & Context")
    set_by_index(
        slide,
        22,
        "AUI course help desk: one login, role per course, Canvas-linked materials.",
    )
    set_by_index(slide, 24, "Campus Help-Seeking Gap")
    replace_all_exact(
        slide,
        {
            "CDG Capital Gestion": "OfficeHours AI",
            "Manual Processing Challenges": "Campus Help-Seeking Gap",
            "Introduction & Context": "Introduction & Context",
        },
    )


def fill_problem(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 12, "Introduction & Context")
    set_by_index(slide, 13, "Related Work")
    set_by_index(slide, 14, "Problem & Motivation")
    set_by_index(slide, 18, "Problem Statement & Motivation")
    # Body often lives in empty rounded rect — write crisp bullets
    bullets = (
        "TAs drown in repeat questions\n"
        "Students fear asking openly\n"
        "ChatGPT invents the syllabus\n"
        "No professor-gated course answers"
    )
    # Prefer rounded rectangle content box (index 19 on template slide 5)
    if not set_by_index(slide, 19, bullets):
        # Fallback: any empty text-capable rounded rect
        for shape in walk_shapes(slide.shapes):
            if not shape.has_text_frame:
                continue
            name = (shape.name or "").lower()
            if "rounded" in name and not (shape.text_frame.text or "").strip():
                set_shape_text(shape, bullets)
                break


def fill_related(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 12, "Problem & Motivation")
    set_by_index(slide, 13, "Solution Overview")
    set_by_index(slide, 14, "Related Work")
    set_by_index(slide, 18, "Existing Work & Literature")
    set_by_index(slide, 27, "Gaps vs Piazza, Ed, ChatGPT")
    body = (
        "Piazza/Ed: peer threads, no gated agent\n"
        "Queue tools: staffing only, no triage ML\n"
        "Campus ChatGPT: unconstrained answers\n"
        "Our bet: classifiers + retrieval + stamp"
    )
    set_by_index(slide, 19, body)


def fill_solution(slide) -> None:
    """Four-card pipeline slide → four AI product surfaces."""
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 13, "Proposed Solution Overview")
    set_by_index(slide, 16, "Related Work")
    set_by_index(slide, 17, "Architecture & Stack")
    set_by_index(slide, 18, "Solution Overview")
    set_by_index(slide, 26, "Four AI Surfaces, One Product Gate")

    card_titles = [
        "Ask Triage\nAnalyzer → Matcher → Synthesizer",
        "Help Coach\nTA mid-session Socratic assist",
        "Study Agent\nQuotes only stamped KB",
        "Pedagogy Agent\nPOST /revision/plan focus path",
    ]
    # Rounded rectangles 14–17 at indices 27–30 (slide_map slide 7)
    for idx, text in zip((27, 28, 29, 30), card_titles):
        set_by_index(slide, idx, text)

    # Group labels if present
    replace_contains(slide, "Four-Flow", "Four AI Surfaces, One Product Gate")
    replace_contains(slide, "Methodology", "Four AI Surfaces, One Product Gate")


def fill_architecture(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Solution Overview")
    set_by_index(slide, 15, "Database & Workflows")
    set_by_index(slide, 16, "Architecture & Stack")
    set_by_index(slide, 18, "System Architecture")
    body = (
        "FastAPI monolith — backend/app/main.py\n"
        "React+Vite SPA — officehours-app :5180\n"
        "API :8000 · WebSocket /ws · SQLite/Postgres\n"
        "Routers: /requests /ta /agent /lti /help-room"
    )
    # Body text box is typically the second TextBox 9 (index 21)
    set_by_index(slide, 21, body)
    replace_contains(slide, "Avis", body)
    replace_contains(slide, "OneDrive", body)


def fill_tech_stack(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Solution Overview")
    set_by_index(slide, 15, "Database & Workflows")
    set_by_index(slide, 16, "Architecture & Stack")
    set_by_index(slide, 18, "Tech Stack")
    body = (
        "Local ML: scikit-learn .joblib triage models\n"
        "Embeddings: all-MiniLM-L6-v2 or lexical\n"
        "Gemini/Claude gated — demo + allow flags\n"
        "Auth: sessions · Microsoft SSO · LTI 1.3"
    )
    set_by_index(slide, 21, body)
    replace_contains(slide, "Avis", body)
    replace_contains(slide, "OneDrive", body)


def fill_auth_lti(slide) -> None:
    """Filled onto a CLONE of the architecture slide."""
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Architecture & Stack")
    set_by_index(slide, 15, "Database & Workflows")
    set_by_index(slide, 16, "Auth & LTI 1.3")
    set_by_index(slide, 18, "Auth & Course Membership")
    body = (
        "User + CourseMembership role per course\n"
        "get_current_user via AuthSession bearer\n"
        "require_course_role in access_control.py\n"
        "LTI: /lti/login · /lti/launch · identity claims"
    )
    set_by_index(slide, 21, body)
    replace_contains(slide, "Avis", body)
    replace_contains(slide, "OneDrive", body)
    replace_contains(slide, "FastAPI", body)
    replace_contains(slide, "System Architecture", "Auth & Course Membership")
    # If title still says Tech Stack / Architecture after clone
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        if cur in {"System Architecture", "Tech Stack", "System Architecture & Tech Stack"}:
            set_shape_text(shape, "Auth & Course Membership")


def fill_workflow_triage(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Architecture & Stack")
    set_by_index(slide, 15, "Live Demonstration")
    set_by_index(slide, 16, "Core Workflows")
    set_by_index(slide, 18, "Workflow: Ask Triage")
    body = (
        "POST /requests/ runs ask_triage_service\n"
        "Quiet ask hides identity on classmate lists\n"
        "triage_* fields store Analyzer/Matcher output\n"
        "Clusters via assign_cluster_id embeddings"
    )
    set_by_index(slide, 30, body)
    replace_contains(slide, "stockbroker", body)
    replace_contains(slide, "sub-folders", body)
    # Four cards → triage steps
    for idx, text in zip(
        (25, 26, 27, 28),
        [
            "1 Submit ask\nmessage / F2F / online",
            "2 Analyzer\ncategory · urgency · tags",
            "3 Matcher\ncourse TA heuristic",
            "4 Synthesizer\nhint or seek-help",
        ],
    ):
        set_by_index(slide, idx, text)


def fill_workflow_ta(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Architecture & Stack")
    set_by_index(slide, 15, "Live Demonstration")
    set_by_index(slide, 16, "Core Workflows")
    set_by_index(slide, 18, "Workflow: TA Desk")
    body = (
        "POST /ta/claim/ — second TA cannot steal\n"
        "GET /ta/coach/ + POST /ta/assist/ Help Coach\n"
        "Reply required before resolve (message mode)\n"
        "Help Coach never publishes to students"
    )
    set_by_index(slide, 31, body)
    replace_contains(slide, "Extract key", body)
    replace_contains(slide, "Excel", body)
    for idx, text in zip(
        (26, 27, 28, 29),
        [
            "1 Claim ask\nwork_status claimed",
            "2 Help Coach\nteaching bank + KB",
            "3 Reply student\nPOST /ta/reply/",
            "4 Resolve\nafter reply exists",
        ],
    ):
        set_by_index(slide, idx, text)


def fill_workflow_professor(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 15, "Architecture & Stack")
    set_by_index(slide, 16, "Live Demonstration")
    set_by_index(slide, 17, "Core Workflows")
    set_by_index(slide, 19, "Workflow: Professor Gate")
    body = (
        "Ingest lands pending_review — not quotable\n"
        "Professor stamps Material before agent use\n"
        "POST /agent/ask refuses below 0.42 similarity\n"
        "External LLM off unless demo allow-gates"
    )
    set_by_index(slide, 36, body)
    replace_contains(slide, "FAUX", body)
    replace_contains(slide, "VRAI", body)
    replace_contains(slide, "comparison", body)
    for idx, text in zip(
        (31, 32, 33, 34),
        [
            "1 Ingest\npending_review",
            "2 Stamp\napprove Material",
            "3 Study Agent\nretrieval only",
            "4 Refuse\nweak match 0.42",
        ],
    ):
        set_by_index(slide, idx, text)


def fill_rooms(slide) -> None:
    set_by_index(slide, 8, HEADER)
    set_by_index(slide, 14, "Architecture & Stack")
    set_by_index(slide, 15, "Live Demonstration")
    set_by_index(slide, 16, "Core Workflows")
    set_by_index(slide, 18, "Rooms & Clustering")
    set_by_index(slide, 34, "Peer Rooms + Similar Asks")
    # Short bullets into empty text boxes if any
    bullets = (
        "Rooms API /help-room/ — peer forum\n"
        "Chapters from Canvas modules (or demo)\n"
        "Express Interest · points leaderboard\n"
        "Staff stay out of the room"
    )
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        name = (shape.name or "")
        if name.startswith("TextBox 9") and not cur:
            set_shape_text(shape, bullets)
            break
    replace_contains(slide, "AI-Driven Data", "Peer Rooms + Similar Asks")


def fill_demo(slide) -> None:
    set_by_index(slide, 12, "Live System Demonstration")
    set_by_index(slide, 13, HEADER)
    set_by_index(slide, 16, "Core Workflows")
    set_by_index(slide, 17, "Testing & Evaluation")
    set_by_index(slide, 18, "Live Demonstration")
    set_by_index(slide, 38, "Three Seats · One Login")
    # Try to put demo path into group-adjacent text if empty rounded rects exist
    demo_bits = [
        "Sara · Quiet ask · Ask Triage",
        "Alice · claim · Help Coach",
        "Benali · stamp · hit-rate",
        "Password aui-demo · :5180",
    ]
    rect_idxs = (34, 35, 36, 37)
    for idx, text in zip(rect_idxs, demo_bits):
        set_by_index(slide, idx, text)
    replace_contains(slide, "Before vs After", "Three Seats · One Login")


def fill_testing(slide) -> None:
    set_by_index(slide, 12, "Testing, Performance & Evaluation")
    set_by_index(slide, 13, HEADER)
    set_by_index(slide, 16, "Core Workflows")
    set_by_index(slide, 17, "Challenges & Lessons")
    set_by_index(slide, 18, "Testing & Evaluation")
    set_by_index(slide, 31, "Citeable Eval Numbers")
    set_by_index(slide, 33, "Honest Framing")
    # Skills / challenges text boxes
    metrics = (
        "Analyzer CV ~85% · n=156 holdout\n"
        "Matcher silver ~87% · demo names\n"
        "Alice gold n=20 · no retrain\n"
        "Weak-match refuse threshold 0.42"
    )
    framing = (
        "Synthetic/curated — not campus QA\n"
        "Live Matcher = course heuristic\n"
        "Pytest suite on CI backend+app\n"
        "Next: ≥40 human_gold / section"
    )
    set_by_index(slide, 32, metrics)
    # Prefer exact replacements for empty/legacy labels
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        name = shape.name or ""
        if name.startswith("TextBox 9") and cur in {"", "Technical Skills & Soft Skills", "Technical Challenges"}:
            if "Skills" in cur or cur == "":
                if "Skills" in cur:
                    set_shape_text(shape, "Citeable Eval Numbers")
                elif not cur:
                    set_shape_text(shape, metrics if "Analyzer" not in metrics else framing)
            if cur == "Technical Challenges":
                set_shape_text(shape, "Honest Framing")
    # Write metrics/framing into empty text boxes
    empties = [
        s
        for s in walk_shapes(slide.shapes)
        if s.has_text_frame and not (s.text_frame.text or "").strip() and "TextBox" in (s.name or "")
    ]
    if len(empties) >= 1:
        set_shape_text(empties[0], metrics)
    if len(empties) >= 2:
        set_shape_text(empties[1], framing)


def fill_challenges(slide) -> None:
    set_by_index(slide, 13, "Technical Challenges & Lessons")
    set_by_index(slide, 14, HEADER)
    set_by_index(slide, 17, "Testing & Evaluation")
    set_by_index(slide, 18, "Conclusion & Future Work")
    set_by_index(slide, 19, "Challenges & Lessons")
    set_by_index(slide, 23, "Technical Challenges")
    set_by_index(slide, 31, "Lessons Learned")
    challenges = (
        "IT creds: Entra + LTI + Canvas token\n"
        "Matcher joblib ≠ live course roster\n"
        "LLM gate vs demo convenience\n"
        "Gold labels still seed-scale"
    )
    lessons = (
        "Professor stamp is the product\n"
        "Role is per CourseMembership\n"
        "Local ML first, Gemini optional\n"
        "One SPA — not three URL demos"
    )
    replace_contains(slide, "Technical Chanllenges", "Technical Challenges")
    # Fill picture-adjacent text / empty boxes
    texts_written = 0
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        if cur in {"Technical Challenges", "Technical Chanllenges"}:
            # Keep title; put bullets in next empty
            continue
        if not cur and "TextBox" in (shape.name or ""):
            set_shape_text(shape, challenges if texts_written == 0 else lessons)
            texts_written += 1
            if texts_written >= 2:
                break
    # Also try rounded / group children
    if texts_written < 2:
        for shape in walk_shapes(slide.shapes):
            if shape.has_text_frame and "challenge" in (shape.text_frame.text or "").lower():
                if "\n" not in (shape.text_frame.text or ""):
                    pass


def fill_lessons(slide) -> None:
    set_by_index(slide, 12, "Technical Challenges & Lessons")
    set_by_index(slide, 13, HEADER)
    set_by_index(slide, 16, "Testing & Evaluation")
    set_by_index(slide, 17, "Conclusion & Future Work")
    set_by_index(slide, 18, "Challenges & Lessons")
    set_by_index(slide, 23, "Lessons Learned")
    set_by_index(slide, 30, "Main Challenges Faced")
    lessons = (
        "Gate first — then optional LLM\n"
        "TAs are staff, not classmates\n"
        "Demo honesty in defense_crib.md\n"
        "CI builds backend + product app"
    )
    challenges = (
        "No campus Microsoft/Canvas yet\n"
        "Heuristic Matcher on real rosters\n"
        "Teaching bank is CSV, not a model\n"
        "Avoid unconstrained ChatGPT path"
    )
    replace_all_exact(
        slide,
        {
            "Lessons Learned": "Lessons Learned",
            "Main challenges faced": "Main Challenges Faced",
        },
    )
    empties = [
        s
        for s in walk_shapes(slide.shapes)
        if s.has_text_frame
        and not (s.text_frame.text or "").strip()
        and "TextBox" in (s.name or "")
    ]
    if empties:
        set_shape_text(empties[0], lessons)
    # Put challenge bullets near "Main Challenges" title by filling next empty-ish
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        if (shape.text_frame.text or "").strip() == "Main Challenges Faced":
            continue
    # Write challenges into a second content area if we find a short leftover
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        if "internship" in cur.lower() or "low-code" in cur.lower():
            set_shape_text(shape, challenges)


def fill_future(slide) -> None:
    set_by_index(slide, 11, "Conclusion, Limitations & Future Work")
    set_by_index(slide, 12, HEADER)
    set_by_index(slide, 15, "Challenges & Lessons")
    set_by_index(slide, 16, "Q&A / Thank You")
    set_by_index(slide, 17, "Conclusion & Future Work")
    set_by_index(slide, 28, "Future Work")
    body = (
        "AUI IT: Entra + LTI key + Canvas token\n"
        "TA gold lab ≥40 human_gold / section\n"
        "Postgres via DATABASE_URL at scale\n"
        "Keep the professor gate — no free LLM"
    )
    replace_contains(slide, "Future Scaling", "Future Work")
    for shape in walk_shapes(slide.shapes):
        if not shape.has_text_frame:
            continue
        cur = (shape.text_frame.text or "").strip()
        if cur == "Future Work" or cur.startswith("Future"):
            # Find sibling empty text boxes in groups — fill empties
            pass
    empties = [
        s
        for s in walk_shapes(slide.shapes)
        if s.has_text_frame and not (s.text_frame.text or "").strip()
    ]
    if empties:
        set_shape_text(empties[0], body)
    else:
        # Overwrite a group text if it still talks about scaling potential body
        for shape in walk_shapes(slide.shapes):
            if shape.has_text_frame and "scaling" in (shape.text_frame.text or "").lower():
                set_shape_text(shape, body)
                break
    # Ensure title box says Future Work
    set_by_index(slide, 28, "Future Work")


def fill_conclusion(slide) -> None:
    set_by_index(slide, 11, "Conclusion, Limitations & Future Work")
    set_by_index(slide, 12, HEADER)
    set_by_index(slide, 15, "Challenges & Lessons")
    set_by_index(slide, 16, "Q&A / Thank You")
    set_by_index(slide, 17, "Conclusion & Future Work")
    set_by_index(slide, 25, "Conclusion")
    conclusion = (
        "OfficeHours is classifiers + retrieval + a professor gate — "
        "not a campus ChatGPT.\n"
        "Students ask earlier; TAs teach; professors stamp what the agent may quote."
    )
    set_by_index(slide, 26, conclusion)
    replace_contains(slide, "internship", conclusion)
    replace_contains(slide, "low-code", conclusion)


def fill_thanks(slide) -> None:
    set_by_index(slide, 11, "THANK YOU")
    set_by_index(slide, 12, HEADER)
    set_by_index(slide, 15, "Challenges & Lessons")
    set_by_index(slide, 16, "Q&A & Thank You")
    set_by_index(slide, 17, "Conclusion & Future Work")
    set_by_index(slide, 25, "THANK YOU FOR YOUR ATTENTION")


def fill_qa(slide) -> None:
    set_by_index(slide, 10, HEADER)
    set_by_index(slide, 12, "Challenges & Lessons")
    set_by_index(slide, 13, "Conclusion & Future Work")
    set_by_index(slide, 15, "Your questions are welcome!")
    set_by_index(slide, 20, "Q&A")


# ===================================================================
# Orchestration
# ===================================================================

def build() -> Path:
    if not INPUT_PATH.exists():
        print(f"ERROR: template not found:\n  {INPUT_PATH}", file=sys.stderr)
        print(
            "Place Capstone_Defense_Presentation_Sophia_Abssi_min.pptx at that path,\n"
            "or set OFFICEHOURS_DEFENSE_INPUT to its location.",
            file=sys.stderr,
        )
        sys.exit(1)

    prs = Presentation(str(INPUT_PATH))
    n = len(prs.slides)
    if n < 21:
        print(f"ERROR: expected ≥21 slides in template, found {n}", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded template with {n} slides from:\n  {INPUT_PATH}")

    # --- Extend: clone architecture slide (index 7) for Auth & LTI ---
    # Why index 7? Same title+body+figure chrome as System Architecture;
    # ideal for Auth/LTI bullet narrative without inventing a blank layout.
    print("Cloning slide index 7 (System Architecture) → Auth & LTI slide")
    auth_slide = duplicate_slide(prs, 7)
    # New slide is at the end; move it to sit right after Tech Stack (index 8)
    # After clone, indices: 0..20 original, 21 = auth clone.
    # Desired: insert auth as new index 9 (after tech stack at 8).
    move_slide(prs, len(prs.slides) - 1, 9)
    print(f"  Moved Auth slide to index 9; total slides now {len(prs.slides)}")

    # --- Populate in final order (0-based after insert) ---
    # 0 title, 1 toc, 2 mission, 3 intro, 4 problem, 5 related, 6 solution,
    # 7 architecture, 8 tech, 9 AUTH (clone), 10 triage wf, 11 ta wf,
    # 12 professor wf, 13 rooms, 14 demo, 15 testing, 16 challenges,
    # 17 lessons, 18 future, 19 conclusion, 20 thanks, 21 qa

    fillers = [
        (0, fill_title),
        (1, fill_toc),
        (2, fill_mission),
        (3, fill_intro),
        (4, fill_problem),
        (5, fill_related),
        (6, fill_solution),
        (7, fill_architecture),
        (8, fill_tech_stack),
        (9, fill_auth_lti),
        (10, fill_workflow_triage),
        (11, fill_workflow_ta),
        (12, fill_workflow_professor),
        (13, fill_rooms),
        (14, fill_demo),
        (15, fill_testing),
        (16, fill_challenges),
        (17, fill_lessons),
        (18, fill_future),
        (19, fill_conclusion),
        (20, fill_thanks),
        (21, fill_qa),
    ]

    for idx, fn in fillers:
        if idx >= len(prs.slides):
            print(f"WARN: skip missing slide index {idx}", file=sys.stderr)
            continue
        print(f"  Filling slide {idx + 1}: {fn.__name__}")
        fn(prs.slides[idx])

    set_header_everywhere(prs, HEADER)
    scrub_internship_leftovers(prs)
    # Re-apply title-slide long name + date after scrub/header passes.
    set_by_index(prs.slides[0], 7, PRODUCT_LONG)
    set_by_index(prs.slides[0], 10, DEFENSE_DATE)
    renumber_slides(prs)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_PATH))
    print(f"\nWrote:\n  {OUTPUT_PATH}")
    print(f"Slides: {len(prs.slides)} (21 template + 1 Auth/LTI clone)")
    return OUTPUT_PATH


def print_clone_map() -> None:
    print(
        """
CLONE / EDIT MAP (template index → final role)
==============================================
Edit in place:
  [0]  Title                         → OfficeHours title + FALL 2026 date
  [1]  TOC                           → Agenda (problem / architecture)
  [2]  Mission and Role              → Mission & per-course roles
  [3]  Introduction & Context        → AUI help-desk context
  [4]  Problem Statement             → Repeat asks / ChatGPT / no gate
  [5]  Existing Work                 → Piazza/Ed/ChatGPT gaps
  [6]  Proposed Solution (4 cards)   → Ask Triage / Help Coach / Study / Pedagogy
  [7]  System Architecture           → FastAPI monolith + SPA + routers
  [8]  Tech Stack                    → Local ML, embeddings, gated Gemini, LTI
  [9]  DB workflows (triage)         → Ask Triage + Quiet ask  [shifts +1 after clone]
  [10] DB workflows (TA)             → Claim + Help Coach
  [11] DB workflows (professor)      → pending_review stamp + 0.42 refuse
  [12] DB workflows (rooms)          → Rooms /help-room/ + clustering
  [13] Live Demonstration            → Sara / Alice / Benali demo path
  [14] Testing & Evaluation          → CV ~85%, silver ~87%, gold n=20, 0.42
  [15] Challenges                    → IT creds, heuristic Matcher, LLM gate
  [16] Lessons                       → Stamp-first, CourseMembership, one SPA
  [17] Future work                   → IT + gold lab + Postgres; keep gate
  [18] Conclusion                    → Classifiers + retrieval + professor gate
  [19] Thank you                     → Thank you
  [20] Q&A                           → Q&A

Clone (extend):
  NEW Auth & LTI  ← deep-clone of template [7] System Architecture
                  Why: identical body+figure chrome for membership/LTI bullets;
                  animations copied via <p:timing>. Inserted after Tech Stack.
"""
    )


if __name__ == "__main__":
    if "--map" in sys.argv:
        print_clone_map()
        sys.exit(0)
    print_clone_map()
    build()
