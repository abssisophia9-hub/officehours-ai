# Evaluation Plan

> Demo path today: unified product app (`./scripts/run_product.sh`, port **5180**).
> Defense evidence package: [`fyp_evidence.md`](fyp_evidence.md).
> Survey templates under `docs/surveys/` include a unified-app draft; older
> kiosk/dashboard instruments are legacy pilots.

## Research Question
Can an AI-assisted office-hours triage system reduce faculty communication overload and improve student comfort in seeking academic help during final exam periods?

## Evaluation Methods

### 1. Technical Evaluation
- Analyzer CV on labeled CSVs → `reports/final_report/classifier_evaluation.json`
- Matcher silver holdout → `reports/final_report/matcher_evaluation.json`
- Human gold (grow beyond seed) → `scripts/evaluate_gold_labels.py`
- Ask Triage latency smoke → `scripts/measure_ask_triage_latency.py` →
  `reports/final_report/ask_triage_latency.json`
- Clustering quality (silhouette / manual gallery) — backlog
- Study Agent KB hit-rate — `GET /analytics/kb-hit-rate` after Canvas sync demos

### 2. User Evaluation
- Simulated finals-week demo (`demo/demo_script.md`) on **`:5180`**
- Legacy pilot surveys (`docs/surveys/`) — kiosk/dashboard era; label as such
- Recommended: refresh surveys for Ask Triage, Help Coach, dual roles, group meetings
  (`docs/surveys/unified_product_post_demo_survey.md`)
- Public university OH research supports **gold-label themes**, not Likert scores
  (`docs/research/office_hours_public_sources.md`)

### 3. Metrics
| Metric | Target | Status |
|---|---|---|
| Analyzer CV accuracy | ≥ 80% on labeled set | ~84.6% (synthetic union) |
| Matcher silver holdout | report with caveats | ~87.5% (not gold) |
| Human gold agreement | grow n ≥ 40 held-out | seed n=12 illustrative only |
| Student comfort survey | Likert ≥ 4.0 | legacy pilot met target |
| Faculty workload survey | Likert ≥ 4.0 | legacy pilot met target |
| Ask Triage latency | report p50/p95 | measure script |
| Faculty time-to-triage vs baseline | qualitative / future study | not instrumented |

## Reporting
Primary graded narrative: `reports/final_report/main.tex`.  
Honesty ceilings: `docs/fyp_evidence.md`, `docs/agent_performance.md`.

Survey deployment: `docs/surveys/README.md`.
