# OfficeHours AI — filled tables (project facts only)

Open this file in Cursor. The `.docx` is for Word/Google Docs only.

## Cover

| Project Title | OfficeHours AI: A Multi-Role Campus Office-Hours Triage System with Custom-Trained Ask Triage Agents. |
| --- | --- |
| Student Name | Sophia Abssi |
| Student ID | 117027 |
| Degree Program | Artificial Intelligence and Robotization |
| Supervisor | Dr. Oumaima Hourrane |
| Date of Submission | September 23, 2026 |

## Project Type

| [X] Software Development Project | [ ] Research-Based Project |
| --- | --- |
| OfficeHours AI: a unified campus web application (React SPA on port 5180 + FastAPI on port 8000) with custom-trained Ask Triage agents (Analyzer, Matcher, Synthesizer), TA Help Coach, professor-gated Study Agent, Rooms, and Canvas LTI 1.3. Not a mobile app and not a hardware kiosk. | Not selected. Analyzer/Matcher evaluation reports support the software product; this FYP is not a standalone research thesis. |

## Project Lifecycle

Official CSC phases kept as row labels. The old Purpose / Possible Activities cells were examples — they are gone. These cells are the OfficeHours answers.

| Phase | Purpose | Activities |
| --- | --- | --- |
| 1. Problem Definition & Background | Pin the AUI finals-week failure OfficeHours actually attacks: CSC courses such as CSC 2302 flood TAs and professors with the same conceptual asks, while Quiet students will not submit if the form forces a name. | Write the research question: can local Ask Triage cut repeated staff load and raise ask comfort. Freeze the product as one React SPA (`frontend/officehours-app`, port 5180) plus FastAPI (`backend/app.main:app`, port 8000). Role is `membership.role` on `course_id` (Sara student, Alice TA on 2302, Amine professor). Keep out of scope: kiosk :5173, professor-dashboard :5174, ta-dashboard :5175, barcode/NFC, scraping canvas.aui.ma. Specify Quiet-ask privacy: identity is stored but stripped on GET `/requests/{id}/status`. |
| 2. Investigation / Requirements | Gather the evidence, baselines, datasets, and campus constraints that bound Ask Triage so we do not claim live AUI transcripts we do not have, and so Canvas LTI is the real enrollment path. | Compare against Canvas inbox/tickets, ungated RAG chatbots, prompted LLM helpdesks, FIFO single-TA queues, and the old three web shells. Lock constraints already in code: LTI 1.3 OIDC + RS256 JWKS + nonce (`backend/app/services/lti13.py`); optional Microsoft Entra `@aui.ma`; `OFFICEHOURS_DEMO`; `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` on intake; tests use `OFFICEHOURS_CLUSTERING_BACKEND=lexical`. Freeze training data in the repo: Analyzer n=156 (`reports/classifier_evaluation.json`), Matcher silver labels (`matcher_evaluation.json`), gold held-out n=80 (`gold_label_evaluation.json`). |
| 3. Technical Design / Research Design | Design one login with per-course RBAC, Ask Triage at POST `/requests/`, a professor knowledge-base gate before any Study Agent answer, and a live TA queue over WebSocket. | Specify auth (`officehours_auth_token`, PBKDF2-HMAC-SHA256 120k) and SQLAlchemy tables: `users`, `memberships`, `requests` (`oracle_category`, `oracle_difficulty`, `cluster_id`, `help_mode`, `quiet`), `knowledge_entries` (`pending_review` → approved/rejected), `help_rooms`, `peer_notes`, `notifications`. Specify models: all-MiniLM-L6-v2 + sklearn LogReg joblibs for Analyzer and Matcher; Synthesizer retrieves teaching bank + approved KB only. Matcher returns `primary_ta_id`, `backup_ta_id`, `wait_estimate` (Alice/Bob on CSC 2302). Design Help Coach POST `/ta/assist/` `{draft_reply,socratic,rewrite_reply,refresh_teaching}`, Study Agent POST `/agent/ask`, clustering for Repeated Topics, routes `/student` `/ta` `/professor`, and realtime `/ws`. |
| 4. Development / Experimentation | Implement the running triage loop from Quiet ask to approved Study Agent answer, plus Rooms and Canvas launch, in this repository. | Ship routers `auth`, `requests`, `ta`, `knowledge`, `help_room`, `canvas`, `lti`, `realtime`. Train with `backend/scripts/train_classifier.py`, `train_matcher.py`, `train_synthesizer.py` → `backend/models/*.joblib`. Wire POST `/requests/` → Analyzer→Matcher→Synthesizer, `cluster_id`, pending KB draft. Staffing: POST `/ta/claim/`, `/ta/assist/`, `/ta/resolve/`. Professor approve/reject KB. Canvas POST `/canvas/launch` JIT provision; pypdf/python-docx ingest into KB and Rooms chapters. Rooms: Problem/Discussion/Article, Hilbert ŵ, Express Interest. Revision Strategist in localStorage (no Canvas gradebook API yet). Frontend: `AuthContext`, `AppShell`, `LoginPage` `/login?as=student\|ta\|professor`, demo password `aui-demo`. Hardening: `rate_limit.py`, upload magic, LTI nonce. |
| 5. Validation & Evaluation | Show whether the built system meets the objectives using pytest and lab model scores, with an honesty table rather than a live AUI accuracy claim. | Run pytest ≥162 covering Quiet-ask redaction, KB refuse-unapproved, dual-TA matcher, Canvas launch, upload/security. Report Analyzer stratified CV ~84.6% (n=156), Matcher holdout ~87.5% (silver), gold held-out Analyzer ~75% / Matcher ~79% (n=80, not campus `human_gold`). Walk through `s.elidrissi` Quiet ask on CSC 2302 → WebSocket to `a.chen` TA desk → Help Coach → `a.benali` approve FAQ → `/agent/ask` uses that FAQ only. Keep CI on backend + officehours-app. If examiners require human labels, run `docs/gold_label_lab.md` (target ≥40 `human_gold`). |
| 6. Finalization & Communication | Package a supervisor-runnable demo and a campus hand-off so Dr. Hourrane, Innovation Day, and AUI IT can inspect the same product. | Deliver `docs/defense_crib.md`, `docs/system_architecture.md`, `docs/SECURITY.md`, `docs/glossary.md`, and the 36×24 poster `docs/presentations/officehours-capstone-poster-36x24.html`. Launch with `./scripts/run_product.sh` (`OFFICEHOURS_DEMO=true`; `s.elidrissi@aui.ma` / `a.chen@aui.ma` / `a.benali@aui.ma`). Hand off production as `OFFICEHOURS_DEMO=false`, `DATABASE_URL` Postgres, Canvas LTI key, Microsoft SSO only after IT `client_id`. Repo github.com/abssisophia9-hub/officehours-ai. URLs http://127.0.0.1:5180 and http://127.0.0.1:8000/docs. |

