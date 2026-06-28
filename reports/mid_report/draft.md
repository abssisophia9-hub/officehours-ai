# OfficeHours AI — Mid-Report Draft

## 1. Project overview

**OfficeHours AI** is an AI-assisted triage system for finals-week academic
support. The project addresses two connected problems:

- Professors receive many repeated or overlapping questions during peak exam
  periods.
- Students may hesitate to ask for help because they feel anxious, embarrassed,
  or unsure how to phrase their confusion.

The prototype provides a student kiosk for submitting requests and a professor
dashboard for reviewing clustered questions and AI-assisted recommendations.
The professor remains in control of final decisions.

## 2. Research question

Can an AI-assisted office-hours triage system reduce faculty communication
overload and improve student comfort in seeking academic help during final exam
periods?

## 3. System architecture

The current system has four major parts:

1. **Student kiosk** (`frontend/student-kiosk/`)
   - Barcode/manual check-in screen
   - Anonymous or identified request submission
   - Confirmation screen after backend submission

2. **Professor dashboard** (`frontend/professor-dashboard/`)
   - Live request queue
   - Category and cluster visualizations
   - Office-hours setup panel
   - Interactive recommendation cards

3. **Backend API** (`backend/`)
   - FastAPI app
   - SQLAlchemy SQLite database for local development
   - Request CRUD routes
   - Classification and clustering services

4. **AI/NLP layer** (`backend/app/ai/`)
   - Rule-based MVP classifier for categories and urgency
   - Sentence-transformer clustering by default
   - Lexical clustering backend for deterministic tests

## 4. Implementation progress

### Backend

Completed:

- FastAPI app with `/`, `/health`, and `/requests/` routes.
- SQLite local development database.
- SQLAlchemy request model with:
  - `id`
  - `text`
  - `anonymous`
  - `student_id`
  - `category`
  - `cluster_id`
  - `recommended_action`
  - `created_at`
- Automatic request classification and recommendation during request creation.
- Automatic cluster assignment during request creation.
- Backend tests and GitHub Actions CI.

### Student kiosk

Completed:

- Vite + React + Tailwind kiosk app.
- Barcode/manual check-in prototype.
- Anonymous vs. identified submission.
- Free-text request form.
- API integration with `POST /requests/`.
- Confirmation screen.

### Professor dashboard

Completed:

- Vite + React + Tailwind + Recharts dashboard app.
- API integration with `GET /requests/`.
- Summary cards.
- Category and cluster charts.
- Triage table.
- Office-hours setup panel.
- Interactive recommendation cards with local approve/edit/dismiss states.

### Data and evaluation assets

Completed:

- Synthetic finals-week request dataset.
- Labeled request dataset for classification evaluation.
- Demo scenarios for clustering and recommendation behavior.
- Evaluation plan.

In progress / companion work:

- Student and professor survey templates are prepared in a separate PR and
  should be merged before final evaluation.

## 5. AI/NLP progress

The current classifier is a rule-based MVP baseline. This was chosen because it
is transparent, fast, and testable with a small synthetic dataset.

Current categories include:

- `conceptual_question`
- `exam_logistics`
- `retake_request`
- `accessibility_accommodation`
- `grading_dispute`
- `emotional_stress`
- `project_submission`
- `office_hours_access`
- `academic_integrity`
- `uncategorized`

The classifier has been tuned against the synthetic labeled dataset and matches
the current labels in tests.

Clustering uses sentence-transformer embeddings and cosine similarity by
default. New requests are compared against existing requests; if similarity is
high enough, the request reuses an existing `cluster_id`, otherwise it starts a
new cluster.

## 6. Ethics and privacy

The design follows three main privacy principles:

1. **Anonymity by default**
   - Students can submit requests without attaching a student ID.

2. **Opt-in identification**
   - Student ID is stored only when the student chooses identified submission.

3. **Human-in-the-loop decision-making**
   - AI recommends actions, but the professor approves or edits final actions.

Important risks:

- Misclassification of urgent or sensitive requests.
- Student discomfort if identity handling is unclear.
- Over-trust in AI recommendations.

Current mitigations:

- Recommendation cards keep professor approval in the workflow.
- The kiosk clearly separates anonymous and identified submission.
- Synthetic data is used during development instead of real student records.

## 7. Evaluation plan

The evaluation has three parts:

1. **Technical evaluation**
   - Backend test pass rate
   - Classifier accuracy on labeled synthetic data
   - Clustering behavior through demo scenarios
   - Build/audit success for both frontend apps

2. **User evaluation**
   - Student post-demo survey about comfort, anonymity, and usability
   - Professor post-demo survey about dashboard clarity and workload reduction

3. **Demo evaluation**
   - Run a finals-week scenario with mixed anonymous/identified requests
   - Show clustering and recommendation cards in the professor dashboard
   - Compare many individual requests to fewer grouped response actions

## 8. Current verification status

The project currently has GitHub Actions CI for:

- Backend tests
- Student kiosk audit/build
- Professor dashboard audit/build

Recent local and CI checks have passed after each major feature PR.

## 9. Remaining work

Near-term:

- Merge the evaluation survey forms PR.
- Persist professor office-hour windows in the backend.
- Persist recommendation card actions such as approve/edit/dismiss.
- Add a demo seeding script for synthetic requests.
- Improve clustering evaluation with metrics and examples.

Optional later work:

- Upgrade classification from rule-based baseline to an ML classifier once more
  labeled examples exist.
- Add real barcode scanner testing.
- Add NFC/tap-card mapping if the hardware returns card UIDs instead of printed
  student IDs.
- Add authentication before using real student data.

## 10. Conclusion

The prototype now demonstrates the core OfficeHours AI workflow: students submit
requests through a kiosk, the backend classifies and clusters them, and the
professor dashboard presents grouped recommendations. The system is still an MVP,
but it is functional enough for a simulated finals-week demo and for collecting
initial feedback from students and professors.
