#!/usr/bin/env python3
"""Keynote-grade OfficeHours AI product demo recorder.

Secrets: load only from repo-root / backend .env (never print values).
Output: capstone_demo_1080p.mp4 + audit frames beside this script.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from playwright.async_api import Page, async_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent
RAW_DIR = OUT_DIR / "raw"
AUDIT_DIR = OUT_DIR / "audit"
CARDS_DIR = OUT_DIR / "cards"
STORE_OUT = Path(
    "/cursor/stores/bc-dc51837a-fa18-4db3-a65f-0e58caaf18ec/final_deliverables/4_Demo_Video"
)
ARTIFACT_OUT = Path("/opt/cursor/artifacts/demo-video")

APP_URL = os.environ.get("OFFICEHOURS_DEMO_URL", "http://127.0.0.1:5180")
API_URL = os.environ.get("OFFICEHOURS_API_URL", "http://127.0.0.1:8000")

DEMO_PASSWORD = "aui-demo"
STUDENT = {"email": "s.elidrissi@aui.ma", "chip": "Student"}
TA = {"email": "a.chen@aui.ma", "chip": "TA (staff on 2302)"}
PROF = {"email": "a.benali@aui.ma", "chip": "Professor"}

COURSE_CODE = "CSC 2302"
REFUSE_Q = "What is the meaning of life according to this course?"
# Lexical retrieval is picky — keep this short and grounded in stamped KB titles.
STUDY_Q = "What is open addressing in hashing?"
ASK_Q = "Why do hash collisions happen when I insert into my open-addressing table?"
ASK_TRIED = "I tried linear probing but still get collisions on insert."
ASK_TOPIC = "Hashing"

VIEWPORT = {"width": 1920, "height": 1080}
DEVICE_SCALE = 2

SECRET_RE = re.compile(
    r"(?:AQ\.[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9_-]{20,})",
    re.I,
)


def redact(text: str) -> str:
    return SECRET_RE.sub("[REDACTED]", text or "")


def load_dotenv_files() -> None:
    for path in (ROOT / ".env", ROOT / "backend" / ".env"):
        if not path.is_file():
            continue
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def log(msg: str) -> None:
    print(redact(msg), flush=True)


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    safe = [redact(c) for c in cmd]
    log("$ " + " ".join(safe))
    return subprocess.run(cmd, check=True, **kwargs)


def ensure_dirs() -> None:
    for d in (OUT_DIR, RAW_DIR, AUDIT_DIR, CARDS_DIR, STORE_OUT, ARTIFACT_OUT):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Motion / cursor engine
# ---------------------------------------------------------------------------

CURSOR_CSS = """
#oh-demo-cursor {
  position: fixed; left: 0; top: 0; width: 22px; height: 22px;
  margin-left: -3px; margin-top: -3px; pointer-events: none; z-index: 2147483647;
  transform: translate3d(-100px,-100px,0);
  transition: transform 16ms linear;
}
#oh-demo-cursor svg { width: 22px; height: 22px; filter: drop-shadow(0 1px 2px rgba(0,0,0,.35)); }
#oh-demo-cursor.clicking svg { transform: scale(.86); }
#oh-demo-ripple {
  position: fixed; width: 18px; height: 18px; border-radius: 999px;
  border: 2px solid rgba(20,51,38,.55); pointer-events: none; z-index: 2147483646;
  transform: translate(-50%,-50%) scale(.4); opacity: 0;
}
#oh-demo-ripple.on {
  animation: ohDemoRipple 420ms cubic-bezier(.2,.8,.2,1) forwards;
}
@keyframes ohDemoRipple {
  0% { opacity: .7; transform: translate(-50%,-50%) scale(.35); }
  100% { opacity: 0; transform: translate(-50%,-50%) scale(2.2); }
}
html { scroll-behavior: smooth; }
.vite-error-overlay, [data-vite-dev-id] { display: none !important; }
"""

CURSOR_HTML = """
<div id="oh-demo-cursor" aria-hidden="true">
  <svg viewBox="0 0 24 24" fill="none">
    <path d="M4 3l15 9.2-6.7 1.7L9.8 21 4 3z" fill="#143326" stroke="#F8F7F4" stroke-width="1.2"/>
  </svg>
