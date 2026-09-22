/**
 * Visual test for redesigned student dashboard (light + dark).
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
  await page.goto(`${APP}/student`, { waitUntil: "domcontentloaded" });
  await page.locator("h1.sd-title").waitFor({ timeout: 15000 });
  await page.waitForTimeout(800);

  await page.locator("#ask-box").fill(
    "I still don't understand red-black tree deletion rotations for CSC 2302.",
  );
  await page.waitForTimeout(300);
  await page.getByRole("button", { name: /Submit quietly/i }).click();
  await page.waitForTimeout(1600);
  await capture(page, "sd-01-student-light");

  await page.goto(`${APP}/student`, { waitUntil: "domcontentloaded" });
  await page.locator("h1.sd-title").waitFor({ timeout: 15000 });
  await page.waitForTimeout(800);
  await capture(page, "sd-02-student-light-home");

  await page.getByRole("button", { name: /Switch to dark mode/i }).click();
  await page.waitForTimeout(700);
  await capture(page, "sd-03-student-dark-home");

  console.log("checks ok", {
    quietRec: await page.getByText(/Recommended when you hesitate/i).count(),
    blocks: await page.getByText(/Block 1 · Start here/i).count(),
    community: await page.getByText(/Campus community/i).count(),
    theme: await page.evaluate(() => document.documentElement.getAttribute("data-theme")),
  });

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
