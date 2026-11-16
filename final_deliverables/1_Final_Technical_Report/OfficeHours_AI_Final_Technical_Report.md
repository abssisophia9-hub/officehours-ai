---
title: "OfficeHours AI — Capstone Final Technical Report"
subtitle: "A Multi-Role Campus Office-Hours Triage System with Custom-Trained Ask Triage Agents"
author: "Sophia Abssi"
student_id: "117027"
supervisor: "Dr. Oumaima Hourrane"
program: "Artificial Intelligence and Robotization"
school: "School of Science and Engineering — Al Akhawayn University"
course: "EGR 4402 Capstone Design"
project_type: "Software Development Project"
evidence_tip: "origin/main db8de9b (merge of PR #147); freeze tag final-nov-16 → 6264d95"
date: "November 2026"
---

# Capstone Final Technical Report

**School of Science and Engineering**  
**Al Akhawayn University**  
*Inspire, Impact & Transform*

**Title:** OfficeHours AI: A Multi-Role Campus Office-Hours Triage System with Custom-Trained Ask Triage Agents  

**Student:** Sophia Abssi (ID 117027)  
**Degree Program:** Artificial Intelligence and Robotization  
**Supervised by:** Dr. Oumaima Hourrane  
**Project Type:** Software Development Project  
**Evidence baseline:** `origin/main` at `db8de9b` (PR [#147](https://github.com/abssisophia9-hub/officehours-ai/pull/147)); freeze tag `final-nov-16` → `6264d95`

---

## Student conduct and copyright

The supervisor and the student (the Capstoner) agree that:

1. Permission has been obtained for any third-party content (data, illustrations, photographs, charts, or maps) used in this report, or such content is original / public-domain / properly cited.
2. The results described in this report have not previously been published as a completed thesis or journal article.
3. Training and evaluation corpora used for model scores are synthetic, silver, or curated public-style laboratory labels — not scraped private AUI student emails or LMS transcripts.
4. Quantitative claims are labeled MEASURED / ESTIMATED / NOT MEASURED where evidence packs apply.

**Student’s name:** Sophia Abssi  
**Supervisor’s name:** Dr. Oumaima Hourrane  

---

## Student Statement

I certify that this Capstone Final Technical Report is my own work as Capstone student for EGR 4402, that the software system described is the OfficeHours AI product developed under the supervision of Dr. Oumaima Hourrane, and that evaluation numbers cited herein are taken from repository artifacts and evidence registers with honesty notes. Where laboratory metrics are reported, I do not claim them as live AUI section quality. Canvas launch screenshots show an unsigned demo simulator unless otherwise stated; production campus launch requires Canvas LTI 1.3 credentials issued by AUI IT.

**Student’s name:** Sophia Abssi  
**Approved by the Supervisor:** Dr. Oumaima Hourrane  

---

## Acknowledgements

I thank Dr. Oumaima Hourrane for sustained technical and pedagogical supervision throughout the Capstone. I thank the School of Science and Engineering at Al Akhawayn University for the Capstone Design framework (EGR 4402) and for an institutional context in which Canvas-centered teaching support is the natural deployment path. I also acknowledge the open research and teaching-commons guidance on office hours and help-seeking that informed the curated held-out evaluation asks (cited in the References), and the engineering practice of keeping assessed triage models local, measurable, and professor-gated.

---

## Contents

1. Introduction  
2. Problem Statement  
3. Functional and Non-Functional Requirements  
4. Related Work  
5. System Design  
 5.1 Software Development Lifecycle  
 5.2 System Architecture  
 5.3 Database Design  
 5.4 Technology Stack and Frameworks  
6. AI Use, Evaluation and Evidence  
 6.1 AI Tools and Purpose  
 6.2 AI-Assisted Development Activities  
 6.3 AI Output Evaluation  
 6.4 Critical Reflection and Limitations  
 6.5 Supporting AI Evidence  
7. Implementation  
8. Testing  
9. Discussion and Analysis  
10. Conclusion  
11. Future Work  
References  
Appendix A — Reproducibility Codex  
Appendix B — Evaluation Artifacts and Survey Summary  
Appendix C — Product Screenshots  

---

## List of Figures

- **Figure 1.** Platform architecture (unified product app, API, agents, Canvas).  
- **Figure 2.** End-to-end office-hours workflow (ask → triage → TA → professor stamp → Study Agent).  
- **Figure 3.** Ask Triage specialists (Analyzer → Matcher → Synthesizer).  
- **Figure 4.** Database entity-relationship overview.  
- **Figure 5.** Canvas enrollment / launch path (demo vs LTI).  
- **Figure 6.** Product deployment (demo vs community).  
- **Figure 7.** Study Agent retrieval-only vs retrieval+check outcomes (mid-report evaluation figures).  
- **Figure 8.** Unified product login (`:5180`).  
- **Figure 9.** Student Quiet ask with Ask Triage feedback.  
- **Figure 10.** TA Help Coach surface.  
- **Figure 11.** Professor knowledge / material gate.  
- **Figure 12.** Canvas launch simulator (unsigned demo).  

---

## List of Tables

- **Table 1.** Functional requirements (FR) and tip status.  
- **Table 2.** Non-functional requirements (NFR) and tip status.  
- **Table 3.** Related-work comparison criteria.  
- **Table 4.** Core ORM entities.  
- **Table 5.** Technology stack.  
- **Table 6.** AI surfaces: audience, mechanism, LLM use.  
- **Table 7.** Ask Triage / Study Agent laboratory metrics (MEASURED).  
- **Table 8.** Latency / cost / load spot checks (MEASURED where labeled).  
- **Table 9.** Legacy pilot survey Likert averages (MEASURED; UI caveat).  
- **Table 10.** Implemented product features at freeze tip.  
- **Table 11.** Automated test inventory at tip.  

---

## Abstract (English)

OfficeHours AI is a packaged multi-role campus web application for office-hours triage at Al Akhawayn University (AUI). Students, teaching assistants (TAs), and professors share one React application; role is decided per course membership. At ask intake, a custom-trained **Ask Triage** pipeline (Analyzer → Matcher → Synthesizer) classifies the question, recommends staff, and retrieves a teaching hint using local sentence-transformer embeddings and scikit-learn models only. Mid-session, a **Help Coach** assists TAs via retrieval over a teaching bank and approved knowledge-base neighbors plus fixed reply templates, with an optional learning-style logistic regression signal — Help Coach is **not** a hosted LLM. Professors remain the publication gate for what the student **Study Agent** may quote. This report describes the shipped system at `origin/main` (`db8de9b`, PR #147; freeze tag `final-nov-16`), technical evaluation on synthetic/silver/curated labels, Study Agent retrieval and optional Gemini check results, a small legacy pilot survey, load/latency spot checks, and honest limits (gold-label size, unsigned Canvas demo simulator, future LTI hardening).

**Keywords:** office-hours triage, educational AI, human-in-the-loop, Canvas LTI, retrieval-augmented teaching support

---

## Résumé (French)

OfficeHours AI est une application campus multi-rôles pour le triage des heures de permanence à l’Université Al Akhawayn. Étudiants, assistants et professeurs partagent une seule application web ; le rôle dépend de l’inscription au cours. À la soumission d’une demande, le pipeline **Ask Triage** (Analyseur → Apparieur → Synthétiseur) classe la question, recommande un assistant et récupère un indice pédagogique à partir de modèles locaux uniquement. Le **Help Coach** assiste les assistants par retrieval et modèles de réponse (régression logistique de style optionnelle) — ce n’est **pas** un LLM hébergé. Le professeur reste le garde-fou de publication pour l’**Study Agent**. Ce rapport décrit le système livré, l’évaluation laboratoire, les limites (labels, simulateur Canvas non signé, LTI à finaliser) et les preuves mesurées.

**Mots clés :** triage des heures de permanence, IA éducative, supervision humaine, Canvas LTI, retrieval pédagogique

---

## 1. Introduction

During final-exam periods, professors and TAs receive many repeated or overlapping student questions, while some students delay asking for help because of stress, embarrassment, or uncertainty about how to phrase their confusion. Existing campus channels — Canvas inbox, email, FIFO queues, and generic chatbots — store messages or generate answers, but they rarely (i) structure an ask into category, urgency, and staff recommendation with published laboratory scores, (ii) hide identity when a student chooses a Quiet ask, (iii) cluster repeated conceptual stuck points into one shared review, and (iv) require a professor stamp before a software agent may quote course material.

OfficeHours AI addresses both sides of this problem inside one product: triage and clustering at intake, live TA staffing with Help Coach, professor-gated knowledge publication, classmate Rooms, and a Canvas-first enrollment story. The Capstone is a **software development** project: one React single-page application and one FastAPI process, with assessed intake AI kept local and measurable.

### 1.1 Research question

Can an AI-assisted office-hours triage system reduce faculty communication overload and improve student comfort in seeking academic help during final exam periods — without replacing the human session, and without publishing unstamped material through an agent?

### 1.2 Contributions

1. **One multi-role product app** with login (or Canvas launch simulation) and role-per-course memberships (a TA can also be a student elsewhere).  
2. **Custom-trained Ask Triage** agents (Analyzer / Matcher / Synthesizer) on the assessed path — no hosted LLM required for intake.  
3. **Help Coach** for TAs: retrieval + templates + optional learning-style LogReg — not an LLM coach.  
4. **Professor publication gate** for the Study Agent; Quiet ask / Identify me; privacy-safe request-code status; shared group meetings for repeated clusters.  
5. **Reproducible evaluation artifacts**, automated tests (**345** collected at tip; PR #147 reports **345 passed** with lexical clustering), and CI on backend + product app.

### 1.3 Evidence baseline and reading guide

Unless otherwise stated, claims refer to repository tip `db8de9b` on `origin/main` (merge of PR #147, AUI CDN `OFFICEHOURS_ROOT_PATH`) and freeze tag `final-nov-16` (`6264d95`). Numbers are preferred from MEASURED artifacts under `reports/final_report/` and the Project evidence pack. Marketing language is avoided; honesty notes accompany laboratory metrics.

---

## 2. Problem Statement

### 2.1 Operational problem

Finals week produces the same conceptual ask many times. Staff time is spent re-answering rotations, hashing, induction proofs, or logistics that could have been clustered. Concurrently, students whose communication style does not fit public forums or named email may avoid asking even when they need help. Canvas already stores modules, files, grades, and an inbox; it does not classify a live conceptual ask, assign a TA by expertise and queue depth, group five similar stuck points into one cluster, or require a professor stamp before a software agent quotes the syllabus.

### 2.2 Research framing

The system under test must therefore (1) structure each ask, (2) cluster repeats, (3) route a TA (or the professor when no TA exists), (4) offer a Quiet receipt, and (5) let a professor stamp the only text an agent may later quote. Success for this Capstone is a demoable loop, passing tests, published lab metrics with honesty notes, and a documented community hand-off — **not** a claim that laboratory F1 equals live AUI section quality.

### 2.3 Stakeholders

| Stakeholder | Need |
| --- | --- |
| Students | Quiet or identified ask; status by code; Study Agent on stamped notes; Rooms; Pedagogy / Revision plan |
| TAs | Live queue; claim; Help Coach; reply before resolve; optional group meeting |
| Professors | Material stamp; Insights; Team load; planner cards |
| AUI IT / SSE | Canvas LTI 1.3 + API token; Postgres when hosted; CDN sub-path (`/officehours-ai`) |
| Examiners | Defendable metrics with caveats; reproducible demo |

### 2.4 Scope and out of scope

**In scope:** unified React SPA + FastAPI; SQLite demo / Postgres host; Ask Triage; clustering; Help Coach; professor-gated Study Agent; Rooms; peer notes; WebSocket `/ws`; Canvas LTI code path + demo simulator; pytest; defense docs; `OFFICEHOURS_ROOT_PATH` for CDN.

**Out of scope:** physical kiosk / NFC / barcode hardware; SIS / portal scraping; claiming curated gold *n*=80 as campus human gold; Microsoft SSO in production before IT issues credentials; WebSocket soak as MEASURED campus capacity (NOT MEASURED).

---

## 3. Functional and Non-Functional Requirements

Requirements below are reconstructed from the Capstone proposal and tip product behavior. Labels FR/NFR are report identifiers (not a separate requirements management tool).

### 3.1 Functional requirements

**Table 1.** Functional requirements and tip status.

| ID | Requirement | Tip status (db8de9b / final-nov-16 lineage) |
| --- | --- | --- |
| FR1 | Student submits Quiet ask or Identify me with help mode (message / face-to-face / online) | Implemented (`POST /requests/`) |
| FR2 | Ask Triage runs Analyzer → Matcher → Synthesizer on submit and persists triage fields | Implemented (`ask_triage_service.py`, `triage_*`) |
| FR3 | Similar asks share `cluster_id`; staff may publish one shared group meeting | Implemented |
| FR4 | TA claim / help / reply; Help Coach drafts stay on TA screen until TA sends | Implemented (`/ta/claim/`, `/ta/assist/`) |
| FR5 | Professor approves/edits/rejects KB; Study Agent quotes only `approved` | Implemented (`POST /agent/ask`) |
| FR6 | Course-scoped login + course picker; role per membership | Implemented |
| FR7 | Canvas launch path (demo simulator and/or LTI 1.3) + materials sync into pending KB | Code present; live campus key **not** installed (demo honesty) |
| FR8 | Rooms classmate forum with Canvas-module (or demo) chapters | Implemented (`/help-room/`) |
| FR9 | Privacy-safe status by request code | Implemented |
| FR10 | CDN / sub-path deploy via `OFFICEHOURS_ROOT_PATH` | Implemented (PR #147) |

### 3.2 Non-functional requirements

**Table 2.** Non-functional requirements.

| ID | Requirement | Tip evidence |
| --- | --- | --- |
| NFR1 | Assessed intake without hosted LLM | `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` on assessed path; local joblibs |
| NFR2 | Reproducible tests in CI | GitHub Actions: backend tests + product app build/audit; **345** tests collected locally |
| NFR3 | Demo vs community mode | `OFFICEHOURS_DEMO=true` seeds Sara/Youssef; `false` for campus |
| NFR4 | Quiet ask does not leak name on staff queue / status | Covered by privacy tests / design (`ethics_privacy.md`) |
| NFR5 | Rate limiting for abuse resistance | MEASURED probe 70/100 → HTTP 429 (evidence Part 7) |
| NFR6 | Ask Triage interactive latency usable in demo | MEASURED Part 4 p50 ≈ 30 ms (n=10); separate TestClient smoke p50 62.57 ms (n=5, lexical) |
| NFR7 | Honest evaluation labeling | Lab metrics cited with synthetic/silver/curated caveats |

---

## 4. Related Work

### 4.1 Baselines

1. **LMS / Canvas inbox and office-hours plugins** — store tickets and files; do not run Analyzer→Matcher→Synthesizer or require a stamp before an agent quotes a note.  
2. **Academic RAG / tutors (including hosted GPT/Claude wrappers)** — generate answers from a corpus; without a professor publication gate they can invent a syllabus. OfficeHours Study Agent copies stamped text or refuses below similarity 0.42.  
3. **Queue / helpdesk products** — FIFO or single-assignee rules; they do not embed asks or suggest `group_session` when cluster size ≥ 3.  
4. **Campus chatbot pilots** — usually one prompted LLM with web tools; hard to score category/TA F1 for a Capstone defense. This project keeps local, measured classifiers on intake.

### 4.2 Differentiation

**Table 3.** Comparison criteria.

| Criterion | Typical baseline | OfficeHours AI |
| --- | --- | --- |
| Intake structure | Manual / FIFO | Ask Triage joblibs with published lab scores |
| Agent quotes | Ungated generation | Professor stamp required |
| Identity | Name required | Quiet ask default option |
| TA assist | Ad hoc notes | Help Coach retrieval + templates (not LLM) |
| Deployment | Second password site | Canvas LTI-intended; CDN sub-path ready |

The contribution is an **AUI-integrated loop** (role-per-course, Quiet ask, professor stamp, LTI path), not a new embedding algorithm.

---

## 5. System Design

### 5.1 Software Development Lifecycle

The project followed an iterative Capstone lifecycle aligned with the proposal phases:

1. **Problem definition** — finals overload + help-seeking mismatch.  
2. **Requirements / investigation** — baselines; evaluation data honesty; Canvas-first enrollment.  
3. **Technical design** — Ask Triage specialists; Help Coach; Study Agent gate; Rooms.  
4. **Implementation / experimentation** — unified SPA; FastAPI; joblib training scripts; demo seed.  
5. **Validation** — pytest; classifier/matcher/gold artifacts; Study eval harness; evidence Parts 1–7; legacy survey.  
6. **Finalization** — defense docs; freeze tag `final-nov-16`; CDN root-path (PR #147); community hand-off notes.

Development used short pull-request iterations with CI on every change (backend pytest + product `npm` build/audit). Prompt/lab notebook entries live in `docs/prompt_log.md` for the AI-use section.

### 5.2 System Architecture

Layers at tip:

1. **Product app** (`frontend/officehours-app`, port 5180) — login, course picker, student / TA / professor workspaces, Canvas simulator.  
2. **Backend API** (FastAPI / SQLAlchemy) — auth, requests, Ask Triage, Help Coach, knowledge, peer notes, Rooms, analytics, WebSockets.  
3. **Ask Triage AI** — Analyzer / Matcher / Synthesizer using MiniLM embeddings + scikit-learn models on disk (`backend/models/*.joblib`).  
4. **Help Coach** — mid-session TA assist (`POST /ta/assist/`) via retrieval + templates (+ optional style LogReg signal).  
5. **Study Agent / Pedagogy** — stamped-KB answers; optional Gemini check under policy gates; Pedagogy/Revision plans with web Resources when enabled.  
6. **Canvas path** — JIT launch provisioning + materials sync; **unsigned demo** unless LTI credentials exist.  
7. **Deploy** — SQLite demo or Postgres; optional `OFFICEHOURS_ROOT_PATH` for `https://cdn.aui.ma/officehours-ai/`.

**Figure 1** (`figures/fig-platform.png`) and **Figure 2** (`figures/fig-workflow.png`) illustrate the platform and workflow. **Figure 3** (`figures/fig-ask-triage.png`) shows the three Ask Triage specialists.

#### End-to-end data flow

1. Student submits (`POST /requests/`) with Quiet ask or Identify me and a help mode.  
2. Ask Triage runs Analyzer → Matcher → Synthesizer; request is clustered; a `pending_review` knowledge draft is seeded.  
3. WebSocket `/ws` updates TA and professor workspaces.  
4. TA claims / helps; Help Coach may draft replies or Socratic steps; repeated clusters may share one group meeting.  
5. Professor approves/edits/rejects KB material — only approved answers reach the Study Agent (`POST /agent/ask`).

### 5.3 Database Design

Default store is SQLite at `backend/officehours.db` (`Base.metadata.create_all` at startup). Hosted deployments set `DATABASE_URL` to Postgres.

**Table 4.** Core entities (simplified).

| Entity | Role |
| --- | --- |
| `users` | Account identity (`email`, `display_name`, optional `student_id`) |
| `courses` | Course code/title/term; optional `canvas_course_id` |
| `course_memberships` | Per-course role: `student` \| `ta` \| `professor` |
| `auth_sessions` | Bearer sessions |
| `requests` | Ask text, anonymity, triage fields, assignment, work_status, help_mode, cluster_id, TA reply |
| `knowledge_entries` | Pending/approved/rejected material for Study Agent / coaching neighbors |
| Rooms / help-room tables | Named classmate posts, chapters, interest, ranks |

**Figure 4** (`figures/fig-database-erd.png`) shows the ER overview. Quiet ask stores no staff-visible name; `created_by_user_id` still lets the submitter open *My asks* without exposing identity on the queue.

### 5.4 Technology Stack and Frameworks

**Table 5.** Technology stack.

| Layer | Choice | Rationale |
| --- | --- | --- |
| Frontend | React 19, Vite, Tailwind, React Router | One SPA for all roles |
| Backend | FastAPI, SQLAlchemy, Pydantic | Typed API; fast local demo |
| DB | SQLite (demo) / Postgres (host) | Zero-ops demo; durable host |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` (lexical fallback in tests) | Trainable local vectors |
| Classifiers | scikit-learn LogReg joblibs | Measurable intake |
| Realtime | WebSocket `/ws` | Live queue without polling |
| CI | GitHub Actions | Backend + product app |
| Optional LLM | Gemini (`gemini-3.5-flash-lite`) under policy | Study check / Pedagogy — **not** assessed Ask Triage; **not** Help Coach core |

---

## 6. AI Use, Evaluation and Evidence

### 6.1 AI Tools and Purpose

**Table 6.** AI surfaces.

| Surface | Audience | Mechanism | Hosted LLM? |
| --- | --- | --- | --- |
| Ask Triage Analyzer | System at intake | MiniLM + `request_classifier.joblib` LogReg (+ overlays) | No |
| Ask Triage Matcher | System at intake | MiniLM + `matcher_classifier.joblib` + roster/queue blend | No |
| Ask Triage Synthesizer | System at intake | Retrieval / ranker over approved KB + teaching bank; copies hint | No |
| Learning-style LogReg | Intake → coaching signal | `learning_style_classifier.joblib` (CV mean 0.925, n=40, lab) | No |
| Help Coach | TA | Retrieval over teaching bank (68-row) + approved KB neighbors + fixed templates / Socratic steps; consumes style signal | **No** (not an LLM coach) |
| Study Agent | Student | Cosine search over **approved** KB; refuse < 0.42; optional Gemini entailment/check under gates | Optional check only |
| Pedagogy / Revision | Student | Plan + Resources (web/YouTube when enabled) | Optional |

### 6.2 AI-Assisted Development Activities

Capstone engineering used Cursor Cloud Agents extensively for implementation, tests, docs, and evidence packs, under human supervision (Sophia Abssi) and faculty supervision (Dr. Hourrane). Pull-request history on `main` records merges with `Co-authored-by: SOPHIA` trailers. The lab notebook `docs/prompt_log.md` records factual PR metadata; narrative prompt fields remain student-owned where marked TODO. AI-assisted code was accepted only after tests/CI and human review of product vocabulary (Ask Triage, Help Coach, Rooms).

### 6.3 AI Output Evaluation

#### 6.3.1 Ask Triage — Analyzer (MEASURED)

On the union of synthetic/curated labeled CSVs (**n=156**), embedding + logistic regression reaches approximately **84.62%** stratified CV accuracy and **0.8455** macro F1 (`reports/final_report/classifier_evaluation.json`). Labels are **not** private AUI transcripts.

#### 6.3.2 Ask Triage — Matcher (MEASURED)

Silver holdout accuracy **87.5%** (28/32; macro F1 ≈ 0.76) (`matcher_evaluation.json`). Labels come from expertise overlap with the demo TA roster — **not** independent gold TA judgments.

#### 6.3.3 Held-out curated gold file (MEASURED)

Gold file **n=80** (12 illustrative seed + 68 curated held-out public-style asks). Analyzer accuracy **75.0%** (macro F1 ≈ 0.66); Matcher accuracy **78.75%** (macro F1 ≈ 0.78). These are **not** scraped private emails and **not** independent campus TA `human_gold` judgments.

#### 6.3.4 Learning-style classifier (MEASURED, laboratory)

`learning_style_evaluation.json`: CV accuracy mean **0.925** (std 0.10) on **n=40** examples across conceptual / example_driven / step_by_step / visual_structural / unknown. Used as an optional signal for coaching templates — not as a clinical diagnosis of learning style.

#### 6.3.5 Study Agent retrieval and check (MEASURED from saved eval files)

From mid-report evidence register (`docs/midreport/EVIDENCE.md`):

- Retrieval-only, sentence-transformers, both filters: **50/75** correct (MEASURED).  
- With Gemini check (`gemini-3.5-flash-lite`, prompt `study-answer-check-v1`): **74/75** harness-correct (MEASURED from saved file; not re-run in this report compilation).  
- Weak-match refusal threshold **0.42** (production cutoff).

#### 6.3.6 Help Coach bank relevance (MEASURED, limited)

Evidence pack cites Help Coach relevant teaching-bank hits **2/16** on a probe set — a ceiling reminder that Help Coach is retrieval + templates, not a generative tutor.

#### 6.3.7 Latency, cost, load (MEASURED spot checks)

**Table 8.** Selected operations metrics.

| Metric | Value | Label | Source |
| --- | --- | --- | --- |
| Ask Triage p50 | ≈ 30 ms (n=10) | MEASURED | evidence Part 4 |
| Ask Triage TestClient p50 | 62.57 ms (n=5, lexical) | MEASURED | `ask_triage_latency.json` |
| Study live wall | ≈ 1305 ms | MEASURED | evidence Part 2 |
| Pedagogy live wall | ≈ 2381 ms | MEASURED | evidence Part 2 |
| Gemini Flash-Lite Standard $/1M | $0.30 in / $2.50 out | MEASURED (price page) | freeze flash-lite cite |
| File-SQLite load concurrency 40 | 0 errors | MEASURED | evidence Part 7 |
| Rate limit probe | 70/100 → 429 | MEASURED | evidence Part 7 |
| Campus concurrent capacity | — | ESTIMATED / NOT MEASURED as production soak | Part 7 |
| WebSocket soak | — | NOT MEASURED | Part 7 |

#### 6.3.8 Legacy pilot survey (MEASURED; UI caveat)

**Table 9.** Likert averages (1–5).

| Cohort | Highlights | n |
| --- | --- | --- |
| Students | Ease 4.5; anonymous comfort 4.5; more likely to seek help 4.5 | 8 |
| Professors | Queue clarity 4.5; clustering 4.5; control 5.0; workload reduction 4.25 | 4 |

**Important:** this pilot targeted the **legacy** kiosk + professor dashboard UI. It supports early usability/privacy claims; it does **not** measure Ask Triage naming, Help Coach, or the unified app `:5180`. A new unified-app survey round is **not required** for the Capstone presentation (`docs/fyp_evidence.md`).

### 6.4 Critical Reflection and Limitations

1. Laboratory metrics ≠ campus quality. Real TA `human_gold` (≥40) remains the stronger bar.  
2. Help Coach must not be described as an LLM: it is retrieval + templates + optional style LogReg.  
3. Canvas `/canvas-demo` is an **unsigned** simulator; production needs LTI 1.3 developer key + API token.  
4. Some list endpoints remain open for local demos; production needs tighter authorization.  
5. Clustering silhouette / longitudinal KB hit-rate tables remain evaluation backlog.  
6. Optional Gemini paths burn quota; assessed FYP intake path keeps external LLM off.

### 6.5 Supporting AI Evidence

Primary artifacts shipped with this deliverable under `appendix/`:

- `classifier_evaluation.json` / `.md`  
- `matcher_evaluation.json`  
- `gold_label_evaluation.json`  
- `learning_style_evaluation.json`  
- `ask_triage_latency.json`  
- `survey_evaluation_summary.md` / `.json`  

Project store evidence pack (Parts 1–7): `/cursor/stores/bc-dc51837a-fa18-4db3-a65f-0e58caaf18ec/docs/evidence/`.  
Defense crib: `docs/fyp_evidence.md`.

---

## 7. Implementation

### 7.1 Product surfaces

**Table 10.** Features at freeze tip.

| Component | Feature |
| --- | --- |
| Product app | Login, course switcher, dual-role TA+student |
| Student | Quiet ask / Identify me, help modes, status lookup, Study Agent, Pedagogy Agent, Rooms, classmate notes, Inbox |
| TA | Claim / help / reply / backup handoff, Help Coach, Past asks |
| Professor | Material stamp, Your desk, Insights, Team, planner cards, Canvas sync |
| Backend | Ask Triage, clustering, auth, WebSockets, analytics, `.ics`, root-path deploy |
| DevOps | GitHub Actions CI, `run_product.sh`, Windows start scripts, seed script |

### 7.2 Ask Triage implementation notes

Module: `backend/app/services/ask_triage_service.py`. On `POST /requests/`:

1. **Analyzer** writes category, urgency, difficulty, estimated minutes, tags, learning style.  
2. **Matcher** writes `assigned_ta` / `alternative_ta` (or professor when no TA).  
3. **Synthesizer** retrieves nearest professor-approved note (or teaching-bank row) and copies `student_hint` — it does not author a free-form paragraph from a hosted LLM.  
4. Clustering shares `cluster_id` when cosine similarity is high (threshold documented in product docs; lexical backend in tests).

### 7.3 Help Coach implementation notes

Module: `backend/app/services/help_coach_service.py`. Endpoints `GET /ta/coach/`, `POST /ta/assist/`. Behavior:

- Retrieve neighbors from the teaching bank and approved KB.  
- Emit Socratic steps / draft / rewrite / refresh teaching script via **templates**.  
- Factual/logistics asks get a logistics draft — **not** a teaching checklist.  
- Drafts remain on the TA screen until the TA sends a reply.  
- Learning style from Ask Triage may bias explanation preference text.  
- **Not a trained generative coach model; not a hosted LLM.**

### 7.4 Study Agent and professor gate

Only `knowledge_entries` with status `approved` may be quoted. Similarity below **0.42** refuses. Optional Gemini check validates quotes/entailment under `OFFICEHOURS_LLM_*` policy budgets (kill switch, per-user/day caps, breaker) documented in mid-report evidence.

### 7.5 Canvas and deploy

- Demo: `OFFICEHOURS_DEMO=true` seeds AUI-style accounts (password `aui-demo`) and local Canvas mirror.  
- Production intent: signed LTI 1.3 (`/lti/login`, `/lti/launch`) + `CANVAS_*` credentials.  
- PR #147: `OFFICEHOURS_ROOT_PATH` for CDN same-origin under `/officehours-ai`.

Demo screenshots: **Figures 8–12** in `figures/product-*.png`.

---

## 8. Testing

### 8.1 Automated suite

**Table 11.** Test inventory.

| Item | Value | Label |
| --- | --- | --- |
| Pytest collected at tip worktree | **345** | MEASURED (`pytest --collect-only`) |
| PR #147 CI claim | **345 passed** (lexical clustering) | MEASURED (PR body) |
| Earlier evidence pack tip | 332 passed, 1 skipped (older SHA) | Historical |
| CI jobs | Backend tests; Product app build and audit | Continuous |

Coverage includes auth, Canvas launch simulation, Ask Triage fields, Help Coach, TA staffing, peer notes, knowledge gating, clustering, agent-quality smoke locks, root-path deploy, and privacy-sensitive Quiet ask behaviors.

### 8.2 Evaluation harnesses (beyond unit tests)

- `scripts/train_classifier.py` / `train_matcher.py` / `train_learning_style.py` / `train_synthesizer.py`  
- `scripts/evaluate_gold_labels.py`  
- `scripts/measure_ask_triage_latency.py`  
- Study eval harnesses under `docs/eval_results/`  
- Evidence Parts 2/4/7 live/mocked runs in the Project store  

### 8.3 Manual / defense walkthrough

Required human path (`docs/fyp_evidence.md`): Quiet ask → Ask Triage breakdown → Alice claim → Help Coach → reply or group meeting → Benali approve KB → Study Agent quotes only stamp → Rooms named post → state clearly that Canvas demo is unsigned.

---

## 9. Discussion and Analysis

### 9.1 Answering the research question

Evidence supports **feasibility** of an AI-assisted triage loop that structures asks, routes staff, preserves Quiet ask privacy, and keeps professors as publication gatekeepers. Laboratory Analyzer/Matcher scores and Study Agent refusal/check results show that local models can produce defendable, reproducible behavior. The legacy pilot survey suggests students and professors rated usability and control above the ≥4.0 target on the older UI — with the explicit caveat that it is not a unified-app measurement.

The research question is **not** claimed as experimentally closed on a live AUI section: that would require institutional ethics approval, real `human_gold` labels, signed LTI, and longitudinal workload metrics.

### 9.2 What worked

- Keeping assessed intake local (joblibs) made evaluation and offline demos tractable.  
- Separating Help Coach (retrieval/templates) from Study Agent (stamped quotes) clarified responsibility: TAs see drafts; students see only stamped agent answers (plus intentional TA async replies on request status).  
- Role-per-course membership matched AUI reality (TA on one course, student on another).  
- Honesty notes in `fyp_evidence.md` reduced over-claim risk for defense.

### 9.3 What remains fragile

- Matcher labels tied to demo roster names.  
- Curated gold still easier than messy live asks.  
- Help Coach teaching-bank hit rate on the probe (2/16) shows retrieval limits.  
- Unsigned Canvas simulator must not be verbally upgraded to “live in AUI Canvas.”  
- Optional Gemini features need quota discipline (`OFFICEHOURS_DEMO=false` blocks external Gemini on community defaults per product docs).

### 9.4 Ethics and privacy

Design principles (`docs/ethics_privacy.md`): Quiet ask anonymity for staff asks; Rooms are named classmate spaces; professor gate for Study Agent; data minimization; escalation for sensitive content; IRB required before real student corpus collection. Misclassification risk is mitigated by human staffing — AI does not auto-resolve grades or publish FAQ without review.

---

## 10. Conclusion

OfficeHours AI delivers a defendable Capstone software system: a unified multi-role campus application, custom-trained Ask Triage under a professor KB gate, TA Help Coach implemented as retrieval plus templates (with optional learning-style LogReg — **not** an LLM), Rooms, measurable laboratory evaluation, and a Canvas-first / CDN-ready deployment story with an honest demo simulator today. At evidence tip `db8de9b` (PR #147) and freeze tag `final-nov-16`, the automated suite collects **345** tests, and core triage metrics are published with caveats. The work demonstrates that responsible educational AI for office hours can prioritize **human-in-the-loop publication**, **local measurable intake models**, and **privacy-preserving Quiet asks** over unconstrained generative answering.

---

## 11. Future Work

1. Run a gold-label lab with ≥40 real TA `human_gold` judgments (`docs/gold_label_lab.md`).  
2. Complete campus Canvas LTI 1.3 install (developer key + API token); retire unsigned simulator for non-demo environments.  
3. Tighten production ACLs on remaining open list endpoints; harden WebSocket authorization beyond demo.  
4. Publish longitudinal KB hit-rate and clustering quality tables.  
5. Optional unified-app UX survey (not required for Capstone presentation).  
6. Microsoft Entra SSO after IT app registration.  
7. Expand teaching-bank coverage to improve Help Coach retrieval hit rate while keeping the non-LLM design.  
8. Postgres-backed campus deploy behind `https://cdn.aui.ma/officehours-ai/` with monitored quotas.

---

## References

American Psychological Association. (2020). *Publication manual of the American Psychological Association* (7th ed.).

Al Akhawayn University. (n.d.). School of Science and Engineering. https://www.aui.ma/

Canvas LMS. (n.d.). *Learning Tools Interoperability (LTI) 1.3*. Instructure.

McGill University. (n.d.). Office hours and help-seeking guidance for students. Teaching and Learning Services.

Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. *Proceedings of EMNLP-IJCNLP*.

Stanford Teaching Commons. (n.d.). Office hours practices.

University of Iowa / UNC / Oregon State / University of Toronto TATP. (n.d.). Public office-hours and help-seeking guidance used as framing sources for curated held-out asks (see `docs/research/office_hours_public_sources.md`).

OfficeHours AI repository artifacts: `reports/final_report/*.json`, `docs/fyp_evidence.md`, `docs/midreport/EVIDENCE.md`, Project evidence pack Parts 1–7 (2026).

Google. (2026). Gemini API pricing (Flash-Lite Standard rates cited 2026-11-15). 

*APA in-text citation practice followed for the Capstone template requirement:* https://columbiacollege-ca.libguides.com/c.php?g=713274&p=5082934

---

## Appendix A — Reproducibility Codex

```bash
# Product demo (local)
./scripts/run_product.sh
# → http://127.0.0.1:5180  and  http://127.0.0.1:8000

# Backend tests
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python -m pytest

# Regenerate evaluation artifacts
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_classifier.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_matcher.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/evaluate_gold_labels.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/measure_ask_triage_latency.py

# Seed demo data
venv/bin/python scripts/seed_demo_data.py
```

Demo accounts when `OFFICEHOURS_DEMO=true` (password `aui-demo`): `s.elidrissi@aui.ma` (student), `a.chen@aui.ma` (TA), `a.benali@aui.ma` (professor).

Evidence tip: `git checkout db8de9b` or tag lineage `final-nov-16` (`6264d95`) then PR #147.

---

## Appendix B — Evaluation Artifacts and Survey Summary

Machine-readable copies are in `appendix/` next to this report. Narrative survey summary matches `reports/final_report/survey_evaluation_summary.md` (legacy UI caveat).

---

## Appendix C — Product Screenshots

See `figures/product-01-login.png` … `product-06-canvas-simulator.png`. Architecture and workflow diagrams: `figures/fig-*.png`.