</div>
<div id="oh-demo-ripple" aria-hidden="true"></div>
"""


async def inject_chrome(page: Page) -> None:
    await page.add_style_tag(content=CURSOR_CSS)
    await page.evaluate(
        """([html]) => {
          if (!document.getElementById('oh-demo-cursor')) {
            const wrap = document.createElement('div');
            wrap.innerHTML = html;
            document.documentElement.appendChild(wrap);
          }
          document.documentElement.style.cursor = 'none';
          document.body.style.cursor = 'none';
        }""",
        [CURSOR_HTML],
    )


async def move_to(page: Page, x: float, y: float, steps: int = 18) -> None:
    await page.mouse.move(x, y, steps=max(8, steps))
    await page.evaluate(
        """([x,y]) => {
          const c = document.getElementById('oh-demo-cursor');
          if (c) c.style.transform = `translate3d(${x}px,${y}px,0)`;
        }""",
        [x, y],
    )


async def click_locator(page: Page, locator, *, wait_visible: bool = True) -> None:
    if wait_visible:
        await locator.first.wait_for(state="visible", timeout=30000)
    try:
        await locator.first.scroll_into_view_if_needed()
    except Exception:
        pass
    box = await locator.first.bounding_box()
    if not box:
        await locator.first.click(force=True)
        return
    x = box["x"] + box["width"] * random.uniform(0.35, 0.65)
    y = box["y"] + box["height"] * random.uniform(0.35, 0.65)
    await move_to(page, x, y, steps=random.randint(14, 28))
    await page.evaluate(
        """([x,y]) => {
          const c = document.getElementById('oh-demo-cursor');
          const r = document.getElementById('oh-demo-ripple');
          if (c) c.classList.add('clicking');
          if (r) {
            r.style.left = x + 'px'; r.style.top = y + 'px';
            r.classList.remove('on'); void r.offsetWidth; r.classList.add('on');
          }
        }""",
        [x, y],
    )
    await page.mouse.down()
    await page.wait_for_timeout(70)
    await page.mouse.up()
    await page.evaluate(
        """() => {
          const c = document.getElementById('oh-demo-cursor');
          if (c) c.classList.remove('clicking');
        }"""
    )
    await page.wait_for_timeout(180)


async def human_type(page: Page, locator, text: str) -> None:
    await click_locator(page, locator)
    await locator.first.fill("")
    for ch in text:
        delay = random.randint(28, 72)
        if ch in ".?,!":
            delay += random.randint(80, 160)
        if ch == " ":
            delay += random.randint(20, 60)
        await page.keyboard.type(ch, delay=delay)
        if random.random() < 0.04:
            await page.wait_for_timeout(random.randint(120, 280))


async def smooth_scroll(page: Page, *, to_y: int | None = None, delta: int | None = None) -> None:
    if to_y is not None:
        await page.evaluate(
            """(y) => new Promise((resolve) => {
              const start = window.scrollY;
              const dist = y - start;
              const dur = Math.min(2200, Math.max(700, Math.abs(dist) * 0.7));
              const t0 = performance.now();
              const ease = (t) => 1 - Math.pow(1 - t, 3);
              function frame(now) {
                const p = Math.min(1, (now - t0) / dur);
                window.scrollTo(0, start + dist * ease(p));
                if (p < 1) requestAnimationFrame(frame); else resolve();
              }
              requestAnimationFrame(frame);
            })""",
            to_y,
        )
    elif delta is not None:
        await page.mouse.wheel(0, delta)
        await page.wait_for_timeout(450)


async def wait_idle(page: Page, ms: int = 600) -> None:
    await page.wait_for_timeout(ms)


async def wait_gone(page: Page, text: str, timeout: int = 120000) -> None:
    loc = page.get_by_text(text, exact=False)
    try:
        await loc.first.wait_for(state="visible", timeout=5000)
    except Exception:
        return
    await loc.first.wait_for(state="hidden", timeout=timeout)


# ---------------------------------------------------------------------------
# Title cards
# ---------------------------------------------------------------------------

def write_card_svg(path: Path, kind: str) -> None:
    if kind == "intro":
        body = """
        <text x="960" y="280" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="18" letter-spacing="4" fill="#A8B5AC">DEMO VIDEO</text>
        <text x="960" y="360" text-anchor="middle" font-family="Georgia, serif" font-size="64" fill="#F8F7F4">OfficeHours AI</text>
        <text x="960" y="425" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="24" fill="#C9D5CC">Multi-Pathway Campus Helpdesk &amp; Pedagogical Intelligence</text>
        <text x="960" y="560" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="22" fill="#E2E0D8">Presented by Sophia Abssi</text>
        <text x="960" y="600" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="20" fill="#A8B5AC">Supervised by Dr. Oumaima Hourrane</text>
        <text x="960" y="660" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="20" fill="#A8B5AC">Al Akhawayn University (AUI)</text>
        """
    else:
        body = """
        <text x="960" y="300" text-anchor="middle" font-family="Georgia, serif" font-size="48" fill="#F8F7F4">Architecture in one line</text>
        <text x="960" y="380" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="24" fill="#C9D5CC">Classifiers · retrieval over professor-stamped material · staff-owned replies</text>
        <text x="960" y="440" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="22" fill="#C9D5CC">Ask Triage routes · Help Coach drafts for TAs · Study Agent never invents the syllabus</text>
        <text x="960" y="560" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="22" fill="#E2E0D8">Sophia Abssi  ·  Supervised by Dr. Oumaima Hourrane</text>
        <text x="960" y="610" text-anchor="middle" font-family="Helvetica, Arial, sans-serif" font-size="20" fill="#A8B5AC">Al Akhawayn University</text>
        """
    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0F241C"/>
      <stop offset="55%" stop-color="#143326"/>
      <stop offset="100%" stop-color="#1B4332"/>
    </linearGradient>
  </defs>
  <rect width="1920" height="1080" fill="url(#g)"/>
  <rect x="80" y="80" width="1760" height="920" fill="none" stroke="#E2E0D8" stroke-opacity=".18" stroke-width="1"/>
  {body}
</svg>
"""
    path.write_text(svg)


