# OfficeHours AI

Campus office-hours help for **Al Akhawayn University** (FYP).

During finals week, the same questions flood faculty while some students never
ask. OfficeHours AI is one login for students, TAs, and professors. Role is
**per course**. Custom **Ask Triage** classifies each ask at intake; TAs get
**Help Coach** while helping; professors stamp what the Study Agent may quote.

Start here: [`docs/product_overview.md`](docs/product_overview.md) ·
[`docs/glossary.md`](docs/glossary.md) · [`docs/README.md`](docs/README.md) ·
[`docs/SECURITY.md`](docs/SECURITY.md)

```bash
./scripts/run_product.sh
# → http://127.0.0.1:5180  (API on :8000)
# Local default: OFFICEHOURS_DEMO=true, password aui-demo
# Hosted / community: OFFICEHOURS_DEMO=false + live Canvas
```

## Roles (what each does today)

| Role | Surfaces |
| --- | --- |
| **Student** | Ask for help · My asks · Study Agent · Pedagogy Agent (with web Resources) · Rooms · Classmate notes · Inbox |
| **TA** | Dashboard · Live Queue with Help Coach · Past asks · reply required before resolving |
| **Professor** | Material approval · Your desk · Insights · Team |

## Agents

| Agent | What it does | How it is built | Sees | Must not | Enforced |
| --- | --- | --- | --- | --- | --- |
| **Ask Triage** | At ask submit: Analyzer → Matcher → Synthesizer | Trained local models (`backend/models/*.joblib`: embeddings + logistic regression; Synthesizer also RAG over the teaching bank). Default path is local — not a prompted Claude chat. Legacy Claude helpers remain in-tree for gated/optional paths only. | Ask text, course, roster context | Invent grades or publish KB answers | `ask_triage_service.py`; see [`docs/training_data.md`](docs/training_data.md), [`docs/fyp_evidence.md`](docs/fyp_evidence.md) |
| **Help Coach** | While a TA is helping: similar opens, KB neighbors, teaching script, Socratic steps, draft/rewrite reply | **Retrieval** over a **68-row** curated teaching bank (+ approved KB). **Not trained.** A separate style classifier (`synthesizer_ranker.joblib`) may cue learning style upstream; coach suggestions themselves are bank/KB retrieval and templates — no LLM. | Claimed ask, triage fields, approved KB | Answer the student as course truth; publish without the TA | `help_coach_service.py` / `synthesizer_model.py`; [`docs/training_data.md`](docs/training_data.md) |
| **Study Agent** | Answers from stamped course material | Retrieval over professor-approved KB; optional external **Gemini** (or Claude) quote/entailment check only when demo + LLM flags allow | Approved chunks + question | Quote unstamped material; invent answers when weak | Professor Material stamp; `agent_policy.py` / Orchestration Layer; [`docs/AGENT_POLICY.md`](docs/AGENT_POLICY.md), [`docs/fyp_evidence.md`](docs/fyp_evidence.md) |
| **Pedagogy Agent** | Short focus plan from practice scores; web Resources | Rule plan + optional **Gemini** think/rank when allowed; Resources use Wikipedia / trusted search + **YouTube** when keyed | Practice scores, preferences, syllabus-ish topics — not real grades or names | Store or send real grades/names | `revision_service.py` / `revision_search.py`; demo/LLM gates |

## Run locally

**Product app only:** `frontend/officehours-app` (port **5180**).  
Folders `frontend/student-kiosk/`, `frontend/professor-dashboard/`, and
`frontend/ta-dashboard/` are **legacy** milestone shells — not the product CI
target.

### Windows (PowerShell), from repo root

```powershell
# Terminal 1 — API → http://127.0.0.1:8000
.\scripts\start-backend.ps1

# Terminal 2 — app → http://127.0.0.1:5180
cd frontend\officehours-app
npm run dev
```

(`.\scripts\start-frontend.ps1` also only runs `npm run dev` from that folder.)

One-time: create `backend\venv`, install CPU PyTorch then `requirements.txt`,
`npm ci` in `frontend\officehours-app`. See [`docs/DEMO.md`](docs/DEMO.md).

### Demo accounts (`OFFICEHOURS_DEMO=true`)

