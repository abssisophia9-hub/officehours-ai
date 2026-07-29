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
