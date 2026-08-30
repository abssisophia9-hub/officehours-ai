# FYP evidence & limitations — OfficeHours AI

What to claim in a defense, what not to claim, and where the numbers live.
Companion to [`product_overview.md`](product_overview.md),
[`agent_performance.md`](agent_performance.md), and
[`reports/final_report/main.tex`](../reports/final_report/main.tex).

## Research question

Can an AI-assisted office-hours triage system **reduce faculty communication
overload** and **improve student comfort** seeking academic help during finals?

## What the prototype demonstrates (safe claims)

| Claim | Evidence |
| --- | --- |
| One multi-role campus app (one role per course; TA ≠ student of that course) | `frontend/officehours-app`, login + course picker |
| Ask Triage at intake (Analyzer → Matcher → Synthesizer) with **local** models | `oracle_service.py`, `backend/models/*.joblib`, `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` |
| Professor remains the Study Agent publication gate | KB `pending_review` → approve → `/agent/ask` |
| TA staffing + Help Coach mid-session | `/ta/claim/`, `/ta/assist/` |
| Privacy-preserving Quiet ask + request-code status | student workspace, `GET /requests/{id}/status` |
| **Rooms** classmate forum + Hilbert ranks | `/student/room` + `/help-room/`; named helpers; Canvas-module chapters; students only |
| Professor chapter/topic review insights | `GET /analytics/review-insights` (asks + Rooms posts) |
| Canvas is the intended community enrollment **and** chapter source | Signed **LTI 1.3** (`/lti/login`, `/lti/launch`) when IT installs the key; `/canvas-demo` only if `OFFICEHOURS_DEMO=true`; live modules when `CANVAS_*` credentials are set |
| Automated regression | ~133 backend pytest cases + CI builds |

## Metric honesty (read before citing)

| Artifact | What it is | What it is **not** |
| --- | --- | --- |
| `classifier_evaluation.json` (~84.6% CV, n=156) | Stratified CV on **synthetic / curated** labels | Proof on real AUI student text |
| `matcher_evaluation.json` (~87.5% holdout) | Silver expertise-overlap labels | Gold TA judgment |
| `gold_label_evaluation.json` (n=80) | Seed + curated held-out from public OH research; Analyzer ~75%, Matcher ~79% | Independent campus TA judgments (`human_gold`) |
| Survey summary (n=8 students / n=4 professors) | **Legacy** kiosk + dashboard pilot (already collected) | Not a required new round for the capstone presentation |
| KB hit-rate endpoint | Runtime Study Agent ceiling | Not yet a published longitudinal table |

## Gaps supervisors will ask about

1. **Gold labels** — n=80 curated held-out set from public uni OH research
   (`docs/research/office_hours_public_sources.md`); still collect real TA
   `human_gold` when possible.
2. **Surveys** — a legacy pilot already exists. **No new survey collection** is
   required before the capstone presentation, and surveys are not a post-product
   submission. Optional templates remain in `docs/surveys/`.
3. **Canvas LTI 1.3** — code is in; campus needs a developer key + API token. Unsigned `/canvas-demo` is demo-only.
4. **Host leftovers** — CORS is origin-locked; `/ws` requires token +
   `course_id`; TA queue requires staff `course_id` (no `course=` bypass).
   Favicon still optional. Older backlog notes in [`repo_audit.md`](repo_audit.md).
5. **Screenshots** — unified-app pack lives in `demo/screenshots/product-*.png`.

## Defense checklist (day-of)

- [ ] `./scripts/run_product.sh` → login Sara / Alice / Benali (`aui-demo`)
- [ ] Show Quiet ask → Ask Triage breakdown → status code
- [ ] Alice: claim → Help Coach → reply **or** group meeting
- [ ] Benali: approve KB → Study Agent only answers approved material
- [ ] Student Rooms: named post, Canvas/demo chapter pick, leaderboard shows names
- [ ] `/canvas-demo`: say clearly **unsigned simulator**, only when `OFFICEHOURS_DEMO=true`; LTI is the production path
- [ ] Cite CV/silver metrics with caveats; do **not** cite seed gold 100% as quality
- [ ] Point to this page + `agent_performance.md` for ceilings

## Recommended next evidence (priority)

1. Keep `reports/final_report/main.tex` synced with the shipped product.
2. Optional: real TA `human_gold` labels when a lab is available.
3. Production: Canvas LTI 1.3 (installed by IT). Unsigned simulator is demo-only.

New user surveys are **not** on this list for the capstone.
