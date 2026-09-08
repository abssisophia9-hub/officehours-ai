#!/usr/bin/env python3
"""Supervisor proposal deck — Discovery → Vision → three live demos."""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
OUT_PATHS = [
    ROOT / "docs" / "presentations" / "supervisor_vision_proposal.pptx",
    Path("/opt/cursor/artifacts/supervisor_vision_proposal.pptx"),
]

# Also keep the expected filename from earlier conversations.
OUT_PATHS.append(ROOT / "docs" / "presentations" / "supervisor_technical_briefing.pptx")

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

INK = RGBColor(0x0F, 0x1F, 0x17)
MUTED = RGBColor(0x3D, 0x52, 0x48)
ACCENT = RGBColor(0x0A, 0x4F, 0x34)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAPER = RGBColor(0xF4, 0xF7, 0xF4)
PANEL = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xC5, 0xD4, 0xCB)
WARN = RGBColor(0x8A, 0x4B, 0x12)
WARN_BG = RGBColor(0xF3, 0xE6, 0xD4)
BLUE = RGBColor(0x1E, 0x3A, 0x5F)
BLUE_BG = RGBColor(0xE4, 0xEE, 0xF8)
SOFT = RGBColor(0xD8, 0xEF, 0xE4)
TITLE_BG = RGBColor(0x0A, 0x4F, 0x34)

VISION = (
    "OfficeHours is the Canvas-linked course help desk: students get Quiet ask "
    "and peer Rooms, TAs get a triaged desk with Help Coach, and professors stamp "
    "the only answers the Study Agent may give — so help is fast without inventing the syllabus."
)


def set_run(run, text, *, size=18, bold=False, color=INK, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def _run(p):
    return p.runs[0] if p.runs else p.add_run()


def write_p(tf, text, *, size=18, bold=False, color=INK, font="Calibri", space_after=6, align=PP_ALIGN.LEFT, clear=False):
    p = tf.paragraphs[0] if clear else tf.add_paragraph()
    if clear:
        p.clear()
    p.alignment = align
    p.space_after = Pt(space_after)
    set_run(_run(p), text, size=size, bold=bold, color=color, font=font)


def fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def add_bg(slide, color=PAPER):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), SLIDE_W, SLIDE_H)
    fill(bg, color)
    spTree = slide.shapes._spTree
    sp = bg._element
    spTree.remove(sp)
    spTree.insert(2, sp)


def add_bar(slide, color=ACCENT):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.12), SLIDE_H)
    fill(bar, color)


def blank(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s, PAPER)
    add_bar(s)
    return s


def eyebrow(s, text, top=0.32):
    box = s.shapes.add_textbox(Inches(0.55), Inches(top), Inches(12), Inches(0.32))
    write_p(box.text_frame, text.upper(), size=12, bold=True, color=ACCENT, clear=True, space_after=0)


def title(s, text, top=0.58, size=30):
    box = s.shapes.add_textbox(Inches(0.55), Inches(top), Inches(12.2), Inches(0.9))
    tf = box.text_frame
    tf.word_wrap = True
    write_p(tf, text, size=size, bold=True, color=INK, font="Georgia", clear=True, space_after=0)


def footer(s, text):
    box = s.shapes.add_textbox(Inches(0.55), Inches(7.05), Inches(12.2), Inches(0.3))
    write_p(box.text_frame, text, size=11, color=MUTED, clear=True, space_after=0)