Password for all: **`aui-demo`**

| Who | Email |
| --- | --- |
| Student (Sara) | `s.elidrissi@aui.ma` |
| TA (Alice) | `a.chen@aui.ma` |
| Professor (Benali) | `a.benali@aui.ma` |

Full table: [`docs/product_overview.md`](docs/product_overview.md).

### Backend `.env` (names only)

Copy `backend/.env.example` → `backend/.env`. Common names:

- `OFFICEHOURS_DEMO`, `OFFICEHOURS_CLUSTERING_BACKEND`
- `CANVAS_BASE_URL`, `CANVAS_API_TOKEN` (never commit real values)
- `GEMINI_API_KEY`, optional `PEDAGOGY_GEMINI_API_KEY`, `YOUTUBE_API_KEY`
- LLM gates: `OFFICEHOURS_LLM_ENABLED`, `OFFICEHOURS_ALLOW_EXTERNAL_LLM`,
  `OFFICEHOURS_LLM_PROVIDER`, `OFFICEHOURS_GEMINI_FREE_TIER_ACK`

Frontend: `VITE_API_BASE` (see `frontend/officehours-app/.env.example`).

**Without API keys:** Ask Triage / Help Coach stay local. Study Agent uses
retrieval-only (no external check). Pedagogy falls back to the rule plan;
Resources may be empty (or keyless Wikipedia/trusted articles only).

## Modes

| | Local FYP (`OFFICEHOURS_DEMO=true`) | Hosted / community (`false`) |
| --- | --- | --- |
| Default | `./scripts/run_product.sh` and `.env.example` | Host injects `OFFICEHOURS_DEMO=false` |
| People / chapters | Demo seed + sample syllabus | Canvas / LTI provision; no hardcoded catalog |
| External Gemini | Allowed only when LLM flags + key + free-tier ack are set | **Blocked** (`ALLOW_EXTERNAL_LLM` requires demo) |
| Canvas | Optional local mirror if live token absent | Live `CANVAS_BASE_URL` + `CANVAS_API_TOKEN` |

**Canvas LTI 1.3** code is in (`/lti/login`, `/lti/launch`). Production needs a
Canvas developer key + API token from IT — unsigned `/canvas-demo` is demo-only.
See [`docs/canvas_live_test.md`](docs/canvas_live_test.md).

Outbound hosts when enabled: Gemini
(`generativelanguage.googleapis.com`), YouTube Data API
(`googleapis.com/youtube`), Wikipedia, DuckDuckGo Instant Answer, Canvas REST,
optional Anthropic / Microsoft login.

## Limits

- Not load-tested at real campus scale.
- YouTube and Gemini quotas are the first ceilings.
- Course sections follow Canvas courses.
- Help Coach suggests teaching approaches; it does **not** answer course
  questions for the student.

Measured notes: Project evidence pack `docs/evidence/README.md` and
`docs/evidence/scaling-design.md` · in-repo
[`docs/fyp_evidence.md`](docs/fyp_evidence.md) ·
[`docs/ops_scale.md`](docs/ops_scale.md).

## Repo map

| Path | Role |
| --- | --- |
| `backend/` | FastAPI API, models, Ask Triage / Help Coach / Study / Pedagogy |
| `frontend/officehours-app/` | Product UI (React + Vite; Tailwind CSS v4 via Vite plugin) |
| `frontend/student-kiosk/`, `professor-dashboard/`, `ta-dashboard/` | Legacy shells |
| `docs/` | Product + defense docs |
| `scripts/run_product.sh` | One-command local demo |
| `data/` | Training CSVs / teaching bank (68 synthesizer rows) |

Classic `tailwind.config.js` exists only under legacy `student-kiosk`; the
product app uses `@tailwindcss/vite`.

## Tests

```bash
# Backend (from backend/)
OFFICEHOURS_CLUSTERING_BACKEND=lexical DATABASE_URL=sqlite:///:memory: \
  venv/bin/python -m pytest

# Product app (from frontend/officehours-app/)
npm ci && npm run build
```

CI builds **only** the backend and `officehours-app`. Cloud operators:
[`AGENTS.md`](AGENTS.md). Security checklist: [`docs/SECURITY.md`](docs/SECURITY.md).
