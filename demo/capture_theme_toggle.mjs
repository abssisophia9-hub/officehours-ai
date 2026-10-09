/**
 * Visual test for the light/dark theme toggle.
 * Prereq: officehours-app :5180 running.
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
    colorScheme: "light",
  });
  const page = await context.newPage();

  await page.goto(`${APP}/login`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);
  const theme = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  console.log("first visit theme:", theme, "stored:", await page.evaluate(() => localStorage.getItem("officehours_theme")));
  await capture(page, "theme-01-login-light");

  await page.getByRole("button", { name: /Switch to dark mode/i }).click();
  await page.waitForTimeout(500);
  const afterToggle = await page.evaluate(() => ({
    theme: document.documentElement.getAttribute("data-theme"),
    stored: localStorage.getItem("officehours_theme"),
  }));
  console.log("after toggle:", afterToggle);
  if (afterToggle.theme !== "dark" || afterToggle.stored !== "dark") {
    throw new Error("Toggle did not persist dark theme");
  }
  await capture(page, "theme-02-login-dark");

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForTimeout(600);
  const afterReload = await page.evaluate(() => document.documentElement.getAttribute("data-theme"));
  console.log("after reload:", afterReload);
  if (afterReload !== "dark") {
    throw new Error("Dark theme did not persist across reload");
  }

  await page.locator('input[type="password"]').first().fill("aui-demo");
  await page.getByRole("button", { name: /Sign in/i }).click();
  await page.waitForURL(/\/student/, { timeout: 15000 });
  await page.waitForTimeout(1200);
  await capture(page, "theme-03-student-dark");

  await page.getByRole("button", { name: /Switch to light mode/i }).click();
  await page.waitForTimeout(500);
  await capture(page, "theme-04-student-light");

  await browser.close();
  console.log("Done.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
