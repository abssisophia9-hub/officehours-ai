/**
 * Capture unified product (:5180) screenshots for the FYP final report.
 *
 * Prereq: backend :8000 + officehours-app :5180 running.
 *
 *   cd /workspace/demo && node capture_product_screenshots.mjs
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
  await page.waitForTimeout(500);
  // Already logged in → go to login by clearing storage
  await page.evaluate(() => {
    localStorage.clear();
    sessionStorage.clear();
  });
  await page.goto(APP, { waitUntil: "networkidle" });
  await page.locator('input[placeholder*="aui.ma"], input[autocomplete="username"]').first().fill(email);
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
        const value = await select.locator("option", { hasText: code }).first().getAttribute("value");
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

  await page.goto(APP, { waitUntil: "networkidle" });
  await capture(page, "product-01-login");

  await login(page, "s.elidrissi@aui.ma");
  await page.goto(`${APP}/student`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1000);
  await pickCourse(page, "CSC 2302");
  await capture(page, "product-02-student-ask");

  const textarea = page.locator("#ask textarea, textarea").first();
  await textarea.waitFor({ timeout: 10000 });
  await textarea.fill(
    "I still don't understand red-black tree deletion rotations for CSC 2302.",
  );
  const quiet = page.getByText("Quiet ask", { exact: false }).first();
  if (await quiet.count()) await quiet.click().catch(() => {});
  await page.getByRole("button", { name: /Submit anonymously|Submit as me|Running Ask Triage/i }).first().click();
  await page.waitForSelector("text=/Analyzer|Matcher|Hint|Submitted/i", { timeout: 20000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await capture(page, "product-03-ask-triage-result");

  await login(page, "a.chen@aui.ma");
  await page.goto(`${APP}/ta`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1000);
  await pickCourse(page, "CSC 2302");
  await page.waitForTimeout(1500);
  const claim = page.getByRole("button", { name: /Claim|Start helping|Help Coach|Assist|Open/i }).first();
  if (await claim.count()) await claim.click().catch(() => {});
  await page.waitForTimeout(1500);
  const coachTab = page.getByRole("button", { name: /Help Coach|Coach|Assist/i }).first();
  if (await coachTab.count()) await coachTab.click().catch(() => {});
  await page.waitForTimeout(1000);
  await capture(page, "product-04-ta-help-coach");

  await login(page, "a.benali@aui.ma");
  await page.goto(`${APP}/professor`, { waitUntil: "networkidle" }).catch(() => {});
  await page.waitForTimeout(1000);
  await pickCourse(page, "CSC 2302");
  await page.waitForTimeout(1500);
  await capture(page, "product-05-professor-kb");

  await page.goto(`${APP}/canvas-demo`, { waitUntil: "networkidle" });
  await page.waitForTimeout(1000);
  await capture(page, "product-06-canvas-simulator");

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
