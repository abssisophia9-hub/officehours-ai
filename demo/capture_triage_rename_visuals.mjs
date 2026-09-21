/**
 * Visual test for the Ask Triage rename (PR #89) + Revision Strategist (PR #85).
 *
 * Prereq: backend :8000 + officehours-app :5180 running in demo mode.
 *
 *   cd /workspace/demo && node capture_triage_rename_visuals.mjs
 */
import { chromium } from "playwright";
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");
const ARTIFACT_DIR = "/opt/cursor/artifacts/screenshots";
const APP = "http://127.0.0.1:5180";
const PASSWORD = "aui-demo";

async function capture(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  await mkdir(ARTIFACT_DIR, { recursive: true });
  await copyFile(filePath, path.join(ARTIFACT_DIR, `${name}.png`));
  console.log(`Saved ${name}.png`);
}

async function login(page, email) {
  await page.goto(APP, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page
    .locator('input[placeholder*="aui.ma"], input[autocomplete="username"]')
    .first()
    .fill(email);
  await page.locator('input[type="password"]').first().fill(PASSWORD);
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/\/(student|ta|professor)/, { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);
}

async function pickCourse(page, code) {
  const select = page.locator("select").first();
  if (await select.count()) {
    const options = await select.locator("option").allTextContents();
    const match = options.find((t) => t.includes(code));
    if (match) {
      await select.selectOption({ label: match }).catch(async () => {
        const value = await select
          .locator("option", { hasText: code })
          .first()
          .getAttribute("value");
        if (value) await select.selectOption(value);
      });
      await page.waitForTimeout(1200);
    }
  }
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // 1. Student: submit an ask → Ask Triage panel rendered from `result.triage.*`.
  await login(page, "s.elidrissi@aui.ma");
  await page.goto(`${APP}/student`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1000);
  await pickCourse(page, "CSC 2302");

  const textarea = page.locator("#ask textarea, textarea").first();
  await textarea.waitFor({ timeout: 10000 });
  await textarea.fill(
    "I still don't understand red-black tree deletion rotations for CSC 2302.",
  );
  await page.waitForTimeout(800);
  const submit = page
    .getByRole("button", { name: /Submit anonymously|Submit as me|Submit/i })
    .first();
  await submit.click();
  // Ask Triage panel (Analyzer / Matcher / Synthesizer hint) or redirect to My asks.
  await page
    .waitForSelector("text=/Analyzer|Matcher|Synthesizer|routed your ask/i", {
      timeout: 25000,
    })
    .catch(() => {});
  await page.waitForTimeout(1800);
  await capture(page, "triage-01-student-ask-triage-result");

  // 2. My asks timeline (new #85 page) fed by renamed request fields.
  await page.goto(`${APP}/student/asks`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1500);
  await capture(page, "triage-02-student-my-asks");

  // 3. Revision Strategist (merged PR #85).
  await page
    .goto(`${APP}/student/revision`, { waitUntil: "networkidle" })
    .catch(() => {});
  await page.waitForTimeout(1500);
  await capture(page, "triage-03-revision-strategist");

  // 4. TA queue + detail: triage_category / triage_difficulty / req.triage.matcher.
  await login(page, "a.chen@aui.ma");
  await page.goto(`${APP}/ta`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1000);
  await pickCourse(page, "CSC 2302");
  await page.waitForTimeout(1500);
  const row = page.locator("table tbody tr").first();
  if (await row.count()) await row.click().catch(() => {});
  await page.waitForTimeout(1500);
  await capture(page, "triage-04-ta-queue-triage-fields");

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