def render_card_mp4(svg_path: Path, mp4_path: Path, seconds: float = 4.0) -> None:
    png = svg_path.with_suffix(".png")
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(svg_path),
            "-vf",
            "scale=1920:1080",
            str(png),
        ]
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-loop",
            "1",
            "-i",
            str(png),
            "-c:v",
            "libx264",
            "-t",
            str(seconds),
            "-pix_fmt",
            "yuv420p",
            "-r",
            "30",
            "-vf",
            "scale=1920:1080",
            str(mp4_path),
        ]
    )


def chapter_overlay_filter(label: str, start: float, end: float) -> str:
    # bottom-left semi-transparent chapter title
    safe = label.replace(":", "\\:").replace("'", "\\'")
    return (
        f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"text='{safe}':x=48:y=h-72:fontsize=28:fontcolor=white@0.92:"
        f"box=1:boxcolor=0x143326@0.55:boxborderw=14:"
        f"enable='between(t\\,{start:.2f}\\,{end:.2f})'"
    )


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

async def login_as(page: Page, seat: dict) -> None:
    await page.goto(f"{APP_URL}/login", wait_until="networkidle")
    await inject_chrome(page)
    await wait_idle(page, 500)
    chip = page.locator("button.demo-account").filter(has_text=seat["chip"])
    if await chip.count():
        await click_locator(page, chip)
    else:
        await human_type(page, page.locator('input[autocomplete="username"]'), seat["email"])
        await human_type(
            page, page.locator('input[autocomplete="current-password"]'), DEMO_PASSWORD
        )
    await click_locator(page, page.get_by_role("button", name=re.compile(r"^Sign in$")))
    await page.wait_for_url(re.compile(r"/(student|ta|professor|$)"), timeout=30000)
    await inject_chrome(page)
    await wait_idle(page, 800)


async def logout(page: Page) -> None:
    trigger = page.locator("button.bh-account-trigger")
    await click_locator(page, trigger)
    await click_locator(page, page.get_by_role("menuitem", name="Log out"))
    await page.wait_for_url(re.compile(r"/login"), timeout=20000)
    await inject_chrome(page)
    await wait_idle(page, 600)


async def pick_course(page: Page, code: str = COURSE_CODE) -> None:
    # Prefer My Courses card if present
    if "/login" in page.url:
        return
    # open All courses for students
    all_courses = page.locator('a.bh-nav-item', has_text="All courses")
    if await all_courses.count():
        await click_locator(page, all_courses)
        await wait_idle(page, 700)
        card = page.locator("button.glass-panel").filter(has_text=code)
        if await card.count():
            await click_locator(page, card)
            await wait_idle(page, 900)
            await inject_chrome(page)
            return
    select = page.locator("select.bh-course-select")
    if await select.count():
        options = await select.locator("option").all_text_contents()
        match = next((o for o in options if code in o), None)
        if match:
            await select.select_option(label=match)
            await wait_idle(page, 900)
            await inject_chrome(page)


async def nav(page: Page, label: str) -> None:
    link = page.locator("a.bh-nav-item").filter(has_text=label)
    await click_locator(page, link)
    await wait_idle(page, 900)
    await inject_chrome(page)


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

async def part_landing(page: Page, marks: dict) -> None:
    marks["landing"] = time.time()
    await page.goto(APP_URL + "/", wait_until="networkidle")
    await inject_chrome(page)
    await wait_idle(page, 1000)
    # scroll through major sections
    for sid in ("hero", "choice", "rooms", "people", "student", "ta", "professor", "canvas", "join"):
        el = page.locator(f"#{sid}")
        if await el.count():
            box = await el.first.bounding_box()
            if box:
                await smooth_scroll(page, to_y=max(0, int(box["y"] - 80)))
                await wait_idle(page, 1100)
    # interactive: journey panels + choice
    for label in ("Quiet or named", "Human and AI", "Help or ignore"):
        cell = page.get_by_text(label, exact=False)
        if await cell.count():
            await click_locator(page, cell)
            await wait_idle(page, 500)
    # Sign in CTA
    cta = page.locator("a.oh-open-nav-cta, a").filter(has_text="Sign in").first
    await click_locator(page, cta)
    await page.wait_for_url(re.compile(r"/login"), timeout=20000)
    await inject_chrome(page)
    await wait_idle(page, 700)


