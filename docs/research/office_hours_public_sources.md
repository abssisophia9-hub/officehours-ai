# Public university research — office hours & help-seeking

**Purpose:** ground Ask Triage evaluation asks and FYP narrative in *public*
university guidance on office hours / help-seeking (not private LMS data).

**What we did *not* scrape:** authenticated Canvas/AUI portals, private student
emails, real advising transcripts, or paid/closed student records.

**Method:** fetch publicly linked `.edu` / university learning-center pages
(2026 agent run), extract recurring student *concern themes*, then author
**original** AUI-framed evaluation questions (`curated_heldout_public`).

## Sources fetched

| University | Page | Themes used |
| --- | --- | --- |
| McGill | [Office hours 101](https://www.mcgill.ca/student-learning-resources/build-academic-connections/office-hours) | Peak load near exams; prepare specific questions; virtual OH; syllabus listing |
| University of Iowa | [Attend office hours](https://clas.uiowa.edu/news/2026/02/want-do-well-your-courses-attend-office-hours) | Myths (judgment, “only if struggling”); exam prep; accommodations; athlete/religious conflicts |
| UNC Learning Center | [Using office hours effectively](https://learningcenter.unc.edu/tips-and-tools/using-office-hours-effectively/) | Concept clarify; practice problems; grade review; syllabus/due dates; Zoom OH |
| Oregon State ASC | [Experience office hours](https://success.oregonstate.edu/learning-corner/studying/office-hours) | Clarification; exam priorities; intimidation barrier; go with classmates / group |
| Stanford Teaching Commons | [OH & review sessions for TAs](https://teachingcommons.stanford.edu/news/strategies-office-hours-and-review-sessions-tas) | Inclusive OH; online option; anonymous question polls; group review before assessment |
| Toronto TATP (index) | [Exam preparation](https://tatp.utoronto.ca/resources/exam-preparation/) | Finals email flood; regrade asks; review sessions; “will I be all right?” anxiety |

## Theme → product mapping

| Public theme | OfficeHours AI surface | Gold category (typical) |
| --- | --- | --- |
| Clarify a lecture concept / practice problem | Student Quiet ask → Ask Triage | `conceptual_question` |
| What’s on the exam / how to prepare | Ask Triage + professor cards | `exam_logistics` |
| Assignment deadlines / Canvas vs syllabus | Ask Triage | `project_submission` / `exam_logistics` |
| Grade confusion / regrade | TA staffing | `grading_dispute` |
| Accommodations letter | Escalation / Sam Ortiz tags | `accessibility_accommodation` |
| Fear of looking “dumb” / anonymous ask | Quiet ask | `emotional_stress` / privacy |
| Can’t make posted OH → Zoom / appointment | Help mode online / F2F | `office_hours_access` |
| Many students stuck on same topic → review | Shared group meeting | `exam_logistics` / cluster |
| Integrity / collaboration rules | Escalation | `academic_integrity` |
| Midterm failure / make-up | Escalation | `retake_request` |

## Evaluation artifact

- Labels: `data/gold_labels/gold_labels.csv` (`label_source=curated_heldout_public`)
- Metrics: `reports/final_report/gold_label_evaluation.json`
- Honesty: these are **curated** from public themes, **not** independent campus
  TA judgments. Prefer future `human_gold` rows from a real TA lab.

## Survey note

Public pages do **not** replace human post-demo surveys. Likert evidence still
needs participants on `:5180` (`docs/surveys/unified_product_post_demo_survey.md`).
Do not invent survey responses from scraped text.