## 4.3 Differentiation

| Criterion | Existing Work / Baseline | Proposed Approach | Expected Improvement / Difference |
| --- | --- | --- | --- |
| Performance / Accuracy | Generic campus chatbots / uncurated RAG with no held-out triage metrics | Local trained Ask Triage (Analyzer → Matcher → Synthesizer) with published CV, holdout, and gold evaluations | Transparent lab metrics (~84.6% Analyzer CV; ~87.5% Matcher holdout; ~75–79% gold held-out, n=80) with documented limits vs real AUI text |
| Cost / Complexity | Paid external LLM APIs and several disconnected student/TA/professor tools | One packaged app with local models; SQLite default and a Postgres path | Lower inference cost on the assessed path; simpler campus operations surface |
| Usability / Accessibility | Separate dashboards; identity always exposed when asking | Unified login, role per course, Quiet ask plus named Rooms | Fewer tools to learn; safer path for students who hesitate to ask |
| Scalability / Efficiency | Polling dashboards and single-TA queues | WebSocket live push, dual-TA Matcher, clustering with shared group meetings | Live queues and better staffing of repeated conceptual topics |
| Security / Reliability | Ad-hoc campus scripts with weak session handling | PBKDF2 sessions, JWT/JWKS LTI path, rate limits, 162+ pytest cases | Documented security hardening plus automated regression |
| Context-specific factor | Manual enrollment or AUI-portal scraping proposals | Canvas LTI 1.3 launch with materials sync; OFFICEHOURS_DEMO vs community modes | Fits the AUI LMS deployment model without kiosk / barcode / NFC hardware |

## 5.3 Success criteria

