import { chromium } from "playwright";
import { copyFile, mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");
const ARTIFACT_DIR = "/opt/cursor/artifacts/screenshots";

const KIOSK_URL = "http://127.0.0.1:5173";
const DASHBOARD_URL = "http://127.0.0.1:5174";
const TA_URL = "http://127.0.0.1:5175";

async function capture(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
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

  // --- Student kiosk ---
  const kiosk = await context.newPage();
  await kiosk.goto(KIOSK_URL, { waitUntil: "networkidle" });
  await kiosk.getByPlaceholder("e.g. 117027").fill("117027");
  await capture(kiosk, "oracle-01-student-kiosk-checkin");

  await kiosk.getByRole("button", { name: "Ask KB agent" }).click();
  await kiosk.waitForSelector("text=Ask approved answers");
  await capture(kiosk, "oracle-02-student-kb-agent-empty");

  await kiosk
    .getByPlaceholder(/recursion base cases/i)
    .fill("How do I think about recursion with a small example?");
  await kiosk.getByRole("button", { name: "Ask", exact: true }).click();
  await kiosk.waitForSelector("text=Matched", { timeout: 15000 });
  await capture(kiosk, "oracle-03-student-kb-agent-answer");

  await kiosk.getByRole("button", { name: "Back" }).click();
  await kiosk.waitForSelector("text=Enter your student ID");
  await kiosk.getByPlaceholder("e.g. 117027").fill("117027");
  await kiosk.getByRole("button", { name: "Continue identified" }).click();
  await kiosk.waitForSelector("text=Ask for help");
  const questionBox = kiosk.locator("textarea").first();
  await questionBox.fill(
    "Please walk me through the steps of binary search on a sorted array for the final.",
  );
  await capture(kiosk, "oracle-04-student-request-form");
  await kiosk.getByRole("button", { name: "Submit request" }).click();
  await kiosk.waitForSelector("text=Request submitted", { timeout: 15000 });
  await capture(kiosk, "oracle-05-student-confirmation");

  // --- TA dashboard ---
  const ta = await context.newPage();
  await ta.goto(TA_URL, { waitUntil: "networkidle" });
  await ta.waitForSelector("text=TA Dashboard");
  await ta.waitForSelector("text=Open queue");
  // Wait for queue items or empty state
  await ta.waitForTimeout(1000);
  await capture(ta, "oracle-06-ta-dashboard-queue");

  const firstQueueItem = ta.locator("section").filter({ hasText: "Open queue" }).locator("button").first();
  if (await firstQueueItem.count()) {
    await firstQueueItem.click();
    await ta.waitForSelector("text=Teaching approach");
    await capture(ta, "oracle-07-ta-teaching-draft");
  }

  // --- Professor dashboard ---
  const prof = await context.newPage();
  await prof.goto(DASHBOARD_URL, { waitUntil: "networkidle" });
  await prof.waitForSelector("text=Professor Dashboard");
  await prof.waitForSelector("text=Curation queue", { timeout: 15000 });
  await capture(prof, "oracle-08-professor-overview");

  await prof.locator("text=Struggle heatmap").scrollIntoViewIfNeeded();
  await capture(prof, "oracle-09-struggle-heatmap-escalations");

  await prof.locator("text=Curation queue").scrollIntoViewIfNeeded();
  await capture(prof, "oracle-10-kb-curation-queue");

  // Show approved filter
  await prof.getByRole("button", { name: "Approved" }).click();
  await prof.waitForTimeout(800);
  await capture(prof, "oracle-11-kb-approved-entries");

  // Live indicator close-up via overview header
  await prof.locator("text=Professor Dashboard").scrollIntoViewIfNeeded();
  await capture(prof, "oracle-12-professor-live-indicator");

  await browser.close();
  console.log("All oracle visuals captured.");
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
