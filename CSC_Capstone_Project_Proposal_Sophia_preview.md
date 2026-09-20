# CSC Capstone Project Proposal - Sophia Abssi (Refined Preview)

> This Markdown file is only a readable preview. Submit the `.docx` file for the official formatted version.

School of Science & Engineering

CAPSTONE DESIGN - EGR 4402 01

CAPSTONE PROJECT PROPOSAL

### Project Type

## Project Lifecycle

## 1. Executive Summary

OfficeHours AI is a multi-role campus web application designed to reduce faculty and teaching-assistant communication overload during high-pressure academic periods such as finals week. The system helps students submit academic help requests, either in identified mode or in a privacy-preserving Quiet Mode, and organizes those requests before they become scattered emails, repeated messages, or long informal queues.

The proposed system uses AI as a decision-support layer, not as a replacement for social interaction between students, TAs, and professors. Its Ask Triage pipeline analyzes incoming requests, groups repeated topics, estimates urgency and difficulty, recommends an appropriate support path, and drafts guidance that staff can review. Professors and TAs remain responsible for final decisions, communication, and academic judgment.

The product includes a unified student, TA, and professor application; a live TA queue; Help Coach support for TAs during sessions; a professor-approved knowledge base; a Study Agent that answers only from approved course materials; peer Rooms for classmate discussion; and a Canvas/LTI deployment path. The expected contribution is an integrated, privacy-aware, AI-assisted office-hours workflow tailored to the AUI academic context and evaluated through software tests, model reports, and documented product walkthroughs.

## 2. Problem Definition & Context

### 2.1 Problem Statement / Research Question

During peak academic periods, professors and TAs often receive many repeated conceptual questions, urgent requests, and individual messages through different channels. This creates delays for students and additional cognitive load for staff. Some students also hesitate to ask for help when they feel their identity is exposed or when they are unsure whether their question is appropriate.

Research question: Can an AI-assisted office-hours triage system reduce faculty communication overload while improving student comfort in seeking academic help, without replacing the human interaction that makes office hours valuable?

### 2.2 Project Context & Motivation

At Al Akhawayn University, Canvas and office hours are central to undergraduate academic support. However, existing LMS tools mainly organize course materials and announcements; they do not actively triage live help requests, recommend staffing, cluster repeated questions, or ensure that automated answers are based only on professor-approved material. OfficeHours AI responds to this gap by combining a practical software product with research potential in AI-assisted communication, help-seeking behavior, request classification, and responsible educational AI.

### 2.3 Stakeholders / Intended Users / Beneficiaries

- Students: submit identified or Quiet asks, receive status updates, join Rooms, and use approved Study Agent support.

- Teaching Assistants: manage live request queues, receive Help Coach suggestions, and resolve sessions efficiently.

- Professors: monitor repeated topics, approve or reject knowledge-base entries, view review insights, and control what the Study Agent can use.

- AUI IT and administration: benefit from a Canvas/LTI-ready deployment path and documented privacy/security controls.

- FYP examiners and peer institutions: evaluate a complete AI-assisted office-hours support model with explicit limits and evidence.

### 2.4 Scope, Constraints & Assumptions

In scope: a unified React/FastAPI application; AI-assisted Ask Triage using local models; Help Coach; Study Agent with professor approval gate; Rooms; peer notes; live WebSocket queues; Canvas launch/sync path; demo/community deployment modes; tests; evaluation reports; and defense documentation.

Out of scope: physical NFC/barcode/kiosk hardware, production Microsoft SSO without IT credentials, scraping the AUI portal, and claims of live AUI accuracy without validated human-labeled data. The project assumes access to a development machine, synthetic or curated training data, demo course materials, and supervisor feedback.

## 3. Related Work / Existing Solutions / State of the Art

Related work includes LMS office-hours tools, generic help-desk systems, academic question-answering tutors, retrieval-augmented chatbots, and queue-management platforms. These tools can support parts of the problem, but they often lack course-scoped AI triage, privacy-preserving student intake, professor-controlled publication of knowledge, and integrated TA staffing recommendations.

