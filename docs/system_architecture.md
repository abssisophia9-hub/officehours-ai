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

Vocabulary: [`glossary.md`](glossary.md) · demo: [`product_overview.md`](product_overview.md) ·
history: [`project_journey.md`](project_journey.md) · training: [`training_data.md`](training_data.md).

## Components

1. **Product app** — login, course picker, student ask (identity + help mode +
   status lookup), Study Agent, Stuck Room, classmate notes, TA queue + Help Coach,
   professor command center + review insights, Canvas simulator, account menu
2. **Backend API** — auth, requests, Ask Triage pipeline, Help Coach, clustering,
   knowledge, peer notes, help-room, Canvas launch/sync, TA roster/staffing, analytics,
   action plans / group meetings, feedback, `.ics`
3. **Ask Triage AI (custom-trained)** — Analyzer / Matcher / Synthesizer at
   intake (implementation: `oracle_service.py` / `oracle_*` fields)
4. **Help Coach AI** — TA mid-session assist (`help_coach_service.py`)
5. **Canvas integration** — JIT launch provisioning + materials → course KB
   (LTI signatures still TODO for production)
6. **Action orchestration** — cluster group meetings + agenda / status / calendar

## End-to-end data flow (current)

1. Student submits (`POST /requests/`) with optional identity + `help_mode`
2. **Ask Triage Analyzer** → category, urgency, difficulty, tags, ETA
3. **Matcher** → primary/alt TA + wait estimate
4. **Synthesizer** → student hint + teaching approach (or seek-help when KB is weak)
5. Meeting modes set/override `recommended_action` for staff scheduling
6. Backend clusters the request and seeds a `pending_review` knowledge draft
7. WebSocket `/ws` pushes live events to TA + professor workspaces
8. TA staffing: claim → start helping → (message reply **or** in-person /
   online help). **Help Coach** (`POST /ta/assist/`) assists while helping
9. Repeated clusters: TA or professor proposes one **shared group meeting**
   (`meeting_title` / `meeting_when` / `meeting_place` on a `group_session`
   decision) → every linked request status shows the same time/place
10. TA may resolve teaching notes → still `pending_review`
11. Professor approves/edits/rejects KB — **only approved** answers reach
    `/agent/ask` (Study Agent)
12. Student checks status by request code (reply and/or group meeting)

## Diagrams

| File | What it shows |
| --- | --- |
| `diagrams/architecture.png` | Unified app + API + Canvas + agents + curation |
| `diagrams/workflow.png` | Identity / help mode → Ask Triage → TA → professor → KB |
| `diagrams/oracle_agents.png` | Analyzer / Matcher / Synthesizer training artifacts |
| `diagrams/product_deployment.png` | Canvas-first community deploy vs alternatives |
| `diagrams/database_erd.png` | Auth, memberships, requests (`help_mode`, work_status), KB |
| `diagrams/canvas_enrollment.png` | JIT Canvas launch + TA-also-student |
| `diagrams/project_journey.png` | Day-1 → current product timeline |

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