def card(s, left, top, width, height, lines, *, bg=PANEL, accent=ACCENT):
    shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    fill(shape, bg)
    shape.line.color.rgb = LINE
    shape.line.width = Pt(1)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, Inches(0.08), height)
    fill(bar, accent)
    box = s.shapes.add_textbox(left + Inches(0.22), top + Inches(0.14), width - Inches(0.4), height - Inches(0.25))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for kind, text in lines:
        if kind == "h":
            write_p(tf, text, size=16, bold=True, color=ACCENT, clear=first, space_after=8)
        elif kind == "muted":
            write_p(tf, text, size=12, color=MUTED, clear=first, space_after=4)
        else:
            write_p(tf, text, size=14, color=INK, clear=first, space_after=6)
        first = False


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    # 1 Title
    s = prs.slides.add_slide(prs.slide_layouts[6])
    add_bg(s, TITLE_BG)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.12), SLIDE_H)
    fill(bar, RGBColor(0x7D, 0xD3, 0xA8))
    box = s.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(11.5), Inches(0.4))
    write_p(box.text_frame, "CAPSTONE SUPERVISOR PROPOSAL  ·  AL AKHAWAYN UNIVERSITY", size=13, bold=True, color=RGBColor(0x9F, 0xDF, 0xBF), clear=True)
    box = s.shapes.add_textbox(Inches(0.7), Inches(2.2), Inches(11.5), Inches(1.2))
    write_p(box.text_frame, "OfficeHours", size=48, bold=True, color=WHITE, font="Georgia", clear=True)
    box = s.shapes.add_textbox(Inches(0.7), Inches(3.5), Inches(11), Inches(1.6))
    tf = box.text_frame
    tf.word_wrap = True
    write_p(
        tf,
        "Discovery → Vision → Live demo\n"
        "What I found as a TA. What I am building. What you will see for student, TA, and professor.",
        size=18,
        color=RGBColor(0xC9, 0xE8, 0xD8),
        clear=True,
    )
    box = s.shapes.add_textbox(Inches(0.7), Inches(6.4), Inches(11.5), Inches(0.4))
    write_p(box.text_frame, "A Vision Makes It SHARED  ·  Discovery confirms the problem is real", size=13, color=RGBColor(0xA7, 0xC4, 0xB5), clear=True)

    # 2 Agenda
    s = blank(prs)
    eyebrow(s, "How this meeting works")
    title(s, "Three beats — then we demo")
    card(s, Inches(0.55), Inches(1.8), Inches(3.9), Inches(4.3), [
        ("h", "1 · Discovery"),
        ("body", "I was a TA."),
        ("body", "I felt the gap."),
        ("body", "That gap is my Bet."),
    ])
    card(s, Inches(4.7), Inches(1.8), Inches(3.9), Inches(4.3), [
        ("h", "2 · Vision"),
        ("body", "One or two sentences."),
        ("body", "What · who · why this."),
        ("body", "Memorable. Specific enough to say no with."),
    ], bg=BLUE_BG, accent=BLUE)
    card(s, Inches(8.85), Inches(1.8), Inches(3.9), Inches(4.3), [
        ("h", "3 · Live demo"),
        ("body", "Student seat"),
        ("body", "TA seat"),
        ("body", "Professor seat"),
    ], bg=WARN_BG, accent=WARN)
    footer(s, "Goal: leave with a shared picture of the product — then critique scope")

    # 3 Discovery
    s = blank(prs)
    eyebrow(s, "Discovery · the Bet")
    title(s, "I was a TA — that is how I found this")
    card(s, Inches(0.55), Inches(1.65), Inches(12.2), Inches(2.0), [
        ("h", "What I saw from the desk"),
        ("body", "The same questions arrived by email, LMS, and walk-in. Students hesitated to ask. Staff re-answered instead of teaching. Peer chats were noisy. Course materials lived in Canvas — but nothing safe used them."),
    ])
    card(s, Inches(0.55), Inches(3.9), Inches(6.0), Inches(2.6), [
        ("h", "The gap"),
        ("body", "Help was either too human (overloaded) or too open (ChatGPT invents the syllabus)."),
        ("body", "There was no course desk that respected roles, peers, and a professor gate."),
    ], bg=WARN_BG, accent=WARN)
    card(s, Inches(6.8), Inches(3.9), Inches(5.9), Inches(2.6), [
        ("h", "The Bet"),
        ("body", "If we put Quiet ask, peer Rooms, and a stamped Study Agent in one Canvas-linked product, students will ask earlier — and staff will spend time teaching, not sorting."),
    ], bg=SOFT, accent=ACCENT)
    footer(s, "Discovery confirms the problem is real. Vision makes the build SHARED.")

    # 4 Vision — the big slide
    s = blank(prs)
    eyebrow(s, "Vision")
    title(s, "What I am building", size=28)
    box = s.shapes.add_textbox(Inches(0.7), Inches(1.8), Inches(12), Inches(2.8))
    tf = box.text_frame
    tf.word_wrap = True
    write_p(tf, VISION, size=22, bold=True, color=INK, font="Georgia", clear=True, space_after=12)
    card(s, Inches(0.55), Inches(4.9), Inches(4.0), Inches(1.6), [
        ("h", "What"),
        ("body", "One multi-role course help desk"),
    ])
    card(s, Inches(4.75), Inches(4.9), Inches(4.0), Inches(1.6), [
        ("h", "Who"),
        ("body", "Students · TAs · professors in a Canvas course"),
    ], bg=BLUE_BG, accent=BLUE)
    card(s, Inches(8.95), Inches(4.9), Inches(3.8), Inches(1.6), [
        ("h", "Why this"),
        ("body", "Help without inventing the syllabus"),
    ], bg=WARN_BG, accent=WARN)
    footer(s, "Repeatable without notes. Specific enough to say no with.")

    # 5 Say no
    s = blank(prs)
    eyebrow(s, "Vision · boundaries")
    title(s, "What this vision says no to")
    card(s, Inches(0.55), Inches(1.7), Inches(6.0), Inches(4.6), [
        ("h", "We are not building"),
        ("body", "• A free-form campus ChatGPT"),
        ("body", "• Auto-published FAQ with no professor stamp"),
        ("body", "• Three separate URL demos as the product"),
        ("body", "• AUI portal / SIS scraping as the enrollment path"),
        ("body", "• TAs treated as classmates in the section they staff"),
    ], bg=WARN_BG, accent=WARN)
    card(s, Inches(6.8), Inches(1.7), Inches(5.9), Inches(4.6), [
        ("h", "We are building"),
        ("body", "• One login app · role per course"),
        ("body", "• Quiet ask (anonymous to staff) + named Rooms"),
        ("body", "• Ask Triage at intake · Help Coach mid-session"),
        ("body", "• Study Agent only after professor stamp"),
        ("body", "• Canvas as course + module source of truth"),
    ], bg=SOFT, accent=ACCENT)
    footer(s, "If it invents the course, it is out of scope.")

    # 6 Demo map
    s = blank(prs)
    eyebrow(s, "Live demo · setup")
    title(s, "One app · three seats · password aui-demo")
    card(s, Inches(0.45), Inches(1.7), Inches(4.0), Inches(4.5), [
        ("h", "Student"),
        ("muted", "s.elidrissi@aui.ma"),
        ("body", "Quiet ask / Identify me"),
        ("body", "Ask Triage breakdown"),
        ("body", "Study Agent refuse vs answer"),
        ("body", "Rooms (named peer help)"),
    ])
    card(s, Inches(4.65), Inches(1.7), Inches(4.0), Inches(4.5), [
        ("h", "TA"),
        ("muted", "a.chen@aui.ma · CSC 2302 staff"),
        ("body", "My desk queue"),
        ("body", "Claim → Help Coach"),
        ("body", "Reply or group meeting"),
        ("body", "Staff — not a classmate here"),
    ], bg=BLUE_BG, accent=BLUE)
    card(s, Inches(8.85), Inches(1.7), Inches(4.0), Inches(4.5), [
        ("h", "Professor"),
        ("muted", "a.benali@aui.ma"),
        ("body", "Clusters / review insights"),
        ("body", "Stamp pending KB"),
        ("body", "Canvas sync"),
        ("body", "Hit-rate after stamp"),
    ], bg=WARN_BG, accent=WARN)
    footer(s, "./scripts/run_product.sh  →  http://127.0.0.1:5180")

    # 7 Student demo
    s = blank(prs)
    eyebrow(s, "Demo 1 · Student")
    title(s, "What we literally run")
    card(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(5.0), [
        ("h", "Script — Sara · s.elidrissi@aui.ma / aui-demo"),
        ("body", "1. Sign in → pick CSC 2302 (student)"),
        ("body", "2. Quiet ask or Identify me → choose message / face-to-face / online → submit"),
        ("body", "3. Show Ask Triage: Analyzer → Matcher → student hint / request code"),
        ("body", "4. Ask the Study Agent something the KB does not have → it must refuse"),
        ("body", "5. Open Rooms → create or join a chapter thread (named) → interest / accept"),
        ("body", "6. Status lookup by request code — receipt, not a public identity dump"),
        ("muted", "Say: students can ask staff quietly or peers by name — the agent never invents."),
    ])
    footer(s, "Student seat proves: ask paths + agent gate + peer Rooms")

    # 8 TA demo
    s = blank(prs)
    eyebrow(s, "Demo 2 · TA")
    title(s, "What we literally run")
    card(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(5.0), [
        ("h", "Script — Alice · a.chen@aui.ma / aui-demo · CSC 2302"),
        ("body", "1. Sign in → course CSC 2302 (TA — a course she already took)"),
        ("body", "2. Open desk filter: My desk (assigned, backup, open)"),
        ("body", "3. Claim one ask (second TA cannot steal the claim)"),
        ("body", "4. Open Help Coach on that ask: draft reply / Socratic steps"),
        ("body", "5. Reply in message mode — or propose a shared group meeting for a cluster"),
        ("body", "6. Point out: Help Coach assists the TA; it does not publish to the Study Agent"),
        ("muted", "Say: this is the desk I wished I had — sorted work, coaching, not inbox chaos."),
    ], bg=BLUE_BG, accent=BLUE)
    footer(s, "TA seat proves: triage queue + Help Coach + staff role clarity")

    # 9 Professor demo
    s = blank(prs)
    eyebrow(s, "Demo 3 · Professor")
    title(s, "What we literally run")
    card(s, Inches(0.55), Inches(1.55), Inches(12.2), Inches(5.0), [
        ("h", "Script — Prof. Benali · a.benali@aui.ma / aui-demo"),
        ("body", "1. Sign in → professor workspace for CSC 2302 / 3323 / 3374"),
        ("body", "2. Show clusters of repeated confusion + review insights"),
        ("body", "3. Open pending KB drafts from intake / materials"),
        ("body", "4. Approve / edit / reject — stamp is the gate"),
        ("body", "5. Optional: Sync Canvas materials into the course KB"),
        ("body", "6. Switch back to student → Study Agent now answers from the stamp (or still refuses if empty)"),
        ("muted", "Say: professors control what the course AI may quote. Empty KB refusing is a feature."),
    ], bg=WARN_BG, accent=WARN)
    footer(s, "Professor seat proves: visibility + stamp gate + Canvas materials")

    # 10 Shared picture
    s = blank(prs)
    eyebrow(s, "After the demo")
    title(s, "What becomes SHARED")
    box = s.shapes.add_textbox(Inches(0.7), Inches(1.7), Inches(12), Inches(1.4))
    tf = box.text_frame
    tf.word_wrap = True
    write_p(
        tf,
        "We now share one picture: a Canvas-linked course help desk with three seats, "
        "peer Rooms, staff Quiet ask, and a Study Agent that only speaks after a stamp.",
        size=18,
        bold=True,
        color=INK,
        font="Georgia",
        clear=True,
    )
    card(s, Inches(0.55), Inches(3.5), Inches(12.2), Inches(2.8), [
        ("h", "What I want from you next"),
        ("body", "1. Does this vision match a defensible FYP scope?"),
        ("body", "2. What would you cut — or insist we keep — before defense?"),
        ("body", "3. Evidence bar: TA gold labels + KB hit-rate, or something else you trust more?"),
    ])
    footer(s, "Thank you — happy to rerun any seat, or dig into the Bet.")

    for path in OUT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        prs.save(path)
        print(f"Wrote {path}")


if __name__ == "__main__":
    build()