| Objective / Claim | Metric or Evidence | Target / Acceptance Criterion |
| --- | --- | --- |
| Working multi-role product (Obj. 1) | Product app on :5180 + API on :8000; student / TA / professor workspaces via course picker | All three role flows demoable end-to-end on CSC 2302 (Quiet ask, TA queue, professor KB gate) |
| Ask Triage quality (Obj. 2) | Classifier, matcher, and gold-label evaluation reports under reports/ | Metrics published with explicit limitation notes (synthetic/silver/gold vs live AUI text) |
| Complete triage loop (Obj. 3) | Help Coach, professor KB gate, Study Agent, Strategic Planner / Revision Strategist, Rooms, Canvas launch/sync | Study Agent answers only from approved KB; Canvas demo launch and Rooms chapters work in demo mode |
| Engineering reliability and privacy (Obj. 4) | pytest suite, CI product build, Quiet-ask status privacy checks | ≥160 backend tests passing; app CI green; Quiet-ask identity never appears on status lookup |

## 8 Deliverables

| Deliverable | Description / Acceptance Condition |
| --- | --- |
| D1 — Product application | Unified officehours-app (students, TAs, professors) with login, course picker, Quiet/Identify asks, Rooms, Strategic Planner / Revision Strategist, and role workspaces. Accepted when all three roles demo end-to-end. |
| D2 — Backend platform | FastAPI services for Ask Triage, Help Coach, KB/Study Agent, Rooms, Canvas/LTI, and WebSockets. Accepted when the pytest suite passes. |
| D3 — Trained models and evaluation reports | Analyzer / Matcher / Synthesizer artifacts plus CV, holdout, and gold held-out reports under reports/. Accepted when reports are in the repository with limitation notes. |
| D4 — Documentation and defense pack | Product overview, glossary, system architecture, defense crib, gold-label lab, and security notes. Accepted when a supervisor can run the documented demo. |
| D5 — Demo and deployment assets | scripts/run_product.sh demo mode, Innovation Day poster, and community deploy notes (OFFICEHOURS_DEMO=false + Canvas LTI checklist). |

## 9 Timeline

| Phase / Milestone | Major Tasks / Output | Start | End | Evidence of Completion |
| --- | --- | --- | --- | --- |
| 1. Definition & Background | RQ + scope freeze; PII/Quiet-ask analysis; this proposal for Dr. Hourrane (EGR 4402) | Sep 01, 2026 | Oct 01, 2026 | Milestone 1: approved problem scope + multi-role product vision |
| 2. Investigation / Requirements | Related work vs Canvas tickets/RAG/chatbots; freeze LTI 1.3 + OFFICEHOURS_DEMO; lock Analyzer/Matcher/gold datasets | Sep 15, 2026 | Oct 06, 2026 | Requirements notes in docs/; related-work section of this proposal |
| 3. Design / Research Design | Schema (requests.oracle_*, knowledge.pending_review); Ask Triage + Help Coach + /agent/ask contracts; UI map /student /ta /professor | Sep 20, 2026 | Oct 06, 2026 | Architecture diagrams; API design; Milestone 2 design freeze |
| 4. Development / Experimentation | Implement routers + joblib models; POST /requests/ pipeline; Rooms; Canvas launch ingest; Revision Strategist; WS hub | Oct 06, 2026 | Nov 11, 2026 | Milestone 3: Help Coach, KB gate, Rooms, Canvas path integrated; working demo |
| 5. Validation & Evaluation | pytest ≥162; write classifier/matcher/gold JSON; Quiet-ask E2E on CSC 2302; CI green | Nov 11, 2026 | Dec 01, 2026 | 162+ passing tests; evaluation JSON/MD under reports/ |
| 6. Finalization & Communication | defense_crib.md; 36×24 poster; run_product.sh; LTI/Postgres handover notes; live demo :5180 | Dec 01, 2026 | Dec 09, 2026 | Milestone 4: evaluation pack / defense materials; live demo |

## 10.1 Resources

| Resource | Purpose | Availability / Source |
| --- | --- | --- |
| Developer workstation (local or cloud CPU) | Development, MiniLM classifier training, and live demos | Student laptop; optional cloud VM |
| GitHub repository and CI | Version control, regression builds, documentation | github.com/abssisophia9-hub/officehours-ai |
| Python 3.12 and Node.js toolchains | Backend venv (FastAPI) and frontend build (Vite/React) | Open-source; installed in the project environment |
| Canvas LMS (AUI) with LTI 1.3 keys | Community enrollments, module chapters, and signed launch | AUI IT — demo mode (OFFICEHOURS_DEMO=true) removes this during development |