AI tutoring and RAG systems can provide quick answers, but many rely on uncurated corpora or external LLM calls and may not enforce a professor approval gate. Queue systems can order requests but typically do not detect repeated conceptual topics or recommend when a group review would be more effective. OfficeHours AI differentiates itself by combining local trained models, human oversight, professor-gated knowledge, and AUI-specific role-per-course semantics in one deployable workflow.

## 4. Gap, Innovation & Expected Contribution

### 4.1 Gap / Need Analysis

The main gap is not the absence of any communication tool; rather, it is the absence of a campus-ready system that organizes office-hours demand intelligently while preserving human academic relationships. Existing tools either manage queues without meaningful triage, answer questions without professor control, or use opaque external models that are difficult to evaluate responsibly in a capstone setting.

### 4.2 Core Contribution / Innovation

OfficeHours AI contributes an integrated, AI-assisted office-hours triage system with five core components: (1) Ask Triage agents for classification, routing, and guidance drafting; (2) Help Coach for TA support during sessions; (3) a professor-gated Study Agent; (4) Rooms and review insights for repeated topics; and (5) a Canvas/LTI-oriented deployment path. The innovation is the responsible integration of these parts into a campus workflow, not the claim of inventing embeddings, classifiers, or LMS protocols.

### 4.3 Value Proposition & Differentiation

## 5. Project Objectives & Success Criteria

### 5.1 Primary Objective

Design, build, and evaluate an AI-assisted campus office-hours triage system that reduces repeated faculty workload while improving student comfort and access to academic help.

### 5.2 Specific Objectives

1. Deliver a working multi-role OfficeHours AI web application for students, TAs, and professors with course-specific roles.

1. Implement Ask Triage using locally trained models to classify, route, and summarize incoming requests.

1. Provide Help Coach, professor knowledge-base approval, Study Agent, Rooms, peer notes, and Canvas launch/sync for a complete support loop.

1. Evaluate the system with functional tests, model reports, privacy checks, walkthroughs, and clearly stated limitations.

### 5.3 Success Criteria / Key Metrics

## 6. Methodology / Technical and Research Approach

The project follows iterative software prototyping with continuous evaluation. Each iteration connects a functional product increment to an evaluation artifact, such as a test suite result, model metric, or walkthrough. The architecture uses a React/Vite frontend, a FastAPI/Uvicorn backend, SQLAlchemy persistence, and a WebSocket hub for live TA queues. SQLite supports local development, while the design remains compatible with PostgreSQL for deployment.

### 6.1 AI-Agent Design and Decision-Support Policy

The AI layer is intentionally framed as assistance, not automation of academic judgment. The agents organize information, identify patterns, and propose actions; professors and TAs keep responsibility for communication and final decisions. This design choice supports responsible AI use and protects the social value of office hours.

### 6.2 Data, Training, and Reproducibility

Training and evaluation use synthetic and curated request examples, silver labels from project assumptions or TA-style heuristics, and held-out gold-label items when available. The project will clearly separate laboratory metrics from claims about real AUI deployment. Reproducibility will be supported through the GitHub repository, documented environment variables, demo scripts, and evaluation reports.

## 7. Evaluation & Validation Plan

Evaluation combines software validation, model evaluation, privacy checks, and product walkthroughs. The goal is to show that the system works end-to-end and that AI claims are reported honestly.

- Functional and integration tests for authentication, request intake, triage, TA staffing, knowledge-base approval, Rooms, Canvas launch, and WebSocket behavior.

- Analyzer and Matcher evaluation reports using cross-validation or held-out data, with clear labeling of synthetic, silver, and gold-label sources.

- Manual walkthroughs covering a Quiet ask, TA Help Coach support, professor approval, and Study Agent response from approved content only.

- Privacy checks ensuring Quiet asks do not expose student identity through status endpoints or staff views beyond authorized roles.

- Deployment checklist covering demo mode, community mode, Canvas/LTI keys, database configuration, and documented limitations.

Baselines will be described qualitatively: non-triaged queues, separate dashboards, LMS inbox messages, and ungated chatbot behavior. Acceptance requires a demoable product, passing tests, documented metrics, and honest limitation notes rather than over-claimed live-campus accuracy.

