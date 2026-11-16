# Sources and provenance — Deliverable 1

Built **without** `PROJECT_FACTS.md` (missing from store/repo/uploads at compile time).

## Authority tip

| Ref | SHA / id |
| --- | --- |
| `origin/main` | `db8de9bafb5693af4b66143cf4d5459958232184` (PR #147 merge) |
| Freeze tag `final-nov-16` | `6264d952c8355968a63d5c50ad2c08124870ad15` |
| PR #147 | https://github.com/abssisophia9-hub/officehours-ai/pull/147 |

## Primary inputs

1. Capstone Word template: `Capstone_Final_report_SOFTWAREDEVELOPMENT (1).docx` (AUI SSE structure + logo)
2. Capstone proposal: `docs/CSC_Capstone_Project_Proposal_Sophia_A_FINAL.docx`
3. `reports/final_report/main.tex` + eval JSON/MD
4. `docs/midreport/INFO_PACK.md`, `EVIDENCE.md`, figures
5. Project evidence pack: `docs/evidence/` (Parts 1–7, freeze evidence numbers)
6. Tip product docs: `docs/product_overview.md`, `system_architecture.md`, `fyp_evidence.md`, `glossary.md`, `ethics_privacy.md`
7. Code: `ask_triage_service.py`, `help_coach_service.py`, models `*.joblib`

## Locked product claims

- **Ask Triage:** local MiniLM + LogReg Analyzer/Matcher + retrieval Synthesizer
- **Help Coach:** retrieval + templates + optional learning-style LogReg — **not** an LLM
- **Study Agent:** professor-approved KB only; refuse below similarity 0.42; optional Gemini check
- **Tests:** 345 collected / PR #147 reports 345 passed (lexical)
- **Canvas demo:** unsigned simulator; production = LTI 1.3
- **Survey:** legacy kiosk/dashboard pilot only

## MEASURED headline numbers (do not inflate)

| Claim | Value | Artifact |
| --- | --- | --- |
| Analyzer CV | 0.8462 acc / 0.8455 macro F1 (n=156) | classifier_evaluation.json |
| Matcher silver | 0.875 (28/32) | matcher_evaluation.json |
| Gold Analyzer/Matcher | 0.75 / 0.7875 (n=80) | gold_label_evaluation.json |
| Learning-style CV | 0.925 mean (n=40) | learning_style_evaluation.json |
| Study retrieval / +check | 50/75 ; 74/75 | midreport EVIDENCE / eval_results |
| Ask Triage p50 | ≈30 ms (Part4); 62.57 ms smoke | evidence Part4; ask_triage_latency.json |
| Load conc 40 | 0 errors | evidence Part7 |
| Survey student/professor | ≥4.0 on core Likert (legacy UI) | survey_evaluation_summary.md |
