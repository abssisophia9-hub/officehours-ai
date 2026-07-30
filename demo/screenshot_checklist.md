# Mid-Report Screenshot Checklist

Use these screenshots in the LaTeX mid-report analysis section.

## Setup

```bash
cd backend
python3 scripts/seed_demo_data.py --reset --limit 20
python3 -m uvicorn app.main:app --reload
```

In separate terminals:

```bash
cd frontend/student-kiosk
npm run dev
```

```bash
cd frontend/professor-dashboard
npm run dev
```

## Capture list

1. **Student kiosk check-in**
   - Show optional typed student ID input (or anonymous skip).
   - Caption: "Optional student ID check-in (software-only)."

2. **Student request form**
   - Show anonymous vs. identified toggle.
   - Caption: "Privacy-preserving request submission."

3. **Submission confirmation**
   - Show generated request number.
   - Caption: "Student receives confirmation after backend submission."

4. **Professor dashboard overview**
   - Show summary cards and charts.
   - Caption: "Professor sees categorized and clustered request queue."

5. **Recommendation cards**
   - Show group session / FAQ / 1:1 cards.
   - Caption: "AI-assisted recommendations group repeated requests into actions."

6. **Action orchestration plan**
   - Click Approve on a recommendation card.
   - Capture generated agenda/status plan.
   - Caption: "Professor decision triggers a next-step action plan."

7. **Survey templates**
   - Show `docs/surveys/` files or Google Form version.
   - Caption: "Evaluation instruments for student and professor feedback."

8. **GitHub Actions**
   - Show green CI checks.
   - Caption: "Automated verification for backend and frontend builds."

## Automated capture

After the servers above are running:

```bash
cd demo
npm install
npx playwright install chromium
node capture_screenshots.mjs
```

Outputs land in `demo/screenshots/` with LaTeX-ready filenames. See `demo/screenshots/README.md` for captions.
