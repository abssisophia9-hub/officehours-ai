import { chromium } from "playwright";
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");
const ARTIFACT_DIR = "/opt/cursor/artifacts/screenshots";

async function shot(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: false });
  await copyFile(filePath, path.join(ARTIFACT_DIR, `${name}.png`));
  console.log(`Saved ${name}.png`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });
  await mkdir(ARTIFACT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });

  const prof = await context.newPage();
  await prof.goto("http://127.0.0.1:5174", { waitUntil: "networkidle" });
  await prof.waitForSelector("text=Curation queue");
  await shot(prof, "oracle-v-professor-header-live");

  await prof.locator("text=Struggle heatmap").scrollIntoViewIfNeeded();
  await prof.waitForTimeout(400);
  await shot(prof, "oracle-v-heatmap-escalations");

  await prof.locator("text=Curation queue").scrollIntoViewIfNeeded();
  await prof.waitForTimeout(400);
  await shot(prof, "oracle-v-curation-pending");

  await prof.getByRole("button", { name: "Approved" }).click();
  await prof.waitForTimeout(700);
  await prof.locator("text=Curation queue").scrollIntoViewIfNeeded();
  await shot(prof, "oracle-v-curation-approved");

  const ta = await context.newPage();
  await ta.goto("http://127.0.0.1:5175", { waitUntil: "networkidle" });
  await ta.waitForSelector("text=TA Dashboard");
  await ta.waitForTimeout(800);
  await shot(ta, "oracle-v-ta-live-queue");
  const item = ta.locator("section").filter({ hasText: "Open queue" }).locator("button").first();
  if (await item.count()) {
    await item.click();
    await ta.waitForSelector("text=Teaching approach");
    await shot(ta, "oracle-v-ta-draft-detail");
  }

  const kiosk = await context.newPage();
  await kiosk.goto("http://127.0.0.1:5173", { waitUntil: "networkidle" });
  await kiosk.getByRole("button", { name: "Ask KB agent" }).click();
  await kiosk.waitForSelector("text=Ask approved answers");
  await kiosk
    .getByPlaceholder(/recursion base cases/i)
    .fill("How do I think about recursion with a small example?");
  await kiosk.getByRole("button", { name: "Ask", exact: true }).click();
  await kiosk.waitForSelector("text=Matched");
  await shot(kiosk, "oracle-v-kb-agent-answer");

  await browser.close();
  console.log("Viewport visuals done.");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