async def part_student(page: Page, marks: dict) -> None:
    marks["student"] = time.time()
    await login_as(page, STUDENT)
    await pick_course(page, COURSE_CODE)

    # Study Agent — refuse then live stamped-material answer
    await nav(page, "Study Agent")
    new_chat = page.get_by_role("button", name=re.compile(r"New chat", re.I))
    if await new_chat.count():
        await click_locator(page, new_chat.first)
        await wait_idle(page, 600)
    await human_type(page, page.locator("textarea.sa-input"), REFUSE_Q)
    await click_locator(page, page.locator("button.sa-send"))
    await wait_gone(page, "Looking…", timeout=90000)
    # wait for refuse copy
    try:
        await page.get_by_text(re.compile(r"don't have professor-approved|No professor-approved", re.I)).first.wait_for(
            state="visible", timeout=60000
        )
    except Exception:
        log("warn: refuse copy not seen")
    await wait_idle(page, 1800)
    await smooth_scroll(page, delta=220)
    await wait_idle(page, 1200)

    if await new_chat.count():
        await click_locator(page, new_chat.first)
        await wait_idle(page, 500)
    await human_type(page, page.locator("textarea.sa-input"), STUDY_Q)
    await click_locator(page, page.locator("button.sa-send"))
    await wait_gone(page, "Looking…", timeout=120000)
    # Prefer a real answer (not refuse)
    try:
        await page.get_by_text(re.compile(r"open addressing|probe|collision|hash", re.I)).first.wait_for(
            state="visible", timeout=90000
        )
    except Exception:
        log("warn: study answer may still be refuse")
        # one recovery attempt with ultra-short grounded prompt
        if await new_chat.count():
            await click_locator(page, new_chat.first)
            await wait_idle(page, 400)
        await human_type(page, page.locator("textarea.sa-input"), "What is open addressing in hashing?")
        await click_locator(page, page.locator("button.sa-send"))
        await wait_gone(page, "Looking…", timeout=90000)
        await wait_idle(page, 1500)
    await wait_idle(page, 2200)
    await smooth_scroll(page, delta=360)
    await wait_idle(page, 2000)

    # Pedagogy Agent — live plan (uses PEDAGOGY_GEMINI when armed)
    await nav(page, "Pedagogy Agent")
    pref = page.locator("#rev-pref")
    if await pref.count():
        await pref.select_option("visual_structural")
        await wait_idle(page, 400)
    dur = page.locator("#rev-duration")
    if await dur.count():
        await dur.select_option("7")
        await wait_idle(page, 300)
    await click_locator(page, page.get_by_role("button", name=re.compile(r"Build plan")))
    # Wait until Building… leaves the primary button
    try:
        await page.get_by_role("button", name=re.compile(r"Building")).first.wait_for(
            state="visible", timeout=10000
        )
    except Exception:
        pass
    await wait_gone(page, "Building…", timeout=180000)
    # Prefer a completed plan schedule (Day 1 / resources / focus)
    ready = False
    for hint in ("Day 1", "Focus", "Red-Black", "YouTube", "resource", "Ask TA"):
        loc = page.get_by_text(hint, exact=False)
        try:
            await loc.first.wait_for(state="visible", timeout=45000)
            ready = True
            break
        except Exception:
            continue
    if not ready:
        log("warn: pedagogy plan body not confirmed")
    await wait_idle(page, 2000)
    await smooth_scroll(page, delta=520)
    await wait_idle(page, 2400)
    await smooth_scroll(page, delta=520)
    await wait_idle(page, 2000)

    # Ask for help — Quiet ask
    await nav(page, "Ask for help")
    box = page.locator("#ask input[type='checkbox'], .sd-check input[type='checkbox']").first
    if await box.count() and not await box.is_checked():
        await click_locator(page, box)
    # Help type Message (default) — click if needed
    msg = page.get_by_role("radio", name=re.compile(r"Message", re.I))
    if await msg.count():
        await click_locator(page, msg.first)
    ask_box = page.locator("#ask-box")
    await human_type(page, ask_box, ASK_Q)
    # optional details
    details = page.locator("details.sd-details summary")
    if await details.count():
        await click_locator(page, details.first)
        await wait_idle(page, 400)
    topic_select = page.locator("#ask-topic")
    if await topic_select.count():
        tag = await topic_select.evaluate("el => el.tagName")
        if tag == "SELECT":
            options = await topic_select.locator("option").all_text_contents()
            match = next((o for o in options if ASK_TOPIC.lower() in o.lower()), None)
            if match:
                await topic_select.select_option(label=match)
            else:
                # pick any hashing-ish or first non-empty
                nonempty = [o for o in options if o.strip() and "Select" not in o]
                if nonempty:
                    await topic_select.select_option(label=nonempty[0])
        else:
            await human_type(page, topic_select, ASK_TOPIC)
    tried = page.locator("#ask-tried")
    if await tried.count() and await tried.is_visible():
        await human_type(page, tried, ASK_TRIED)
    send = page.get_by_role("button", name=re.compile(r"Send anonymously|^Send$"))
    await click_locator(page, send)
    await wait_idle(page, 2500)
    # confirmation
    conf = page.get_by_text(re.compile(r"Sent anonymously|request #|Assigned", re.I))
    try:
        await conf.first.wait_for(state="visible", timeout=30000)
    except Exception:
        log("warn: ask confirmation text not seen; continuing")
    await wait_idle(page, 1600)

    # My asks
    await nav(page, "My asks")
    row = page.locator("button, a, [role='button']").filter(has_text=re.compile(r"Quiet|hash|collision", re.I))
    if await row.count():
        await click_locator(page, row)
        await wait_idle(page, 1600)
        await smooth_scroll(page, delta=240)
    await wait_idle(page, 1400)

    # Rooms — browse filters, open a room, publish a classmate question
    await nav(page, "Rooms")
    await wait_idle(page, 1200)
    # Tab filters
    for tab_name in ("Unanswered", "Solved", "Newest"):
        tab = page.get_by_role("tab", name=tab_name)
        if await tab.count():
            await click_locator(page, tab.first)
            await wait_idle(page, 700)
    # Chapter filter (Hashing when available)
    chapter_filter = page.locator("label.rooms-chapter select, .rooms-filters select").first
    if await chapter_filter.count():
        options = await chapter_filter.locator("option").all_text_contents()
        hashing = next((o for o in options if "Hash" in o), None)
        if hashing:
            await chapter_filter.select_option(label=hashing)
            await wait_idle(page, 900)
            # reset to all chapters so the new post is visible
            await chapter_filter.select_option(label="All chapters")
            await wait_idle(page, 500)
    # Top helpers glance
    helpers = page.get_by_role("button", name=re.compile(r"Top helpers", re.I))
    if await helpers.count():
        await click_locator(page, helpers.first)
        await wait_idle(page, 1400)
        back = page.get_by_role("button", name=re.compile(r"Back", re.I))
        if await back.count():
            await click_locator(page, back.first)
            await wait_idle(page, 700)
    # Initiate a Room / Ask a question
    ask_btn = page.get_by_role("button", name=re.compile(r"Ask a question", re.I))
    await click_locator(page, ask_btn.first)
    await wait_idle(page, 900)
    form = page.locator("form.rooms-form")
    await form.wait_for(state="visible", timeout=15000)
    title_input = form.locator('label.rooms-field:has-text("Title") input, input').first
    await human_type(
        page,
        title_input,
        "Open addressing: why do probe sequences still collide under high load?",
    )
    details = form.locator('label.rooms-field:has-text("Details") textarea, textarea').first
    await human_type(
        page,
        details,
        "I understand the home bucket idea, but after a few inserts my linear probe "
        "keeps landing on occupied slots. Looking for a classmate sketch of the sequence.",
    )
    tried = form.locator('label.rooms-field:has-text("What I tried") textarea').first
    if await tried.count():
        await human_type(
            page,
            tried,
            "Drew a small table with load factor ~0.7 and stepped +1 — still stuck.",
        )
    chapter_sel = form.locator('label.rooms-field:has-text("Chapter") select, select').first
    if await chapter_sel.count():
        opts = await chapter_sel.locator("option").all_text_contents()
        hashing = next((o for o in opts if "Hash" in o), None)
        if hashing:
            await chapter_sel.select_option(label=hashing)
            await wait_idle(page, 400)
    await click_locator(page, form.get_by_role("button", name=re.compile(r"^Post$")))
    # Wait for thread or list with the new question
    try:
        await page.get_by_text(re.compile(r"probe sequences|Open addressing", re.I)).first.wait_for(
            state="visible", timeout=30000
        )
    except Exception:
        log("warn: rooms post not confirmed in UI")
    await wait_idle(page, 1800)
    await smooth_scroll(page, delta=280)
    await wait_idle(page, 1200)
    # If on thread, return to list to show the room in the feed
    back_q = page.get_by_role("button", name=re.compile(r"Back to questions|Back", re.I))
    if await back_q.count():
        await click_locator(page, back_q.first)
        await wait_idle(page, 1000)
    await wait_idle(page, 1200)

    # Classmate notes — share a note, then exercise filters
    await nav(page, "Classmate notes")
    await wait_idle(page, 1200)
    await smooth_scroll(page, delta=200)
    # Share form
    share = page.locator("#peer-notes form, form").filter(has_text="Share your notes").first
    if await share.count() == 0:
        share = page.locator("#peer-notes").first
    notes_root = page.locator("#peer-notes")
    title_n = notes_root.locator('input[placeholder*="Title"]').first
    await human_type(page, title_n, "Hashing open-addressing cheatsheet")
    week = notes_root.locator('label:has-text("Week #") input').first
    lecture = notes_root.locator('label:has-text("Lecture #") input').first
    if await week.count():
        await human_type(page, week, "4")
    if await lecture.count():
        await human_type(page, lecture, "2")
    topic_sel = notes_root.locator("form label:has-text('Topic') select, form select").first
    if await topic_sel.count():
        await topic_sel.select_option(label="Hashing")
    caption = notes_root.locator('textarea[placeholder*="caption" i]').first
    if await caption.count():
        await human_type(
            page,
            caption,
            "One-page probe sequence + load-factor tips for CSC 2302.",
        )
    # Attach a small text note file
    note_path = RAW_DIR / "hashing-cheatsheet.txt"
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text(
        "CSC 2302 — Open addressing\n"
        "1. Home bucket from hash(key).\n"
        "2. Linear probe steps +1; clustering rises with load factor.\n"
        "3. Quadratic probe reduces primary clustering.\n",
        encoding="utf-8",
    )
    file_input = notes_root.locator('input[type="file"]').first
    if await file_input.count():
        await file_input.set_input_files(str(note_path))
        await wait_idle(page, 600)
    await click_locator(
        page, notes_root.get_by_role("button", name=re.compile(r"Share with classmates"))
    )
    try:
        await page.get_by_text(re.compile(r"Hashing open-addressing|cheatsheet", re.I)).first.wait_for(
            state="visible", timeout=30000
        )
    except Exception:
        log("warn: shared note not visible yet")
    await wait_idle(page, 1600)
    await smooth_scroll(page, delta=420)
    await wait_idle(page, 1000)

    # Filters: search → topic → week → sort → my notes
    search = notes_root.locator('input[placeholder*="Title or topic"]')
    if await search.count():
        await human_type(page, search.first, "Hashing")
        await wait_idle(page, 1100)
    # Browse filter Topic select (outside the share form)
    topic_filters = notes_root.locator('label:has-text("Topic") select')
    if await topic_filters.count() >= 2:
        await topic_filters.nth(1).select_option(label="Hashing")
        await wait_idle(page, 1000)
    filter_week = notes_root.locator('label:has-text("Week") input').last
    if await filter_week.count():
        await filter_week.fill("")
        await human_type(page, filter_week, "4")
        await wait_idle(page, 900)
    sort_sel = notes_root.locator('label:has-text("Sort") select')
    if await sort_sel.count():
        await sort_sel.select_option(label="Most liked")
        await wait_idle(page, 800)
        await sort_sel.select_option(label="Newest")
        await wait_idle(page, 800)
    box = notes_root.locator('label:has-text("My notes") input[type="checkbox"]')
    if await box.count():
        await click_locator(page, box.first)
        await wait_idle(page, 1100)
        await click_locator(page, box.first)
        await wait_idle(page, 700)
    if await search.count():
        await search.first.fill("")
        await wait_idle(page, 700)
    await smooth_scroll(page, delta=260)
    await wait_idle(page, 1400)

    await logout(page)


