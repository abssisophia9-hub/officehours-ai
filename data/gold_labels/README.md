# Human gold labels

Staff (TA / professor) judgments used to evaluate Analyzer + Matcher quality
**beyond silver/heuristic training labels**.

## File

`gold_labels.csv`

| Column | Meaning |
| --- | --- |
| `label_id` | Stable ID |
| `text` | Student question text |
| `gold_category` | Human category label |
| `gold_assigned_ta` | Human choice of best TA (roster name) |
| `gold_hint_useful` | `1` useful / `0` not (for synthesizer preference) |
| `department` | e.g. `MTH`, `COM`, `CSC`, `ECO`, `ENG`, `GEN` |
| `course_code` | Optional AUI code |
| `labeled_by` | Who labeled (email or role tag) |
| `label_source` | `human_gold_seed` or `human_gold` |
| `notes` | Free text |

## How to grow this set

1. Export confusing asks from a live demo / pilot.
2. Have a TA fill `gold_category` + `gold_assigned_ta` (even 40 rows helps).
3. Run:

```bash
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
  venv/bin/python scripts/evaluate_gold_labels.py
```

Metrics land in `reports/final_report/gold_label_evaluation.json`.

You can also POST labels into the running API (`POST /analytics/gold-labels`) —
they are stored in SQLite and included when the evaluate script uses `--include-db`.

Seed rows are **illustrative** and may overlap synthetic training text, so
perfect scores on the seed set are **not** proof of generalization. Replace with
real held-out TA judgments before claiming production quality.

## Lab-session checklist (collect ≥40 gold rows)

Use one 45–60 minute TA lab. Goal: held-out judgments, not more synthetic CSVs.

1. **Prep (5 min)** — Export 40–60 confusing / mixed asks from a seeded demo or
   pilot (`GET /requests/` or CSV dump). Prefer text that is **not** copied from
   `labeled_requests*.csv`.
2. **Brief TAs (5 min)** — Show category list + TA roster names. One primary TA
   per ask; optional `gold_hint_useful` after they see the synthesizer hint.
3. **Label (30–40 min)** — Fill `gold_category`, `gold_assigned_ta`,
   `labeled_by`, set `label_source=human_gold`, add `department` / `course_code`.
4. **Merge** — Append to `gold_labels.csv` (or `POST /analytics/gold-labels`).
5. **Evaluate** — Run `evaluate_gold_labels.py`; expect imperfect scores.
   Sample errors for the final report (do not chase 100%).
6. **Cite** — Update `reports/final_report/main.tex` with the new `n`, accuracy,
   and 3–5 error examples. See `docs/fyp_evidence.md`.

FYP bar: **≥40 real `human_gold` rows** beats another round of synthetic labels.
