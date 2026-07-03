# Mid-Report Screenshots

Captured with `demo/capture_screenshots.mjs` after seeding demo data.

| File | LaTeX caption |
| --- | --- |
| `01-student-kiosk-checkin.png` | Scanner-compatible student check-in flow. |
| `02-student-request-form.png` | Privacy-preserving request submission. |
| `03-submission-confirmation.png` | Student receives confirmation after backend submission. |
| `04-professor-dashboard-overview.png` | Professor sees categorized and clustered request queue. |
| `05-recommendation-cards.png` | AI-assisted recommendations group repeated requests into actions. |
| `06-action-orchestration-plan.png` | Professor decision triggers a next-step action plan. |
| `07-survey-templates.png` | Evaluation instruments for student and professor feedback. |
| `08-github-actions-ci.png` | Automated verification for backend and frontend builds. |

## Regenerate

```bash
cd backend
python3 scripts/seed_demo_data.py --reset --limit 20
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000

# separate terminals
cd frontend/student-kiosk && npm run dev -- --host 127.0.0.1 --port 5173
cd frontend/professor-dashboard && npm run dev -- --host 127.0.0.1 --port 5174

cd demo
npm install
npx playwright install chromium
node capture_screenshots.mjs
```
