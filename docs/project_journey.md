Historical document, written for an earlier version of the product (the Revision Strategist is now the Pedagogy Agent)

# OfficeHours AI — project journey (day 1 → this upgrade)

Living history of the FYP product for Al Akhawayn University (AUI).
Use this with [`product_overview.md`](product_overview.md),
[`system_architecture.md`](system_architecture.md), and the
[`diagrams/`](../diagrams/) folder.

## One-sentence product today

**One campus web app** where a person signs in (or launches from Canvas), their
**role is per course** (a TA is staff on a course they already took), they ask quietly
or identified, optionally request a face-to-face / online meeting, and
**Ask Triage** agents help under a professor KB gate — with **Help Coach** for
TAs, **Rooms** for named classmate help, and **shared group meetings** for
repeated concepts.

Vocabulary: [`glossary.md`](glossary.md).

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
- Student kiosk (Vite/React/Tailwind): submit questions, optional typed ID check-in
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
- Legacy kiosk/dashboards kept as older web shells only (**no** physical
  hardware / barcode / NFC path)

### Phase 5 — AUI realism + Canvas path

- AUI-style emails (`Initial.Lastname@aui.ma`) and catalog codes (`CSC 3374`, …)
- Demo undergrad load ~6–7 courses; Canvas course ids on tenants
- Canvas materials sync (live API or local mirror) into course-scoped KB
- Canvas launch simulator + `POST /canvas/launch` (JIT user/course/membership)
- Office-hours command center for professors; agent performance backlog

### Phase 6 — Identity, meetings, deployment clarity

| Decision / feature | What we shipped |
| --- | --- |
| **Quiet ask vs Identify me** | Students choose; anonymous strips identity; identified needs name/ID |
| **Help mode** | `message` · `face_to_face` · `online_meeting` → TA-facing recommended action |
| **TA is staff** | Assigned to a course they already took — not a classmate in that section |
| **Community deployment** | **Canvas LTI** is the recommended source of enrollments (not AUI portal scraping, not manual entry as the main path) |
| Docs / diagrams / demo | Journey doc + diagrams + per-course role demo accounts |

### Phase 7 — TA staffing, Help Coach, peer notes, shared meetings

| Decision / feature | What we shipped |
| --- | --- |
| **TA staffing loop** | Claim → start helping → reply / done → backup handoff → curation |
| **Help Coach** | `POST /ta/assist/` — similar opens, KB neighbors, Socratic, draft/rewrite |
| **Shared group meetings** | One cluster meeting (title/when/place) on every linked request status |
| **Classmate notes** | Peer upload/like/comment/download under Study Agent (not agent training) |
| **Account menu** | Tour, report bug/issue (`POST /feedback/bugs`), log out |

### Phase 8 — Course community + professor review insights

| Decision / feature | What we shipped |
| --- | --- |
| **Course community (not a live chat)** | `/student/room` — first as threads, then as a classmate forum |
| **Staff stay out of the room** | Students post/reply; professors get `GET /analytics/review-insights` |
| **Review insights** | Question board: emphasize / covered / next-cohort note / draft FAQ |

### Phase 9 — Rooms as an AUI Stack Overflow hybrid

| Decision / feature | What we shipped |
| --- | --- |
| **Typed rooms** | Problem / Discussion / Article + Open/Solved + Express Interest |
| **Named helpers** | No hide-my-name in Rooms. Hilbert Weight ŵ / Node Points / podium ranks. Quiet ask stays the anonymous path to staff. |
| **Chapters from Canvas** | Production grid = Canvas modules. Sample CSC/MTH outlines only if `OFFICEHOURS_DEMO=true`. |
| **Demo gate** | `OFFICEHOURS_DEMO` seeds Sara/Youssef and the local Canvas mirror. Community deploy leaves it off. |

### Phase 10 — Opening story, Microsoft SSO, signed Canvas LTI (29–30 Aug 2026)

Full chit-chat (every request, rejection, and IT ask):  
[`session_log_opening_auth_canvas.md`](session_log_opening_auth_canvas.md).

