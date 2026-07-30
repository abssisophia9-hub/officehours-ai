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
| One multi-role campus app (role per course) | `frontend/officehours-app`, login + course picker |
| Ask Triage at intake (Analyzer → Matcher → Synthesizer) with **local** models | `oracle_service.py`, `backend/models/*.joblib`, `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` |
| Professor remains the Study Agent publication gate | KB `pending_review` → approve → `/agent/ask` |
| TA staffing + Help Coach mid-session | `/ta/claim/`, `/ta/assist/` |
| Privacy-preserving Quiet ask + request-code status | student workspace, `GET /requests/{id}/status` |
| Canvas is the intended community enrollment path | `/canvas/launch` **simulator** (unsigned demo) |
| Automated regression | ~118 backend pytest cases + CI builds |

## Metric honesty (read before citing)

| Artifact | What it is | What it is **not** |
| --- | --- | --- |
| `classifier_evaluation.json` (~84.6% CV, n=156) | Stratified CV on **synthetic / curated** labels | Proof on real AUI student text |
| `matcher_evaluation.json` (~87.5% holdout) | Silver expertise-overlap labels | Gold TA judgment |
| `gold_label_evaluation.json` (seed n=12, perfect scores) | **Illustrative** seed set | Held-out human gold — replace before claiming quality |
| Survey summary (n=8 students / n=4 professors) | **Legacy kiosk + professor-dashboard** pilot | Eval of Ask Triage / Help Coach / `:5180` product |
| KB hit-rate endpoint | Runtime Study Agent ceiling | Not yet a published longitudinal table |

## Gaps supervisors will ask about

1. **Gold labels** — collect ≥40 real TA judgments (`data/gold_labels/README.md`).
2. **Surveys** — re-run on unified app with Ask Triage / Help Coach questions
   (`docs/surveys/` templates are mid-report era).
3. **Canvas LTI 1.3** — production needs signed launches; today is unsigned JIT demo.
4. **Open demo APIs** — some list endpoints are convenient for local demos; not
   campus-hardened ACLs.
5. **Screenshots in final LaTeX** — mid-report kiosk PNGs still in appendix until
   a `:5180` capture pack is added.

## Defense checklist (day-of)

- [ ] `./scripts/run_product.sh` → login Sara / Alice / Benali (`aui-demo`)
- [ ] Show Quiet ask → Ask Triage breakdown → status code
- [ ] Alice: claim → Help Coach → reply **or** group meeting
- [ ] Benali: approve KB → Study Agent only answers approved material
- [ ] `/canvas-demo`: say clearly **unsigned simulator**, LTI next
- [ ] Cite CV/silver metrics with caveats; do **not** cite seed gold 100% as quality
- [ ] Point to this page + `agent_performance.md` for ceilings

## Recommended next evidence (priority)

1. Rewrite/keep `reports/final_report/main.tex` synced with this product (done in
   evidence-harden pass).
2. Real gold labels + re-run `evaluate_gold_labels.py`.
3. Unified-app screenshots + optional short demo video.
4. New survey round on `:5180`.
5. Publish one latency + KB hit-rate table after a Canvas sync demo.
