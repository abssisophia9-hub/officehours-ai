/**
 * Visual test for student onboarding + feature differentiation (light + dark).
 */
import { chromium } from "playwright";
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");
const ARTIFACT_DIR = "/opt/cursor/artifacts/screenshots";
const APP = "http://127.0.0.1:5180";

async function capture(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  await mkdir(ARTIFACT_DIR, { recursive: true });
  await copyFile(filePath, path.join(ARTIFACT_DIR, `${name}.png`));
  console.log(`Saved ${name}.png`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("officehours_theme", "light");
    document.documentElement.setAttribute("data-theme", "light");
  });
  await page.reload({ waitUntil: "networkidle" });
  await page
    .locator('input[placeholder*="aui.ma"], input[autocomplete="username"]')
    .first()
    .fill("s.elidrissi@aui.ma");
  await page.locator('input[type="password"]').first().fill("aui-demo");
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/\/student/, { timeout: 15000 });
  await page.waitForTimeout(800);

  const select = page.locator("select").first();
  const options = await select.locator("option").allTextContents();
  const match = options.find((t) => t.includes("CSC 2302"));
  if (match) {
    await select.selectOption({ label: match });
    await page.waitForTimeout(1000);
  }

  await page.goto(`${APP}/student`, { waitUntil: "networkidle" });
  await page.locator("h1.sd-title").waitFor({ timeout: 15000 });
  await page.locator(".sd-onboard").waitFor({ timeout: 8000 });
  await page.waitForTimeout(600);
  await capture(page, "sd-04-onboard-light");

  await page.locator(".sd-onboard .sd-cta").click();
  await page.waitForTimeout(700);
  await page.locator(".sd-ask-guide").waitFor({ timeout: 5000 });
  await capture(page, "sd-05-quickstart-ask-light");

  await page.locator(".sd-path").filter({ hasText: "Study Agent" }).click();
  await page.waitForTimeout(700);
  await page.locator("#agent .sd-guide").waitFor({ timeout: 5000 });
  await capture(page, "sd-06-quickstart-agent-light");

  await page.evaluate(() => {
    localStorage.setItem("officehours_theme", "dark");
    document.documentElement.setAttribute("data-theme", "dark");
  });
  await page.waitForTimeout(500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(400);
  await capture(page, "sd-07-onboard-dark");

  const checks = {
    onboardDismissed: await page.locator(".sd-onboard").count(),
    paths: await page.locator(".sd-path").count(),
    pathPrimary: await page.locator(".sd-path-primary").count(),
    navGroups: await page.locator(".bh-nav-group").count(),
    startBadge: await page.locator(".bh-nav-badge").count(),
    navHints: await page.locator(".bh-nav-hint").count(),
    theme: await page.evaluate(() => document.documentElement.getAttribute("data-theme")),
  };
  console.log("checks", checks);
  if (
    checks.onboardDismissed !== 0 ||
    checks.paths !== 3 ||
    checks.pathPrimary !== 1 ||
    checks.navGroups < 3 ||
    checks.startBadge < 1 ||
    checks.navHints < 4
  ) {
    throw new Error(`Unexpected onboarding layout: ${JSON.stringify(checks)}`);
  }

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
