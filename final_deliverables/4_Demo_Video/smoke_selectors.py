#!/usr/bin/env python3
"""Quick selector smoke (no long AI waits). Redacts secrets in output."""
from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_demo import (  # noqa: E402
    APP_URL,
    COURSE_CODE,
    DEMO_PASSWORD,
    STUDENT,
    click_locator,
    inject_chrome,
    load_dotenv_files,
    log,
    login_as,
    pick_course,
    redact,
)


async def main() -> None:
    load_dotenv_files()
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1920, "height": 1080})
        await page.goto(APP_URL + "/", wait_until="networkidle")
        await inject_chrome(page)
        for sid in ("hero", "choice", "rooms", "student", "ta", "professor", "join"):
            n = await page.locator(f"#{sid}").count()
            log(f"landing#{sid}={n}")
        await page.goto(APP_URL + "/login", wait_until="networkidle")
        chips = await page.locator("button.demo-account").count()
        log(f"demo_chips={chips}")
        await login_as(page, STUDENT)
        log(f"after_login={page.url}")
        await pick_course(page, COURSE_CODE)
        log(f"after_course={page.url}")
        for label in (
            "Study Agent",
            "Pedagogy Agent",
            "Ask for help",
            "My asks",
            "Rooms",
            "Classmate notes",
        ):
            n = await page.locator("a.bh-nav-item").filter(has_text=label).count()
            log(f"nav[{label}]={n}")
        await page.locator("a.bh-nav-item").filter(has_text="Study Agent").click()
        log(f"sa_input={await page.locator('textarea.sa-input').count()}")
        await browser.close()
    log("smoke_ok")


if __name__ == "__main__":
    asyncio.run(main())
