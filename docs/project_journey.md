# OfficeHours AI — project journey (day 1 → this upgrade)

Living history of the FYP product for Al Akhawayn University (AUI).
Use this with [`product_overview.md`](product_overview.md),
[`system_architecture.md`](system_architecture.md), and the
[`diagrams/`](../diagrams/) folder.

## One-sentence product today

**One campus web app** where a person signs in (or launches from Canvas), their
**role is per course** (a TA can also be a student elsewhere), they ask quietly
or identified, optionally request a face-to-face / online meeting, and custom
Ask Triage agents triage help under a professor KB gate.

---

## Timeline

### Phase 0 — Proposal (day 1)

| | |
| --- | --- |
| Intent | Cut finals-week overload; lower the barrier to ask for help |
| Scope | Prototype kiosk + dashboard + classify/cluster pipeline |
| Explicitly out of scope then | Full LMS/SIS integration, multi-language |
| Doc | [`proposal.md`](proposal.md) |

### Phase 1 — Backend + student kiosk MVP

- FastAPI request CRUD, health, SQLite
- Student kiosk (Vite/React/Tailwind): submit questions, barcode check-in prototype
- Synthetic finals-week dataset for early classifier work

### Phase 2 — Professor surface + first AI

- Professor dashboard MVP (triage, charts)
- Request classification + semantic clustering
- Recommendation cards, surveys, mid-report
- Action orchestration + office-hours persistence + `.ics` export
- Anonymous request status lookup

### Phase 3 — TA queue + knowledge + Ask Triage agents

- TA dashboard (live queue, draft edit, resolve)
- Knowledge-base curation (professor approve / edit / reject)
- Student KB agent over **approved** answers only
- Custom-trained **Ask Triage**: Analyzer → Matcher → Synthesizer (no prompted Claude on the FYP path)
- WebSocket live push across dashboards
- Architecture diagrams + training-data docs

### Phase 4 — One packaged product (not three URLs)

- Unified `frontend/officehours-app` (port **5180**)
- Login + `users` / `courses` / `course_memberships`
- Role is **never** in the email — only in the membership for the active course
- Legacy kiosk/dashboards kept for hardware experiments only

### Phase 5 — AUI realism + Canvas path

- AUI-style emails (`Initial.Lastname@aui.ma`) and catalog codes (`CSC 3374`, …)
- Demo undergrad load ~6–7 courses; Canvas course ids on tenants
- Canvas materials sync (live API or local mirror) into course-scoped KB
- Canvas launch simulator + `POST /canvas/launch` (JIT user/course/membership)
- Office-hours command center for professors; agent performance backlog

### Phase 6 — This upgrade (identity, meetings, deployment clarity)

| Decision / feature | What we shipped |
| --- | --- |
| **Quiet ask vs Identify me** | Students choose; anonymous strips identity; identified needs name/ID |
| **Help mode** | `message` · `face_to_face` · `online_meeting` → TA-facing recommended action |
| **TA is also a student** | Demo + Canvas simulator: same person, different roles per course |
| **Community deployment** | **Canvas LTI** is the recommended source of enrollments (not AUI portal scraping, not manual entry as the main path) |
| Docs / diagrams / demo | This journey doc + regenerated diagrams + dual-role demo accounts |

---

## How campus enrollment works (production recommendation)

```
AUI already uses Canvas
        │
        ▼
Student / TA / professor opens a Canvas course
        │
        ▼
Clicks “Open OfficeHours AI”  (real LTI next; demo launch today)
        │
        ▼
We learn: email · course · Canvas role
        │
        ▼
Auto-create account + course + membership (role for THAT course only)
        │
        ▼
Signed-in workspace for that role
```

| Option | Use for community deploy? |
| --- | --- |
| **Canvas LTI launch** | **Yes — primary.** Matches AUI teaching; roles/courses already there; materials sync shares the same LMS |
| AUI portal / SIS sync | No (unless IT forces it later). Slow; Canvas already mirrors enrollments |
| Manual typing each login | No as the main path. Thin admin escape hatch only |

**Important:** a TA is still a student. Role is per course — TA in CSC 2302 and student in MTH 1304 is normal and supported.

---

## What a supervisor demos now

1. `./scripts/run_product.sh` → http://127.0.0.1:5180  
2. Student `s.elidrissi@aui.ma` / `aui-demo` → Quiet ask or Identify me → message / face-to-face / online  
3. TA+student `a.chen@aui.ma` → TA workspace on CSC 2302; switch course picker to a student course  
4. Professor `a.benali@aui.ma` → command center, Canvas sync, approve KB  
5. Optional: `/canvas-demo` → launch as Karim (TA in OS, student in Data Structures)

Password for all seeded accounts: **`aui-demo`**.

Full account table: [`product_overview.md`](product_overview.md).

---

## Diagrams (regenerate after edits)

| File | Story |
| --- | --- |
| `diagrams/architecture.png` | Unified product app + API + Ask Triage + Canvas + curation |
| `diagrams/workflow.png` | Ask (identity + help mode) → Ask Triage → TA → professor → KB |
| `diagrams/oracle_agents.png` | Analyzer / Matcher / Synthesizer artifacts |
| `diagrams/product_deployment.png` | Canvas-first community deploy vs what we are not |
| `diagrams/database_erd.png` | Auth + memberships + requests (`help_mode`) + KB |
| `diagrams/canvas_enrollment.png` | JIT Canvas launch + dual-role (TA + student) |
| `diagrams/project_journey.png` | Phase timeline day 1 → this upgrade |

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

---

## Honest next steps (agents + production)

1. Replace unsigned `POST /canvas/launch` with **real Canvas LTI 1.3**  
2. Keep growing course KB from Canvas modules (agent quality ceiling)  
3. Retrain Analyzer / Matcher / Synthesizer on CSC-covered labels ([`agent_performance.md`](agent_performance.md))  
4. Optional tabular signals (learning style / stress) from external CSVs — bridge, not drop-in text training  

---

## Key paths in the repo

| Area | Path |
| --- | --- |
| Product UI | `frontend/officehours-app/` |
| Auth + memberships | `backend/app/models/auth.py`, `routes/auth.py` |
| Demo seed | `backend/app/services/demo_accounts.py` |
| Canvas launch | `backend/app/services/canvas_launch_service.py` |
| Ask + help mode | `backend/app/routes/requests.py` |
| Ask Triage pipeline | `backend/app/services/triage_service.py` |
| Run helper | `scripts/run_product.sh` |