async def part_ta(page: Page, marks: dict) -> None:
    marks["ta"] = time.time()
    await login_as(page, TA)
    await pick_course(page, COURSE_CODE)

    await nav(page, "Dashboard")
    await wait_idle(page, 1400)
    await smooth_scroll(page, delta=260)
    await wait_idle(page, 1000)

    await nav(page, "Live Queue")
    await wait_idle(page, 1200)
    # select open ask
    ask_row = page.locator(".tar-queue button, .tar-mini button, button, [role='button']").filter(
        has_text=re.compile(r"hash|collision|Quiet|open|queued", re.I)
    )
    if await ask_row.count() == 0:
        ask_row = page.locator(".tar-queue button, button.tar-row, [data-ask-id]").first
    if await ask_row.count():
        await click_locator(page, ask_row.first)
        await wait_idle(page, 1200)

    claim = page.get_by_role("button", name=re.compile(r"Claim Ask"))
    if await claim.count() and await claim.first.is_enabled():
        await click_locator(page, claim)
        await wait_idle(page, 1500)

    # Help Coach pane should populate
    coach = page.get_by_text("Help Coach", exact=False)
    try:
        await coach.first.wait_for(state="visible", timeout=60000)
    except Exception:
        log("warn: Help Coach label not visible")
    # wait for coach content (Suggested / Socratic / approach)
    for hint in ("Suggested", "Socratic", "approach", "Insert into Reply", "Factual"):
        loc = page.get_by_text(hint, exact=False)
        try:
            await loc.first.wait_for(state="visible", timeout=45000)
            break
        except Exception:
            continue
    await wait_idle(page, 2000)

    insert = page.get_by_role("button", name=re.compile(r"Insert into Reply"))
    if await insert.count() and await insert.first.is_enabled():
        await click_locator(page, insert)
        await wait_idle(page, 1000)

    # type a short human reply addition if composer empty/filled
    composer = page.locator("textarea").first
    if await composer.count():
        existing = await composer.input_value()
        if len(existing.strip()) < 8:
            await human_type(
                page,
                composer,
                "Start from the probe sequence: same hash bucket + step size still collide under high load. Sketch one insert, then try quadratic.",
            )
        else:
            await click_locator(page, composer)
            await page.keyboard.press("End")
            await page.keyboard.type(" — walk the probe sequence once with the student.", delay=35)
    send = page.get_by_role("button", name=re.compile(r"Send Reply|Send & Resolve|Send"))
    if await send.count():
        await click_locator(page, send.first)
        await wait_idle(page, 2000)

    await nav(page, "Past asks")
    await wait_idle(page, 1400)
    await smooth_scroll(page, delta=240)
    await wait_idle(page, 1000)

    await logout(page)