## 8. Expected Deliverables

## 9. Project Plan, Milestones & Timeline

### 9.1 Key Milestones

### 9.2 Detailed Timeline

### 9.3 Dependencies

- AUI IT support for production Canvas LTI keys and optional Microsoft Entra registration.

- Local or cloud compute resources for sentence-transformer and scikit-learn training/inference.

- Access to representative course materials for demo knowledge-base entries.

- Optional TA/student participation for human gold-label validation or walkthrough feedback.

- Supervisor feedback cycles to refine scope, evaluation, and defense positioning.

## 10. Resources & Budget

### 10.1 Required Resources

### 10.2 Budget

## 11. Potential Risks & Mitigation

## 12. Ethics, Privacy, Security, Standards & Responsible AI

## 13. References

1. OfficeHours AI Project. (2026). Product overview, glossary, architecture, and defense documentation. Al Akhawayn University FYP repository.

1. Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. EMNLP-IJCNLP.

1. Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825-2830.

1. FastAPI / Uvicorn documentation. (n.d.). https://fastapi.tiangolo.com/

1. React and Vite documentation. (n.d.). Meta / VoidZero open-source tooling.

1. 1EdTech. (n.d.). Learning Tools Interoperability (LTI) 1.3.

1. Instructure. (n.d.). Canvas LMS API and LTI documentation.

1. OfficeHours AI. (2026). Classifier, matcher, and gold-label evaluation reports. AUI FYP repository.

---

## Tables from the refined document

### Table 1
| Project Title | OfficeHours AI: A Multi-Role Campus Office-Hours Triage System with AI-Assisted Decision Support |
| --- | --- |
| Student Name | Sophia Abssi |
| Student ID | 117027 |
| Degree Program | Artificial Intelligence and Robotization |
| Supervisor | Dr. Oumaima Hourrane |
| Date of Submission | September 23, 2026 |

### Table 2
| Project Type |
| --- |
| Software development project: a web application with AI-assisted, locally trained decision-support agents. |

### Table 3
| Phase | Purpose | Main Activities |
| --- | --- | --- |
| 1. Problem Definition & Background | Define the finals-week communication overload problem and the research question. | Clarify stakeholders, scope, privacy concerns, and the role of OfficeHours AI as a decision-support system rather than a replacement for office hours. |
| 2. Investigation & Requirements | Study current LMS, ticketing, chatbot, and office-hours support approaches. | Compare Canvas inbox/tickets, generic helpdesks, AI tutors, and queue systems; define functional, privacy, and deployment requirements. |
| 3. Technical / Research Design | Design the multi-role architecture and AI-assisted workflow. | Specify student, TA, and professor roles; define Ask Triage agents; design the professor-approved knowledge base, Rooms, live queues, and Canvas/LTI integration path. |
| 4. Development & Experimentation | Build and refine the working prototype. | Implement the React/FastAPI application, local ML pipeline, Help Coach, Study Agent, WebSocket queues, database models, and demo/community deployment modes. |
| 5. Validation & Evaluation | Evaluate both software reliability and AI triage quality. | Run backend/frontend tests, measure classifier and matcher performance, validate privacy behavior for Quiet asks, and perform manual walkthroughs. |
| 6. Finalization & Communication | Prepare the project for presentation and handover. | Finalize documentation, defense materials, poster, deployment notes, and a reproducible demo script. |

### Table 4
| Criterion | Baseline / Existing Approach | OfficeHours AI Approach | Expected Difference |
| --- | --- | --- | --- |
| Triage quality | Manual email/inbox sorting or FIFO queues. | Local Ask Triage analyzes category, urgency, difficulty, repetition, and support mode. | More structured intake and better routing of repeated or urgent questions. |
| Human oversight | Chatbots may answer directly from broad or unapproved content. | Study Agent answers only from professor-approved knowledge; staff make final decisions. | AI assists decision-making without replacing academic interaction. |
| Privacy and comfort | Students may need to expose identity for every question. | Quiet Mode allows privacy-preserving asks and identity-safe status tracking. | Lower barrier for students who hesitate to ask for help. |
| Staff workload | Repeated questions are handled individually. | Clusters repeated topics and suggests group review or FAQ-style responses. | Reduced duplicate replies and improved use of office-hours time. |
| Deployment fit | Disconnected dashboards or ad-hoc tools. | Unified app with role per course and Canvas/LTI path. | Better fit for AUI course workflows and future campus rollout. |

