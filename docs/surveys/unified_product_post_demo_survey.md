# OfficeHours AI — Google Forms survey pack (copy/paste)

Use this after a short demo of the **unified product** (`./scripts/run_product.sh` →
http://127.0.0.1:5180). Create **three** Google Forms (Student / TA / Professor),
then email the links via **`survey@aui.ma`**.

**Scale for all Likert items:**  
1 = Strongly disagree · 2 = Disagree · 3 = Neutral · 4 = Agree · 5 = Strongly agree

**Rules**
- Students: keep responses **anonymous** (do not require name/email on the student form).
- Do not ask for real grades, medical details, or private student records.
- Send forms **after** the demo, not during a live advising session.
- Export CSVs later into `data/survey_responses/` for the final report.

---

## Form A — Students

**Form title:** OfficeHours AI — Student post-demo survey  
**Description (paste into Google Forms):**  
You just saw a short demo of OfficeHours AI (campus office-hours help app).  
Please rate each statement from 1 (strongly disagree) to 5 (strongly agree).  
Responses are anonymous.

### Required Likert (multiple choice 1–5)

1. It was easy to submit a Quiet ask or Identify me from the product app.
2. I understood the difference between anonymous and identified asks.
3. I felt comfortable submitting a question anonymously.
4. The Ask Triage feedback after submit (category / assigned TA / hint) was clear.
5. Checking status with my request code felt private enough.
6. I would be more likely to seek help during finals with this tool.
7. If shown: the Study Agent’s “I don’t know — ask a human” behavior felt honest.

### Optional multiple choice

8. Preferred ask mode in a real finals week:  
   `Anonymous (Quiet ask)` · `Identified` · `It depends on the question`

### Free text (paragraph)

9. What would you change or improve?
10. Any privacy or trust concerns?

---

## Form B — Teaching Assistants (TAs)

**Form title:** OfficeHours AI — TA post-demo survey  
**Description:**  
You saw / used the TA workspace (queue, Help Coach, reply / meetings).  
Rate 1–5. Optional: add your role/course at the end (not required).

### Required Likert (1–5)

1. The queue made it clear who needed help and how (message / meeting).
2. Claim → start helping → done / reply felt workable.
3. Help Coach drafts / Socratic steps were useful.  
   *(Add “N/A” as an option if they did not use Help Coach.)*
4. A shared group meeting for a repeated cluster made sense.
5. Switching to a student course with the same login was clear.
6. This would reduce repeated 1:1 typing for common questions.

### Free text

7. Biggest risk if this shipped campus-wide?
8. What would you change in the TA workspace?

---

## Form C — Professors / instructors

**Form title:** OfficeHours AI — Professor post-demo survey  
**Description:**  
You saw the professor workspace (clusters, KB gate, Canvas materials, meetings).  
Rate 1–5.

### Required Likert (1–5)

1. Clusters and recommendation cards reduced repeated 1:1 handling in the demo.
2. I remained in control of what enters the student Study Agent knowledge base.
3. Canvas materials sync (or local mirror) was understandable for demos.
4. Shared group meetings for repeated concepts look useful.
5. Perceived workload reduction vs answering each ask separately.
6. I would trust this for a real course **after** Canvas LTI / campus hardening.

### Free text

7. What must be true before you trust this with a real course?
8. Any ethics, privacy, or academic-integrity concerns?

---

## Email to send from `survey@aui.ma`

**Subject:** OfficeHours AI demo — short feedback survey (2–3 min)

**Body (edit names/links):**

```text
Hello,

Thank you for attending / watching the OfficeHours AI demo.

Please complete the short form that matches your role (2–3 minutes):

• Students:   <PASTE STUDENT FORM LINK>
• TAs:        <PASTE TA FORM LINK>
• Professors: <PASTE PROFESSOR FORM LINK>

This is for an AUI final-year project evaluation. Student responses are anonymous.
Do not include real grades or personal medical details.

Thank you,
OfficeHours AI project team
```

---

## After responses arrive

1. Google Forms → Responses → Download CSV.  
2. Save under `data/survey_responses/` (e.g. `unified_student_responses.csv`).  
3. Compute Likert averages (1–5) per question.  
4. Add a **“unified-app survey (n=…)”** subsection in `reports/final_report/main.tex`  
   (keep the older kiosk pilot labeled as legacy).

Target (nice to have): ≥8 students, ≥3 TAs, ≥3 professors — report whatever n you get honestly.