## 10.2 Budget

| Item | Quantity | Unit Cost (MAD) | Total (MAD) | Justification |
| --- | --- | --- | --- | --- |
| Software stack (React, FastAPI, sentence-transformers, scikit-learn) | — | 0 | 0 | Entirely open source; no paid LLM APIs on the assessed path |
| Optional cloud compute | 1 | 0–500 | 0–500 | Only if local hardware is insufficient for training |
| Innovation Day poster printing (36″ × 24″) | 1 | 150–400 | 150–400 | Physical academic poster for exhibition |
| Estimated total |  |  | 0–900 | No mandatory direct expenditure; state explicitly: core project requires 0 MAD |

## 11 Risks

| Potential Risk | Likelihood | Impact | Mitigation / Fallback |
| --- | --- | --- | --- |
| Canvas / IT credentials delayed (highest integration uncertainty) | Med | High | Ship OFFICEHOURS_DEMO=true and the unsigned Canvas launch simulator; document LTI install steps for IT |
| Model metrics over-claimed versus real AUI student text | Med | High | Publish the metric-honesty table; run the human gold-label lab (≥40); keep prompted LLMs off the assessed intake path |
| Scope creep (hardware kiosk, extra agents, multi-campus) | Med | Med | Keep kiosk/NFC out of scope; freeze the triage loop (Ask Triage, Help Coach, KB gate, Rooms, Canvas) before extras |
| Privacy leak on Quiet asks | Low | High | Status endpoint strips identity; dedicated tests; security review checklist in docs/SECURITY.md |

## 12 Ethics (Project Response column)

| Consideration | Guiding Question | Project Response |
| --- | --- | --- |
| Human participants / user studies | Does the project collect data from or test with people? What consent/approval is required? | Optional walkthroughs/surveys with classmates and TAs use informed consent and no grade linkage. A legacy pilot (n=8 students, n=4 professors) was already collected. Any new human gold-label lab follows the same consent practice. |
| Privacy & personal data | What personal/sensitive data are collected or processed? How will access, storage, minimization, and retention be handled? | Emails, student IDs, and ask text are processed. Quiet asks minimize identity exposure; status lookups never reveal the asker. Demo data is synthetic. Session tokens are stored securely; PII is kept out of logs; retention follows course-term demo data, not a permanent student archive. |
| Cybersecurity | What security threats or misuse cases are relevant? What safeguards and testing are planned? | Threats: session theft, cross-course IDOR, prompt injection into the Study Agent, malicious uploads. Safeguards: authorization checks, rate limiting, professor KB gate, upload validation, and dedicated pytest security cases. |
| Legal / regulatory / licensing | Are there sector-specific rules, software licenses, data licenses, copyright, or API terms to consider? | Canvas and Microsoft API terms are respected. All core dependencies are open-source licensed. Portal scraping is rejected as an enrollment model in favor of LTI 1.3. |
| Engineering / technical standards | Identify standards, protocols, or best-practice guidelines relevant to the work. | HTTP/JSON APIs; Canvas LTI 1.3; JWT/JWKS validation; OWASP-inspired hardening documented in docs/SECURITY.md. |
| Responsible use of AI tools | If AI tools are used for coding, research, writing, design, or analysis, explain how outputs will be verified, attributed where required, and used transparently. | AI coding assistants may accelerate implementation. All critical logic is reviewed and covered by the pytest suite. FYP claims cite repository evidence (tests, evaluation JSON, docs), not generated prose alone. |
| AI system risks (if applicable) | Consider bias, hallucination, explainability, data provenance, model limitations, user oversight, and failure modes. | Risks: ask mis-routing, biased categories, Study Agent hallucination. Controls: local trained models with published evaluations, professor publication gate, refuse-unapproved answers, and human TA/professor oversight. |
| Environmental / accessibility considerations | Where relevant, consider energy/resource use, accessibility, inclusion, and deployment context. | Local MiniLM classifiers avoid large external LLM energy/cost on the assessed path. The web app uses clear role labels and an English UI matching AUI instruction. |