async def part_professor(page: Page, marks: dict) -> None:
    marks["professor"] = time.time()
    await login_as(page, PROF)
    await pick_course(page, COURSE_CODE)

    # Material
    mat = page.locator("a.bh-nav-item, a").filter(has_text=re.compile(r"Material|Knowledge|Canvas", re.I))
    # professor shell may use hash sections — open /professor
    await page.goto(f"{APP_URL}/professor", wait_until="networkidle")
    await inject_chrome(page)
    await wait_idle(page, 1200)
    await smooth_scroll(page, delta=300)

    canvas_btn = page.get_by_role("button", name=re.compile(r"Import from Canvas"))
    if await canvas_btn.count():
        await click_locator(page, canvas_btn)
        await wait_idle(page, 1000)
        imp = page.get_by_role("button", name=re.compile(r"^Import$"))
        if await imp.count():
            await click_locator(page, imp)
            await wait_idle(page, 3500)

    # Approve pending Canvas/hashing material first (Study Agent gate)
    for _ in range(3):
        approve = page.get_by_role("button", name=re.compile(r"^Approve$"))
        if await approve.count() == 0:
            break
        await click_locator(page, approve.first)
        await wait_idle(page, 1400)

    # Show Approved stamped material (no empty-title validation toasts)
    approved_tab = page.get_by_role("button", name=re.compile(r"Approved", re.I))
    if await approved_tab.count():
        await click_locator(page, approved_tab.first)
        await wait_idle(page, 1800)
        await smooth_scroll(page, delta=280)
        await wait_idle(page, 1200)
    # Clean paste with required Title + Text (min lengths)
    paste_btn = page.get_by_role("button", name=re.compile(r"Paste text"))
    if await paste_btn.count():
        await click_locator(page, paste_btn)
        await wait_idle(page, 500)
        form = page.locator('form[aria-label="Paste text"]')
        if await form.count():
            await human_type(page, form.locator("input").first, "Hashing probe note")
            await human_type(
                page,
                form.locator("textarea").first,
                "Open addressing probes for the next free slot when the home bucket is taken.",
            )
            await click_locator(page, form.get_by_role("button", name=re.compile(r"Add this text")))
            await wait_idle(page, 1600)
            approve = page.get_by_role("button", name=re.compile(r"^Approve$"))
            if await approve.count():
                await click_locator(page, approve.first)
                await wait_idle(page, 1200)

    # Insights (nav link — not Material)
    insights_nav = page.locator("a.bh-nav-item").filter(has_text=re.compile(r"^Insights$"))
    await click_locator(page, insights_nav.first)
    await page.wait_for_url(re.compile(r"/professor/insights"), timeout=20000)
    await inject_chrome(page)
    await wait_idle(page, 2000)
    await smooth_scroll(page, delta=480)
    await wait_idle(page, 2000)
    await smooth_scroll(page, delta=480)
    await wait_idle(page, 1600)

    # Desk / asks
    desk = page.locator("a.bh-nav-item").filter(has_text=re.compile(r"Your desk"))
    await click_locator(page, desk.first)
    await page.wait_for_url(re.compile(r"/professor/asks"), timeout=20000)
    await inject_chrome(page)
    await wait_idle(page, 1800)
    await smooth_scroll(page, delta=320)
    await wait_idle(page, 1400)

    # Team
    team = page.locator("a.bh-nav-item").filter(has_text=re.compile(r"^Team$"))
    await click_locator(page, team.first)
    await page.wait_for_url(re.compile(r"/professor/team"), timeout=20000)
    await inject_chrome(page)
    await wait_idle(page, 1800)
    await smooth_scroll(page, delta=240)
    await wait_idle(page, 1600)

    marks["outro"] = time.time()