### Table 5
| Objective / Claim | Metric or Evidence | Target / Acceptance Criterion |
| --- | --- | --- |
| Working multi-role product | Student, TA, and professor workspaces; product app and API running locally. | All three role flows are demoable end-to-end on a sample course. |
| Ask Triage quality | Analyzer, Matcher, and held-out evaluation reports. | Metrics are reported transparently with limits on synthetic, silver, and gold-label data. |
| Complete triage loop | Quiet ask, TA queue, Help Coach, professor KB approval, and Study Agent walkthrough. | Study Agent uses approved entries only; repeated topics can be clustered for review. |
| Engineering reliability | Automated tests and CI/product build evidence. | Backend tests pass; product build remains reproducible. |
| Privacy and responsible AI | Quiet-ask status checks, authorization tests, KB gate behavior. | Quiet identity is not exposed on status lookup; AI suggestions remain reviewable by humans. |

### Table 6
| Agent / Component | Role | Human Oversight |
| --- | --- | --- |
| Ask Analyzer | Classifies the student ask by topic, urgency, difficulty, and likely support need. | Its output is visible to staff and can be corrected or overridden. |
| Ask Matcher | Recommends a support path, such as TA handling, professor attention, group review, or FAQ drafting. | TAs and professors decide whether to accept the recommendation. |
| Response Synthesizer | Drafts teaching guidance or FAQ suggestions using approved material and retrieved context. | Drafts remain suggestions until reviewed or approved. |
| Help Coach | Assists TAs during sessions by suggesting Socratic prompts, clearer explanations, or safer replies. | The TA chooses what to say and remains responsible for the session. |
| Study Agent | Answers student questions only from professor-approved knowledge-base entries. | If approved material is missing, it should refuse or redirect instead of hallucinating. |

### Table 7
| Deliverable | Description / Acceptance Condition |
| --- | --- |
| Product application | Unified OfficeHours AI web app with student, TA, and professor experiences, accepted when the main role flows work end-to-end. |
| Backend platform | FastAPI services for Ask Triage, Help Coach, knowledge-base approval, Study Agent, Rooms, Canvas/LTI, and WebSockets, accepted when backend tests pass. |
| Trained models and evaluation reports | Analyzer/Matcher/Synthesizer artifacts and reports, accepted when metrics and limitations are documented. |
| Documentation and defense pack | Architecture, glossary, defense notes, security notes, and gold-label lab plan, accepted when a supervisor or examiner can understand and run the demo. |
| Demo and deployment assets | Run script, poster/presentation materials, and community deployment checklist for OFFICEHOURS_DEMO=false and Canvas/LTI setup. |

### Table 8
| Milestone | Target Date | Evidence of Completion |
| --- | --- | --- |
| Milestone 1: Approved problem scope and product vision | October 01, 2026 | Supervisor-approved research question, scope, and proposal. |
| Milestone 2: Ask Triage and unified app vertical slice | October 06, 2026 | Student request submission, triage output, and basic staff dashboard demoable. |
| Milestone 3: Help Coach, KB gate, Rooms, and Canvas path integrated | November 11, 2026 | Complete triage loop works in demo mode. |
| Milestone 4: Evaluation pack and defense materials | December 09, 2026 | Tests, reports, documentation, poster, and final presentation ready. |

### Table 9
| Phase | Major Tasks / Output | Start | End |
| --- | --- | --- | --- |
| Definition & Background | Finalize research question, scope, stakeholders, and privacy assumptions. | Sep 01, 2026 | Oct 01, 2026 |
| Investigation & Requirements | Compare baselines, define Canvas/LTI path, and lock dataset/evaluation assumptions. | Sep 15, 2026 | Oct 06, 2026 |
| Design / Research Design | Finalize database schema, API contracts, agent behavior, and UI flow. | Sep 20, 2026 | Oct 06, 2026 |
| Development & Experimentation | Implement main product features, trained models, Rooms, Canvas launch, and live queues. | Oct 06, 2026 | Nov 11, 2026 |
| Validation & Evaluation | Run tests, model evaluations, privacy checks, and product walkthroughs. | Nov 11, 2026 | Dec 01, 2026 |
| Finalization & Communication | Prepare defense documentation, poster, demo script, and deployment notes. | Dec 01, 2026 | Dec 09, 2026 |