| Decision / feature | What we shipped |
| --- | --- |
| **Opening is community, not the agent** | Headline: choose how you get help and how you give it. Rooms + Hilbert ŵ + help-or-ignore first. |
| **Hard chapter cuts** | User rejected gradients. Solid cream/white/lime/forest blocks + forest 01–05 bands. |
| **Illustrated journey** | Alone at 2:13 AM → shared at 2:31 AM. Quiet vs named, TA + agent, professor as guide. |
| **Microsoft Entra ID** | `/auth/microsoft/login` → AUI tenant picker → `/sso`. Waiting on IT app registration. |
| **Canvas LTI 1.3** | `/lti/login` + `/lti/launch`. Unsigned `/canvas/launch` and `/canvas-demo` **off** when not demo. |
| **CI housekeeping** | `nanoid` 3.3.18 in all four frontend lockfiles; drop unused Three.js/Recharts from the unified app. |

---

## How campus enrollment works (production recommendation)

```
AUI already uses Canvas
        │
        ▼
Student / TA / professor opens a Canvas course
        │
        ▼
Clicks “Open OfficeHours AI”  (signed LTI 1.3 when IT installs the tool; `/canvas-demo` only if `OFFICEHOURS_DEMO=true`)
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

1. `./scripts/run_product.sh` → http://127.0.0.1:5180 (landing path, then Sign in)  
2. Student `s.elidrissi@aui.ma` / `aui-demo` → Quiet ask or Identify me → message / face-to-face / online  
3. TA+student `a.chen@aui.ma` → TA workspace on CSC 2302; switch course picker to a student course  
4. Student Rooms (`/student/room` on CSC 3323) → Create a Room, Express Interest, leaderboard (named)  
5. Professor `a.benali@aui.ma` → command center, Canvas sync, approve KB, review insights  
6. Optional: `/canvas-demo` → launch as Karim (TA in OS, student in Data Structures)

Password for all **demo** accounts (`OFFICEHOURS_DEMO=true`): **`aui-demo`**.

Full account table: [`product_overview.md`](product_overview.md).

---

## Diagrams (regenerate after edits)

| File | Story |
| --- | --- |
| `diagrams/architecture.png` | Unified product app + API + Ask Triage + Canvas + curation |
| `diagrams/workflow.png` | Ask (identity + help mode) → Ask Triage → TA → professor → KB |
| `diagrams/oracle_agents.png` | Ask Triage Analyzer / Matcher / Synthesizer artifacts (filename historical) |
| `diagrams/product_deployment.png` | Canvas-first community deploy vs what we are not |
| `diagrams/database_erd.png` | Auth + memberships + requests (`help_mode`) + KB |
| `diagrams/canvas_enrollment.png` | JIT Canvas launch + per-course role (TA is staff) |
| `diagrams/project_journey.png` | Phase timeline day 1 → this upgrade |

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

---

## Honest next steps (agents + production)

Defense claims / ceilings: [`fyp_evidence.md`](fyp_evidence.md).

1. **AUI IT:** Microsoft Entra app registration (client id, secret, redirect URI) and Canvas LTI 1.3 developer key + API token. Code is ready; credentials are not.  
2. Optional: collect held-out TA **gold labels** when a lab is available  
3. Host the SPA with a real `VITE_API_BASE` / reverse proxy, favicon, and `OFFICEHOURS_DEMO=false`  
4. Retrain Analyzer / Matcher / Synthesizer on CSC-covered labels ([`agent_performance.md`](agent_performance.md))  
5. Optional tabular signals (learning style / stress) from external CSVs — bridge, not drop-in text training  

New campus surveys are **not required** for the capstone presentation.

---

## Key paths in the repo

| Area | Path |
| --- | --- |
| Product UI | `frontend/officehours-app/` |
| Auth + memberships | `backend/app/models/auth.py`, `routes/auth.py` |
| Demo seed | `backend/app/services/demo_accounts.py` (`OFFICEHOURS_DEMO`) |
| Demo switch | `backend/app/services/demo_mode.py` |
| Rooms | `backend/app/services/help_room_service.py`, `room_chapters.py` |
| Canvas launch | `backend/app/services/canvas_launch_service.py` |
| Ask + help mode | `backend/app/routes/requests.py` |
| Ask Triage (`ask_triage_service.py`, historically `oracle_service.py`) | `backend/app/services/ask_triage_service.py` |
| Help Coach | `backend/app/services/help_coach_service.py` |
| Run helper | `scripts/run_product.sh` |
