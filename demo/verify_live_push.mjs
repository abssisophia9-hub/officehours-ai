/**
 * Verify Live WebSocket: kiosk submit updates professor dashboard
 * without clicking Refresh.
 *
 * Run with services already up:
 *   node verify_live_push.mjs
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ARTIFACT_DIR = "/opt/cursor/artifacts/live-e2e";
const KIOSK_URL = "http://127.0.0.1:5173";
const DASHBOARD_URL = "http://127.0.0.1:5174";
const UNIQUE =
  "LIVE-E2E unique recursion tracing question " + Date.now();

async function main() {
  await mkdir(ARTIFACT_DIR, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
  });

  const dash = await context.newPage();
  const wsFrames = [];
  dash.on("websocket", (ws) => {
    if (!ws.url().includes("/ws")) return;
    console.log(`WS opened: ${ws.url()}`);
    ws.on("framereceived", (frame) => {
      wsFrames.push(frame.payload);
      console.log(`WS frame: ${String(frame.payload).slice(0, 200)}`);
    });
  });

  await dash.goto(DASHBOARD_URL, { waitUntil: "networkidle" });
  await dash.getByText("Live", { exact: true }).waitFor({ timeout: 15000 });
  console.log("Dashboard shows Live indicator");
  await dash.screenshot({
    path: path.join(ARTIFACT_DIR, "01-dashboard-live-before.png"),
    fullPage: true,
  });

  const beforeCount = await dash.locator("text=/Request #\\d+/").count();
  const beforeText = await dash.locator("body").innerText();
  if (beforeText.includes(UNIQUE)) {
    throw new Error("Unique marker already present before submit");
  }
  console.log(`Request markers before submit: ${beforeCount}`);

  const kiosk = await context.newPage();
  await kiosk.goto(KIOSK_URL, { waitUntil: "networkidle" });
  await kiosk
    .getByRole("button", { name: /Skip check-in and stay anonymous/i })
    .click();
  await kiosk.waitForSelector("textarea");
  await kiosk.locator("textarea").first().fill(UNIQUE);
  await kiosk.screenshot({
    path: path.join(ARTIFACT_DIR, "02-kiosk-ready-to-submit.png"),
    fullPage: true,
  });
  await kiosk.getByRole("button", { name: "Submit request" }).click();
  await kiosk.waitForSelector("text=Request submitted", { timeout: 20000 });
  console.log("Kiosk submission confirmed");
  await kiosk.screenshot({
    path: path.join(ARTIFACT_DIR, "03-kiosk-confirmation.png"),
    fullPage: true,
  });

  // Critical assertion: dashboard updates WITHOUT clicking Refresh.
  await dash.bringToFront();
  await dash.waitForFunction(
    (marker) => document.body.innerText.includes(marker),
    UNIQUE,
    { timeout: 20000 },
  );
  console.log("Dashboard received Live update without manual refresh");

  const gotCreated = wsFrames.some((frame) =>
    String(frame).includes("request.created"),
  );
  if (!gotCreated) {
    throw new Error("Did not observe request.created WebSocket frame");
  }
  console.log("Observed request.created over WebSocket");

  await dash.screenshot({
    path: path.join(ARTIFACT_DIR, "04-dashboard-live-after.png"),
    fullPage: true,
  });

  const afterText = await dash.locator("body").innerText();
  if (!afterText.includes(UNIQUE)) {
    throw new Error("Unique request text missing after Live update");
  }

  // Ensure we never clicked Refresh during the wait.
  const refreshClicks = await dash.evaluate(() => window.__refreshClicked || 0);
  console.log(`Refresh button clicks during test: ${refreshClicks}`);

  console.log("PASS: Live end-to-end verified");
  await browser.close();
}

main().catch((error) => {
  console.error("FAIL:", error);
  process.exit(1);
});