### Table 10
| Resource | Purpose | Availability / Source |
| --- | --- | --- |
| Developer workstation or cloud VM | Development, local training, testing, and live demos. | Personal laptop; optional cloud VM if needed. |
| GitHub repository and CI | Version control, regression builds, and documentation. | Project repository. |
| Python 3.12 and Node.js toolchains | Backend FastAPI environment and frontend Vite/React build. | Open-source tools. |
| Canvas LMS with LTI 1.3 keys | Community deployment, course enrollments, module material sync, and signed launch. | AUI IT; demo mode removes this dependency during development. |
| Course materials / sample requests | Knowledge-base demos, training, and evaluation examples. | Synthetic, curated, and approved course material. |

### Table 11
| Item | Quantity | Unit Cost (MAD) | Total (MAD) | Justification |
| --- | --- | --- | --- | --- |
| Software stack | -- | 0 | 0 | React, FastAPI, sentence-transformers, scikit-learn, and related tools are open source. |
| Optional cloud compute | 1 | 0-500 | 0-500 | Only needed if local hardware is insufficient for training or demos. |
| Innovation Day poster printing | 1 | 150-400 | 150-400 | Physical academic poster for exhibition/presentation. |
| Estimated total | -- | -- | 0-900 | The core software project requires no mandatory direct expenditure. |

### Table 12
| Potential Risk | Likelihood | Impact | Mitigation / Fallback |
| --- | --- | --- | --- |
| Canvas or IT credentials are delayed. | Medium | High | Use OFFICEHOURS_DEMO=true and a documented Canvas launch simulator; prepare LTI setup steps for IT. |
| Model performance is over-claimed compared with real AUI text. | Medium | High | Report metrics honestly, separate synthetic/silver/gold data, and run a human gold-label lab if required. |
| Scope creep expands the project beyond the triage loop. | Medium | High | Keep hardware kiosk/NFC out of scope and prioritize Ask Triage, Help Coach, KB gate, Rooms, and Canvas path. |
| Quiet ask privacy is accidentally exposed. | Medium | High | Implement status redaction, authorization checks, dedicated tests, and a security review checklist. |
| AI suggestions are treated as authoritative answers. | Medium | Medium | Use visible human review, professor approval gates, refusal behavior, and clear UI language that labels outputs as suggestions. |

### Table 13
| Consideration | Project Response |
| --- | --- |
| Human participants / user studies | Optional walkthroughs or surveys with students/TAs will use informed consent and will not be linked to grades. Any new human gold-label lab will follow the same consent practice. |
| Privacy and personal data | The system may process emails, student IDs, and academic help text. Quiet Mode minimizes identity exposure; demo data is synthetic; PII is kept out of logs where possible; retention follows course-term needs rather than a permanent student archive. |
| Cybersecurity | Relevant threats include session theft, cross-course access, prompt injection, and malicious uploads. Mitigations include authorization checks, rate limiting, upload validation, secure session handling, and tests. |
| Legal / regulatory / licensing | Canvas and Microsoft API terms must be respected. Core dependencies are open source. Portal scraping is rejected in favor of standards-based LTI 1.3 integration. |
| Engineering standards | The project uses HTTP/JSON APIs, Canvas LTI 1.3, JWT/JWKS validation, documented environment variables, and OWASP-inspired hardening practices. |
| Responsible AI use | AI outputs are treated as suggestions, not final decisions. Critical outputs are reviewed by TAs or professors, Study Agent answers are restricted to approved materials, and model limitations are documented. |
| Accessibility and inclusion | Quiet Mode and clear role-based navigation support students who hesitate to ask directly. The UI should use accessible contrast, readable labels, and language appropriate for AUI instruction. |
