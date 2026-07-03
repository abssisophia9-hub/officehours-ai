import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const OUT_DIR = path.join(__dirname, "screenshots");

const KIOSK_URL = "http://127.0.0.1:5173";
const DASHBOARD_URL = "http://127.0.0.1:5174";

async function capture(page, name) {
  const filePath = path.join(OUT_DIR, `${name}.png`);
  await page.screenshot({ path: filePath, fullPage: true });
  console.log(`Saved ${filePath}`);
}

async function main() {
  await mkdir(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  // 1. Student kiosk check-in
  await page.goto(KIOSK_URL, { waitUntil: "networkidle" });
  await page.getByPlaceholder("Scan barcode or type 117027").fill("117027");
  await capture(page, "01-student-kiosk-checkin");

  // 2. Student request form (anonymous toggle visible)
  await page.getByRole("button", { name: "Continue identified" }).click();
  await page.waitForSelector("text=How would you like to submit?");
  await capture(page, "02-student-request-form");

  // 3. Submission confirmation
  await page
    .getByPlaceholder(/recursion/i)
    .fill(
      "Can you explain how BFS and DFS differ for the graph algorithms final question?",
    );
  await page.getByRole("button", { name: "Submit request" }).click();
  await page.waitForSelector("text=Request submitted");
  await capture(page, "03-submission-confirmation");

  // 4. Professor dashboard overview
  const dashboard = await context.newPage();
  await dashboard.goto(DASHBOARD_URL, { waitUntil: "networkidle" });
  await dashboard.waitForSelector("text=Professor Dashboard");
  await dashboard.waitForSelector("text=Recommendation cockpit");
  await capture(dashboard, "04-professor-dashboard-overview");

  // 5. Recommendation cards
  await dashboard.locator("text=Pick the next move").scrollIntoViewIfNeeded();
  await capture(dashboard, "05-recommendation-cards");

  // 6. Action orchestration plan (approve first card)
  const approveButton = dashboard.getByRole("button", { name: "Approve" }).first();
  await approveButton.scrollIntoViewIfNeeded();
  await approveButton.click();
  await dashboard.waitForSelector("text=Next step generated", { timeout: 10000 });
  await capture(dashboard, "06-action-orchestration-plan");

  // 7. Survey templates (render markdown files in browser)
  const surveyPage = await context.newPage();
  const fs = await import("node:fs/promises");
  const studentSurvey = await fs.readFile(
    path.join(__dirname, "../docs/surveys/student_post_demo_survey.md"),
    "utf8",
  );
  const professorSurvey = await fs.readFile(
    path.join(__dirname, "../docs/surveys/professor_post_demo_survey.md"),
    "utf8",
  );
  const escapeHtml = (value) =>
    value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");

  const surveyHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Evaluation Survey Templates</title>
  <style>
    body { font-family: Georgia, serif; max-width: 960px; margin: 40px auto; padding: 0 24px; color: #0f172a; background: #f8fafc; }
    p { font-family: system-ui, sans-serif; color: #475569; }
    h1 { font-family: system-ui, sans-serif; }
    section { background: white; border: 1px solid #e2e8f0; border-radius: 16px; padding: 24px; margin: 24px 0; box-shadow: 0 8px 24px rgba(15,23,42,.06); }
    h2 { margin-top: 0; font-family: system-ui, sans-serif; color: #4338ca; }
    pre { white-space: pre-wrap; line-height: 1.6; font-size: 15px; margin: 0; }
  </style>
</head>
<body>
  <h1>OfficeHours AI — Evaluation Survey Templates</h1>
  <p>Student and professor post-demo surveys for usability and impact evaluation.</p>
  <section><h2>Student Post-Demo Survey</h2><pre>${escapeHtml(studentSurvey)}</pre></section>
  <section><h2>Professor Post-Demo Survey</h2><pre>${escapeHtml(professorSurvey)}</pre></section>
</body>
</html>`;

  await surveyPage.setContent(surveyHtml, { waitUntil: "domcontentloaded" });
  await capture(surveyPage, "07-survey-templates");

  // 8. GitHub Actions CI (render latest workflow run from gh CLI)
  const ciPage = await context.newPage();
  const { execSync } = await import("node:child_process");
  let ciRuns = [];
  try {
    const raw = execSync(
      'gh run list --workflow=ci.yml --limit 5 --json databaseId,status,conclusion,displayTitle,createdAt,url',
      { cwd: path.join(__dirname, ".."), encoding: "utf8" },
    );
    ciRuns = JSON.parse(raw);
  } catch {
    ciRuns = [];
  }

  const ciHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GitHub Actions — CI</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 40px auto; padding: 0 24px; background: #0d1117; color: #e6edf3; }
    h1 { font-size: 28px; }
    .run { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 16px 20px; margin: 12px 0; display: flex; justify-content: space-between; gap: 16px; align-items: center; }
    .success { color: #3fb950; font-weight: 700; }
    .pending { color: #d29922; font-weight: 700; }
    .failed { color: #f85149; font-weight: 700; }
    .meta { color: #8b949e; font-size: 14px; }
    .badge { border-radius: 999px; padding: 4px 10px; font-size: 12px; font-weight: 700; background: #238636; color: white; }
  </style>
</head>
<body>
  <h1>OfficeHours AI / CI</h1>
  <p class="meta">Automated verification for backend tests and frontend builds.</p>
  ${ciRuns
    .map((run) => {
      const statusClass =
        run.conclusion === "success"
          ? "success"
          : run.conclusion === "failure"
            ? "failed"
            : "pending";
      const label = run.conclusion || run.status;
      return `<div class="run">
        <div>
          <div>${run.displayTitle}</div>
          <div class="meta">${new Date(run.createdAt).toLocaleString()}</div>
        </div>
        <span class="${statusClass}">${label}</span>
      </div>`;
    })
    .join("")}
  <p class="meta">Jobs: Backend tests · Student kiosk build and audit · Professor dashboard build and audit</p>
</body>
</html>`;

  await ciPage.setContent(ciHtml, { waitUntil: "domcontentloaded" });
  await capture(ciPage, "08-github-actions-ci");

  await browser.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