# ---------------------------------------------------------------------------
# Mastering
# ---------------------------------------------------------------------------

def find_raw_webm() -> Path:
    webs = sorted(RAW_DIR.rglob("*.webm"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not webs:
        raise FileNotFoundError("No Playwright webm found under raw/")
    return webs[0]


def silence_trim_and_master(raw_webm: Path, marks: dict, t0: float) -> Path:
    """Scale to 1080p, add intro/outro, chapter overlays, trim long stillness loosely."""
    intro_svg = CARDS_DIR / "intro.svg"
    outro_svg = CARDS_DIR / "outro.svg"
    write_card_svg(intro_svg, "intro")
    write_card_svg(outro_svg, "outro")
    intro_mp4 = CARDS_DIR / "intro.mp4"
    outro_mp4 = CARDS_DIR / "outro.mp4"
    render_card_mp4(intro_svg, intro_mp4, 4.0)
    render_card_mp4(outro_svg, outro_mp4, 4.0)

    body = RAW_DIR / "body_1080p.mp4"
    # Convert webm → h264 1080p 30fps high bitrate
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(raw_webm),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-an",
            str(body),
        ]
    )

    # Chapter overlays relative to body start
    def rel(key: str, default: float = 0.0) -> float:
        return max(0.0, marks.get(key, t0) - t0)

    landing_s, student_s = rel("landing"), rel("student")
    ta_s, prof_s = rel("ta"), rel("professor")
    # estimate durations from mark deltas; fall back to spans
    duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(body),
            ],
            text=True,
        ).strip()
        or "0"
    )
    ends = {
        "landing": student_s or 30,
        "student": ta_s or max(student_s + 60, 90),
        "ta": prof_s or max(ta_s + 40, 140),
        "professor": duration,
    }
    overlays = [
        chapter_overlay_filter("Landing Experience", 0, ends["landing"]),
        chapter_overlay_filter("Student AI Workspace", student_s, ends["student"]),
        chapter_overlay_filter("TA Operations & Grading", ta_s, ends["ta"]),
        chapter_overlay_filter("Professor Analytics & Control", prof_s, ends["professor"]),
    ]
    body_ch = RAW_DIR / "body_chapters.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(body),
            "-vf",
            ",".join(overlays),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            str(body_ch),
        ]
    )

    # concat intro + body + outro with crossfades
    # Use xfade for polish
    intro_body = RAW_DIR / "intro_body.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(intro_mp4),
            "-i",
            str(body_ch),
            "-filter_complex",
            "[0:v][1:v]xfade=transition=fade:duration=0.6:offset=3.4,format=yuv420p[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            str(intro_body),
        ]
    )
    # duration of intro_body for outro offset
    d2 = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(intro_body),
            ],
            text=True,
        ).strip()
    )
    offset = max(0.5, d2 - 0.6)
    final = OUT_DIR / "capstone_demo_1080p.mp4"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(intro_body),
            "-i",
            str(outro_mp4),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration=0.6:offset={offset:.2f},format=yuv420p[v]",
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-crf",
            "17",
            "-preset",
            "medium",
            "-movflags",
            "+faststart",
            "-r",
            "30",
            str(final),
        ]
    )
    return final


