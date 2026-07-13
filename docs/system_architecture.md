# System Architecture

## Overview

OfficeHours AI is a **packaged multi-role campus application** for finals-week
office-hours triage at Al Akhawayn University.

Users log in once. **Course memberships** decide whether they work as a student,
TA, or professor for each course. Professors may teach multiple courses; courses
may have multiple TAs; students may enroll in several courses and switch context.

| Surface | Port (dev) | Who uses it |
| --- | --- | --- |
| **Unified product app** | `5180` | Students, TAs, professors (login + course switcher) |
| Backend API | `8000` | Serves the product app |
| Legacy kiosk / dashboards | `5173–5175` | Optional hardware/experiment shells |

See also: [`product_overview.md`](product_overview.md), [`training_data.md`](training_data.md).


## Components

1. **Student Kiosk** — barcode/manual check-in, anonymous/identified submit, status lookup, approved-KB agent chat
2. **Professor Dashboard** — live triage, Oracle metrics, KB curation gate, heatmap, escalations, office hours, recommendations
3. **TA Dashboard** — live queue, edit teaching draft / hint, resolve → `pending_review`
4. **Backend API** — requests, Oracle pipeline, clustering, knowledge, TA roster, analytics, action plans, `.ics`
5. **Oracle AI layer (custom-trained)** — Analyzer / Matcher / Synthesizer (no prompted Claude on the FYP path)
6. **Action orchestration** — professor decisions → agenda / status / calendar plans

## Oracle data flow (current)

1. Student submits on the kiosk (`POST /requests/`)
2. **Analyzer** (fine-tuned classifier) → category, urgency, difficulty, tags, ETA
3. **Matcher** (fine-tuned TA assigner) → primary/alt TA + wait estimate
4. **Synthesizer** (RAG + style ranker) → student hint + teaching approach
5. Backend also clusters the request and seeds a `pending_review` knowledge draft
6. WebSocket `/ws` pushes live events to professor + TA dashboards (no refresh required)
7. TA may edit/resolve notes (still `pending_review`)
8. Professor approves/edits/rejects KB entries — **only approved** answers reach `/agent/ask`
9. Professor may approve recommendation cards → action plans + optional `.ics`
10. Student checks status by request code (privacy-safe)

## Diagrams

| File | What it shows |
| --- | --- |
| `diagrams/architecture.png` | Three apps + API + three custom agents + curation gate |
| `diagrams/workflow.png` | End-to-end Oracle → TA → professor → student KB flow |
| `diagrams/oracle_agents.png` | Analyzer / Matcher / Synthesizer training artifacts |
| `diagrams/product_deployment.png` | What the final product is / is not |
| `diagrams/database_erd.png` | SQLite entities including KB + TA roster + Oracle fields |

Regenerate:

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

## Tech stack rationale

- **FastAPI + SQLite** — fast local demo; `DATABASE_URL` can point at Postgres later
- **sentence-transformers (`all-MiniLM-L6-v2`) + scikit-learn** — trainable local models suitable for FYP constraints
- **React + Tailwind** — three focused UIs (kiosk / professor / TA)
- **WebSockets** — live queue/curation without polling
- **External LLM disabled by default** (`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`)
