# Evaluation Survey Forms

> **Note:** these templates were written for mid-report demos that used the
> **legacy** student kiosk + professor dashboard. Prefer demos on the unified
> product app (`:5180`) today; keep or adapt questions for Ask Triage, Help Coach,
> dual roles, and group meetings when you run a new eval round.

This folder contains survey templates for evaluating the OfficeHours AI demo.

## Forms

- `student_post_demo_survey.md` — student comfort, anonymity, kiosk usability,
  and help-seeking intent.
- `professor_post_demo_survey.md` — professor workload, dashboard clarity,
  recommendation usefulness, and human-in-the-loop trust.

## How to deploy

1. Copy each template into Google Forms, Microsoft Forms, or a paper handout.
2. Keep student survey responses anonymous.
3. Do not collect real grades, medical details, or private student records.
4. Run the surveys after a simulated demo, not during a real advising session.
5. Export responses as CSV for qualitative notes and Likert-score summaries.
6. Store pilot/demo CSV exports under `data/survey_responses/`.
7. Summarize results with `backend/scripts/analyze_survey_responses.py`.

## Metrics supported

| Evaluation metric | Survey source |
|---|---|
| Student comfort using anonymous request flow | Student Q3, Q6, Q8 |
| Understanding of anonymous vs. identified submission | Student Q2, Q7 |
| Kiosk usability | Student Q1, Q4, Q5, Q9 |
| Faculty perceived workload reduction | Professor Q1, Q2, Q5 |
| Recommendation usefulness | Professor Q3, Q6, Q9 |
| Human-in-the-loop trust and risk | Professor Q4, Q7, Q8, Q10 |

## Suggested analysis

- Calculate average Likert score for each closed-ended question.
- Compare student comfort scores for anonymous vs. identified preference.
- Summarize free-response feedback into themes:
  - privacy/anonymity
  - UI clarity
  - recommendation trust
  - missing information
  - hardware/check-in concerns
