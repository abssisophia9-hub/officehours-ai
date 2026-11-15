# OfficeHours AI

Campus office-hours triage system for **Al Akhawayn University** (FYP).

Students, TAs, and professors use **one packaged web app**. Custom-trained
**Ask Triage** agents (Analyzer → Matcher → Synthesizer) classify each ask at
intake; **Help Coach** assists TAs while helping; the professor remains the
gate for what students can retrieve from the knowledge base.

> **Naming:** product docs say **Ask Triage**. Some API fields, DB columns, and
> the service module still use the historical prefix `oracle_*` /
> `oracle_service.py` — same pipeline.

## What is the final product?

A **multi-role campus application** with login (or Canvas launch):

- role is **per course** (a TA is staff on a course they already took)
- Quiet ask or Identify me; message / face-to-face / online meeting
- one workspace: `frontend/officehours-app` (port **5180**)

**Community deploy path:** Canvas LTI (not AUI portal scraping, not manual
enrollment as the main model). Physical kiosk / barcode / NFC hardware is
**out of scope**.

Start here:

- [`docs/product_overview.md`](docs/product_overview.md) — how to demo **and** how to deploy
- [`docs/glossary.md`](docs/glossary.md) — Ask Triage · Help Coach · **Rooms** · roles · status
- [`docs/fyp_evidence.md`](docs/fyp_evidence.md) — what to claim in a defense
- [`docs/README.md`](docs/README.md) — full documentation index
- [`docs/project_journey.md`](docs/project_journey.md) — day 1 → current product
- [`docs/system_architecture.md`](docs/system_architecture.md) — components + diagrams
- [`diagrams/`](diagrams/) — architecture / workflow / Canvas / journey PNGs

```bash
./scripts/run_product.sh
# → http://127.0.0.1:5180
# Demo walkthrough: OFFICEHOURS_DEMO=true (default in that script), password aui-demo
# Community deploy: OFFICEHOURS_DEMO=false + live Canvas credentials
```

### How to run on Windows (PowerShell)

Use **two** PowerShell windows from the **repo root**. Do not paste `uvicorn` or
`npm` flags by hand — the scripts set demo defaults.

**One-time setup** (if `backend\venv` or frontend `node_modules` are missing):

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cpu
.\venv\Scripts\pip install -r requirements.txt
cd ..\frontend\officehours-app
npm ci
cd ..\..
```

**Every time you run the product:**

```powershell
# Terminal 1 — API  →  http://127.0.0.1:8000
.\scripts\start-backend.ps1

# Terminal 2 — product app  →  http://127.0.0.1:5180
.\scripts\start-frontend.ps1
```

`start-backend.ps1` sets `OFFICEHOURS_DEMO=true` and lexical clustering when
unset, then runs `backend\venv\Scripts\uvicorn.exe`. `start-frontend.ps1` only
`Set-Location`s to `frontend\officehours-app` and runs `npm run dev` (Vite
port **5180**). Open http://127.0.0.1:5180 — demo login password **`aui-demo`**.
`tzdata` is in `backend/requirements.txt` so `ZoneInfo("America/Los_Angeles")`
works on Windows after a fresh `pip install -r requirements.txt`.

## Agents (custom-trained)

| Surface | When it runs | Agents / modes |
| --- | --- | --- |
| **Ask Triage** | `POST /requests/` (intake) | Analyzer → Matcher → Synthesizer |
| **Help Coach** | `POST /ta/assist/` (while helping) | draft reply · Socratic · refresh script · rewrite |
| **Study Agent** | `POST /agent/ask` | Approved KB only (professor gate) |

| Ask Triage agent | Model | Training data |
| --- | --- | --- |
| Analyzer | embeddings + LogReg | Labeled synthetic + CSC / multi-dept rows |
| Matcher | embeddings + LogReg | Silver TA labels + supplements |
| Synthesizer | RAG + style ranker | Teaching-bank + supplements |

No prompted Claude / no `USE_MOCK_CLAUDE` on the assessed path. Details:
[`docs/training_data.md`](docs/training_data.md),
[`docs/agent_performance.md`](docs/agent_performance.md).

## Problem

Finals week floods faculty with repeated questions while some students hesitate
to ask for help.

## Solution highlights

- Anonymous or identified asks; message / face-to-face / online preference
- Live WebSocket queues (signed in + subscribed to one course)
- Ask Triage at intake + Help Coach while TAs help
- TA staffing loop (claim → help → reply / group meeting → curation)
- Shared **group meetings** for repeated clusters (same time/place on every
  student’s request status)
- Professor-approved knowledge base + student Study Agent
- **Rooms** — course-scoped classmate forum (Problem / Discussion / Article),
  Canvas-module chapters, named helpers on a Hilbert-weighted leaderboard
- Classmate peer notes (study feed — does not train the agent)
- Account menu: tour, report bug/issue (`POST /feedback/bugs`), log out
- Canvas materials sync + launch provisioning (LTI hardening next)

## Tech stack

- React + Tailwind — **product app `5180`** (legacy web shells: kiosk `5173`,
  professor `5174`, TA `5175`)
- FastAPI + SQLAlchemy + SQLite
- sentence-transformers + scikit-learn
- WebSockets for live push

## Cloud / agent operators

See [`AGENTS.md`](AGENTS.md) for how to run backend tests and frontends in this
environment (`OFFICEHOURS_CLUSTERING_BACKEND=lexical` for tests).
