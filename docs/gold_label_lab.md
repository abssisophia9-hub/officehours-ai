# Gold labels — what to do (due, not optional)

**Short answer:** do **not** send TAs a satisfaction survey to build a gold set.
Send them a **labeling task** (or sit with them for 45 minutes in the TA desk).
Papers and public office-hours FAQs only justify the *schema* and the seed
themes. They are not a substitute for staff judgment on real asks.

Gold labels evaluate Analyzer + Matcher. They do **not** retrain `.joblib` and
they never publish to the Study Agent.

## Survey vs research vs gold lab

| Method | Use it for | Do not use it for |
| --- | --- | --- |
| **Likert survey** (“the queue was clear”) | Optional UX after a demo (`docs/surveys/`) | Gold labels. A 1–5 score is not a category. |
| **Literature / public OH FAQs** | Category list, themes, seed `curated_heldout_public` rows | Claiming campus quality |
| **TA gold lab** (required for a quality number) | `gold_category` + `gold_hint_useful` + who should take the ask | Product satisfaction |

You already have the in-app control: TA desk → select an ask → **Gold label this ask**.

## The lab (one section, 45–60 minutes)

**Who:** 1–2 TAs who actually staff that course (they already took it).
**How many:** **≥40 asks**. Ten real labels beat another synthetic CSV.
**Where:** live TA desk on `:5180`, or a printed sheet then `POST /analytics/gold-labels`.

1. **Prep (5 min)** — Pick 40–60 asks from *this* course that are **not** copied
   from `data/labeled_requests*.csv`. Mix conceptual, logistics, and one sensitive
   case. Export from the professor queue or write them from a real recitation.
2. **Brief (5 min)** — Show the category list (same dropdown as the TA desk).
   One primary TA per ask. After they read the Synthesizer hint: useful or not.
3. **Label (30–40 min)** — For each ask, set:
   - `gold_category` (the truth, even if Ask Triage was wrong)
   - `gold_assigned_ta` (who should have taken it on *this* roster)
   - `gold_hint_useful` (`1` / `0`)
   - `labeled_by` = their AUI email
   - `label_source` = `human_gold`
   - `course_code` / `department`
4. **Save** — In-app **Save gold label**, or append `data/gold_labels/gold_labels.csv`.
5. **Evaluate** (does not retrain):

```bash
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
  venv/bin/python scripts/evaluate_gold_labels.py --include-db
```

6. **Cite** — New `n`, accuracy, and 3–5 errors in the report. Expect imperfect
   scores. Do not chase 100%.

## Ethics

- Prefer Quiet-ask text already in the course, or asks the TA invented for the lab.
- Do not scrape private student email or Canvas inbox threads.
- Do not put student names in the CSV.
- Alice’s 20-row `ta_alice_pass.csv` is a **demo pass**. Replace it in the report
  once the lab exists.

## Why not a Google Form survey?

A survey asks “was this useful?” Gold asks “what *is* this ask?” Those are
different instruments. If you also want UX numbers, run the optional Form B in
`docs/surveys/unified_product_post_demo_survey.md` **after** the demo — keep
that file separate from `gold_labels.csv`.
