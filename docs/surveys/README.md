# Evaluation Survey Forms

## Use this for the current product (`:5180`)

**Primary pack (Google Forms + email):**  
[`unified_product_post_demo_survey.md`](unified_product_post_demo_survey.md)

That file has copy/paste questions for:

1. Student form  
2. TA form  
3. Professor form  

Plus an email draft for **`survey@aui.ma`**.

## Legacy mid-report forms (kiosk + professor dashboard)

- `student_post_demo_survey.md` — early kiosk pilot  
- `professor_post_demo_survey.md` — early dashboard pilot  

Keep those as historical; prefer the unified pack for new data collection.

## How to deploy (unified pack)

1. Create three Google Forms from `unified_product_post_demo_survey.md`.
2. Email the links from `survey@aui.ma` (template in that file).
3. Keep student responses anonymous.
4. Do not collect real grades, medical details, or private student records.
5. Run after a simulated / demo session, not a live advising session.
6. Export CSVs to `data/survey_responses/`.
7. Put averages + themes into `reports/final_report/main.tex`.

## Metrics supported (unified pack)

| Metric | Form |
| --- | --- |
| Student comfort / anonymity / Quiet ask | Student Q1–Q3, Q8 |
| Ask Triage clarity | Student Q4 |
| Status privacy | Student Q5 |
| Help-seeking intent | Student Q6 |
| Study Agent honesty | Student Q7 |
| TA queue / staffing loop | TA Q1–Q2 |
| Help Coach usefulness | TA Q3 |
| Group meetings | TA Q4, Professor Q4 |
| Dual-role clarity | TA Q5 |
| Professor KB control | Professor Q2 |
| Perceived workload reduction | Professor Q5, TA Q6 |