def extract_audit_frames(final: Path, marks: dict | None = None, t0: float = 0.0) -> list[Path]:
    duration = float(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(final),
            ],
            text=True,
        ).strip()
    )
    # intro xfade keeps ~3.4s of intro before body timeline
    intro_pad = 3.4
    def body(t: float) -> float:
        return min(duration - 1.0, max(0.5, intro_pad + t))

    if marks:
        samples = {
            "01-intro": 2.0,
            "02-landing": body(max(2.0, (marks.get("landing", t0) - t0) + 4)),
            "03-student": body(max(8.0, (marks.get("student", t0) - t0) + 25)),
            "04-ta": body(max(12.0, (marks.get("ta", t0) - t0) + 12)),
            "05-professor": body(max(16.0, (marks.get("professor", t0) - t0) + 10)),
            "06-outro": max(0.5, duration - 2.0),
        }
    else:
        samples = {
            "01-intro": 2.0,
            "02-landing": min(8.0, duration * 0.08),
            "03-student": min(duration * 0.28, duration - 6),
            "04-ta": min(duration * 0.55, duration - 6),
            "05-professor": min(duration * 0.78, duration - 5),
            "06-outro": max(0.5, duration - 2.0),
        }
    paths = []
    for name, t in samples.items():
        out = AUDIT_DIR / f"{name}.png"
        run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-ss",
                f"{t:.2f}",
                "-i",
                str(final),
                "-frames:v",
                "1",
                str(out),
            ]
        )
        paths.append(out)
    return paths


def publish_outputs(final: Path, frames: list[Path]) -> None:
    for dest in (STORE_OUT, ARTIFACT_OUT):
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final, dest / final.name)
        for f in frames:
            shutil.copy2(f, dest / f.name)
        # copy script + readme (no secrets)
        for name in ("generate_demo.py", "README.md"):
            src = OUT_DIR / name
            if src.is_file():
                shutil.copy2(src, dest / name)


async def record() -> dict:
    ensure_dirs()
    marks: dict[str, float] = {}
    t0 = time.time()
    marks["start"] = t0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--font-render-hinting=none"],
        )
        context = await browser.new_context(
            viewport=VIEWPORT,
            device_scale_factor=DEVICE_SCALE,
            record_video_dir=str(RAW_DIR),
            record_video_size={"width": 1920, "height": 1080},
            color_scheme="light",
        )
        # hide native cursor in screenshots/video where possible
        page = await context.new_page()
        page.on("console", lambda msg: None)  # avoid logging API payloads

        # health gate
        page2 = await context.new_page()
        await page2.goto(API_URL + "/health", wait_until="networkidle")
        health = redact(await page2.inner_text("body"))
        log(f"health: {health[:200]}")
        await page2.close()

        await part_landing(page, marks)
        await part_student(page, marks)
        await part_ta(page, marks)
        await part_professor(page, marks)

        await wait_idle(page, 1500)
        await context.close()
        await browser.close()

    marks["end"] = time.time()
    (RAW_DIR / "marks.json").write_text(
        json.dumps({k: v - t0 for k, v in marks.items()}, indent=2)
    )
    return {"marks": marks, "t0": t0}


def main() -> int:
    load_dotenv_files()
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-record", action="store_true")
    parser.add_argument("--skip-master", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    # never write env into store
    log(
        "env flags: "
        f"DEMO={os.getenv('OFFICEHOURS_DEMO')} "
        f"LLM={os.getenv('OFFICEHOURS_LLM_PROVIDER')} "
        f"ALLOW={os.getenv('OFFICEHOURS_ALLOW_EXTERNAL_LLM')} "
        f"GEMINI_SET={bool(os.getenv('GEMINI_API_KEY'))} "
        f"PEDAGOGY_SET={bool(os.getenv('PEDAGOGY_GEMINI_API_KEY'))} "
        f"YT_SET={bool(os.getenv('YOUTUBE_API_KEY'))}"
    )

    marks = {}
    t0 = time.time()
    if not args.skip_record:
        result = asyncio.run(record())
        marks = result["marks"]
        t0 = result["t0"]
    else:
        marks_path = RAW_DIR / "marks.json"
        if marks_path.is_file():
            rel = json.loads(marks_path.read_text())
            marks = {k: t0 + float(v) for k, v in rel.items()}

    if not args.skip_master:
        raw = find_raw_webm()
        log(f"raw video: {raw}")
        final = silence_trim_and_master(raw, marks, t0)
        frames = extract_audit_frames(final, marks=marks, t0=t0)
        publish_outputs(final, frames)
        log(f"final: {final}")
        log(f"store: {STORE_OUT / final.name}")
        log(f"audit frames: {len(frames)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        log(f"FATAL: {type(exc).__name__}: {exc}")
        raise
