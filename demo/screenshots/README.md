# Screenshots

## Unified product (`product-*.png`) — use these

Captured with `demo/capture_product_screenshots.mjs` against `:5180`.

| File | Caption |
| --- | --- |
| `product-01-login.png` | Unified product login |
| `product-02-student-ask.png` | Student Quiet ask form (CSC 2302) |
| `product-03-ask-triage-result.png` | Ask Triage Analyzer / Matcher / hint |
| `product-04-ta-help-coach.png` | TA workspace / Help Coach |
| `product-05-professor-kb.png` | Professor command center |
| `product-06-canvas-simulator.png` | Unsigned Canvas launch simulator |

```bash
# backend :8000 + officehours-app :5180 running
cd demo && npm ci && npx playwright install chromium
node capture_product_screenshots.mjs
```

## Mid-report legacy set (historical)

> Older kiosk `:5173` + professor dashboard `:5174` captures for mid-report LaTeX.

| File | LaTeX caption |
| --- | --- |
| `01-student-kiosk-checkin.png` | Optional student ID check-in (software-only). |
| `02-student-request-form.png` | Privacy-preserving request submission. |
| `03-submission-confirmation.png` | Student receives confirmation after backend submission. |
| `04-professor-dashboard-overview.png` | Professor sees categorized and clustered request queue. |
| `05-recommendation-cards.png` | AI-assisted recommendations group repeated requests into actions. |
| `06-action-orchestration-plan.png` | Professor decision triggers a next-step action plan. |
| `07-survey-templates.png` | Evaluation instruments for student and professor feedback. |
| `08-github-actions-ci.png` | Automated verification for backend and frontend builds. |

```bash
cd backend && python3 scripts/seed_demo_data.py --reset --limit 20
# start legacy frontends 5173/5174 + backend, then:
cd demo && node capture_screenshots.mjs
```
