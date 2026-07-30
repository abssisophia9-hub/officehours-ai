# Unified product post-demo survey (draft)

Use this after a demo on **`http://127.0.0.1:5180`** (`./scripts/run_product.sh`).
Likert items: 1 = strongly disagree … 5 = strongly agree.

> Replaces the mid-report kiosk/dashboard instruments for new eval rounds.
> Legacy pilot results remain in `reports/final_report/survey_evaluation_summary.md`.

## Student form

1. It was easy to submit a Quiet ask or Identify me from the product app.
2. I understood the difference between anonymous and identified asks.
3. I felt comfortable submitting a question anonymously.
4. The Ask Triage feedback after submit (category / TA / hint) was clear.
5. Checking status with my request code felt private enough.
6. I would be more likely to seek help during finals with this tool.
7. (If shown) The Study Agent’s “I don’t know — ask a human” behavior felt honest.
8. Free text: what would you change?

## TA form

1. The queue made it clear who needed help and how (message / meeting).
2. Claim → start helping → done / reply felt workable.
3. Help Coach drafts / Socratic steps were useful (or N/A if not used).
4. Shared group meeting for a repeated cluster made sense.
5. Switching to a student course with the same login was clear.
6. Free text: biggest risk if this shipped campus-wide?

## Professor form

1. Clusters and recommendation cards reduced repeated 1:1 handling in the demo.
2. I remained in control of what enters the student Study Agent KB.
3. Canvas materials sync (or mirror) was understandable for demos.
4. Shared group meetings for repeated concepts look useful.
5. Perceived workload reduction vs answering each ask separately.
6. Free text: what must be true before you trust this with a real course?

## Deploy notes

Same as `docs/surveys/README.md`: anonymous student responses, no real grades /
medical data, export CSV under `data/survey_responses/`, summarize with
`backend/scripts/analyze_survey_responses.py` (extend the analyzer if new
column names are used).
