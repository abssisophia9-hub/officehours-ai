/**
 * Visual test: Ask is sole primary; Agent/Revision demoted; one lime focal.
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
  const page = await (await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  })).newPage();

  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    localStorage.clear();
    localStorage.setItem("officehours_theme", "light");
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
    await page.waitForTimeout(800);
  }

  await page.goto(`${APP}/student`, { waitUntil: "networkidle" });
  await page.locator("h1.sd-title").waitFor({ timeout: 15000 });
  await page.locator(".sd-onboard").waitFor({ timeout: 8000 });
  await page.waitForTimeout(500);
  await capture(page, "sd-08-ask-primary-light");

  await page.locator(".sd-onboard-go").click();
  await page.locator(".sd-ask-guide").waitFor({ timeout: 5000 });
  await page.waitForTimeout(400);
  await capture(page, "sd-09-ask-focused-light");

  await page.evaluate(() => {
    localStorage.setItem("officehours_theme", "dark");
    document.documentElement.setAttribute("data-theme", "dark");
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(500);
  await capture(page, "sd-10-ask-primary-dark");

  const checks = {
    pathCards: await page.locator(".sd-path").count(),
    altTools: await page.locator(".sd-alt-tools").count(),
    askCta: await page.locator(".sd-ask .sd-cta").count(),
    onboardCta: await page.locator(".sd-onboard .sd-cta").count(),
    navBadge: await page.locator(".bh-nav-badge").count(),
    onboard: await page.locator(".sd-onboard").count(),
    theme: await page.evaluate(() => document.documentElement.getAttribute("data-theme")),
  };
  console.log("checks", checks);
  if (
    checks.pathCards !== 0 ||
    checks.altTools !== 1 ||
    checks.askCta !== 1 ||
    checks.onboardCta !== 0 ||
    checks.navBadge !== 0 ||
    checks.onboard !== 0
  ) {
    throw new Error(`Hierarchy regression: ${JSON.stringify(checks)}`);
  }

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
