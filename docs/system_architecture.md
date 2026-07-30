# System Architecture

## Overview

OfficeHours AI is a **packaged multi-role campus application** for office-hours
triage at Al Akhawayn University.

Users enter via login or Canvas launch. **Course memberships** decide whether
they work as a student, TA, or professor for each course. The same person may
be a TA in one course and a student in another. Professors may teach multiple
courses; courses may have multiple TAs.

| Surface | Port (dev) | Who uses it |
| --- | --- | --- |
| **Unified product app** | `5180` | Students, TAs, professors (login + course switcher + Canvas demo) |
| Backend API | `8000` | Serves the product app |
| Legacy kiosk / dashboards | `5173–5175` | Optional older web shells (not hardware) |

See also: [`product_overview.md`](product_overview.md),
[`project_journey.md`](project_journey.md), [`training_data.md`](training_data.md).


## Components

1. **Product app** — login, course picker, student ask (identity + help mode), TA queue, professor command center, Canvas simulator
2. **Backend API** — auth, requests, Oracle pipeline, clustering, knowledge, Canvas launch/sync, TA roster, analytics, action plans, `.ics`
3. **Oracle AI layer (custom-trained)** — Analyzer / Matcher / Synthesizer (no prompted Claude on the FYP path)
4. **Canvas integration** — JIT launch provisioning + materials → course KB (LTI signatures still TODO for production)
5. **Action orchestration** — professor decisions → agenda / status / calendar plans

## Oracle data flow (current)

1. Student submits (`POST /requests/`) with optional identity + `help_mode`
2. **Analyzer** → category, urgency, difficulty, tags, ETA
3. **Matcher** → primary/alt TA + wait estimate
4. **Synthesizer** → student hint + teaching approach (or seek-help when KB is weak)
5. Meeting modes set/override `recommended_action` for staff scheduling
6. Backend clusters the request and seeds a `pending_review` knowledge draft
7. WebSocket `/ws` pushes live events to TA + professor workspaces
8. TA may use **Help Coach** (`POST /ta/assist/`) while helping — similar open
   asks, approved KB neighbors, Socratic steps, draft/rewrite reply, refresh
   teaching script — then edit/resolve notes (still `pending_review`)
9. Professor approves/edits/rejects KB entries — **only approved** answers reach `/agent/ask`
10. Student checks status by request code (privacy-safe)

## Diagrams

| File | What it shows |
| --- | --- |
| `diagrams/architecture.png` | Unified app + API + Canvas + three agents + curation |
| `diagrams/workflow.png` | Identity / help mode → Oracle → TA → professor → KB |
| `diagrams/oracle_agents.png` | Analyzer / Matcher / Synthesizer training artifacts |
| `diagrams/product_deployment.png` | Canvas-first community deploy vs alternatives |
| `diagrams/database_erd.png` | Auth, memberships, requests (`help_mode`), KB |
| `diagrams/canvas_enrollment.png` | JIT Canvas launch + TA-also-student |
| `diagrams/project_journey.png` | Day-1 → this upgrade timeline |

Regenerate:

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

## Tech stack rationale

- **FastAPI + SQLite** — fast local demo; `DATABASE_URL` can point at Postgres later
- **sentence-transformers (`all-MiniLM-L6-v2`) + scikit-learn** — trainable local models suitable for FYP constraints
- **React + Tailwind** — unified product UI (legacy three-app shells optional)
- **WebSockets** — live queue/curation without polling
- **External LLM disabled by default** (`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`)

## Production enrollment (decision)

**Primary:** Canvas LTI launch (course + role from LMS).  
**Not primary:** AUI portal / SIS sync.  
**Support only:** manual admin fixes.
