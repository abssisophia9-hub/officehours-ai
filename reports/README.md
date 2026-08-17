# Reports

- `mid_report/` — mid-semester progress report (historical kiosk + dashboard era)
  - `draft.md` — markdown draft
  - `main.tex` — LaTeX report with demo screenshots
  - `progress_checklist.md`
- `final_report/` — final project report (**keep synced with the unified product**)
  - `main.tex` — LaTeX final report (Ask Triage, Help Coach, Rooms, evidence caveats)
  - `classifier_evaluation.*` / `matcher_evaluation.json` / `gold_label_evaluation.json`
  - `ask_triage_latency.json` — from `backend/scripts/measure_ask_triage_latency.py`
  - `survey_evaluation_summary.md` / `.json` — **legacy** kiosk pilot summary
- `paper_draft/` — optional publication draft (empty until final report is solid)

Defense notes (not LaTeX): [`docs/fyp_evidence.md`](../docs/fyp_evidence.md).

## Build LaTeX locally

From the repository root (requires `pdflatex`):

```bash
cd reports/mid_report && pdflatex main.tex
cd ../final_report && pdflatex main.tex
```

Screenshot paths in the `.tex` files are relative to each report directory
(`../../demo/screenshots/`). Prefer live `:5180` demos; legacy PNGs are labeled
as such in the final report appendix.

## Regenerate evaluation artifacts

```bash
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_classifier.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_matcher.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/evaluate_gold_labels.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/measure_ask_triage_latency.py
python3 scripts/analyze_survey_responses.py
```

Pilot response CSVs live in `data/survey_responses/` (legacy UI).
