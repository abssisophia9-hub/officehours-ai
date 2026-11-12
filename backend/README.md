# OfficeHours AI — Backend

FastAPI backend for the OfficeHours AI product (Ask Triage + Help Coach + KB).

> **Naming:** docs and code both say **Ask Triage** for the intake pipeline.
> The implementation module is `app/services/ask_triage_service.py` and
> columns/fields use the `triage_*` prefix (renamed from historical `oracle_*`).

## Ask Triage pipeline (custom-trained models)

On `POST /requests/`, the backend runs **local trained models only** (FYP path —
no prompted Claude calls, no `USE_MOCK_CLAUDE` mocks):

1. **Analyzer** — fine-tuned small classifier (embeddings + logistic regression)
   (`OFFICEHOURS_ANALYZER_BACKEND=ml`). Produces category, difficulty, tags,
   estimated minutes. Train: `python3 scripts/train_classifier.py`
2. **Matcher** — trained TA assignment classifier + queue-depth penalty.
   Train: `python3 scripts/train_matcher.py`
3. **Synthesizer** — RAG over curated teaching bank / professor-approved KB +
   trained learning-style ranker (no LLM). Train: `python3 scripts/train_synthesizer.py`

Professor curation remains the gate: TA resolve → `pending_review` → professor
approve → student Study Agent / lifetime confusion agent.

## Help Coach (TA mid-session)

`POST /ta/assist/` — modes: `draft_reply` | `socratic` | `refresh_teaching` |
`rewrite_reply`. Same local RAG stack; oriented for TAs while helping.
See `app/services/help_coach_service.py`.

## Setup

Copy [`backend/.env.example`](.env.example) for community deploy variables.
Security baseline: [`docs/SECURITY.md`](../docs/SECURITY.md).

```bash
cd backend
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run the dev server

```bash
uvicorn app.main:app --reload
```

Visit:

- API root: http://127.0.0.1:8000/
- Interactive docs (Swagger UI): http://127.0.0.1:8000/docs

## Core API endpoints

### Auth / Canvas

- `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- `GET /auth/config` — `{ demo, canvas_mode }` (no auth; login UI hides demo chips when false)
- `GET /courses/mine`, `GET /courses/`
- `POST /canvas/launch` — JIT provision user/course/membership (demo unsigned)

### Requests / status

- `POST /requests/` — Ask Triage + cluster + pending KB draft
- `GET /requests/`, `GET /requests/{id}`
- `GET /requests/{id}/status` — privacy-safe status (TA reply **or** shared
  group meeting fields: `meeting_title`, `meeting_when`, `meeting_place`)
- `GET|POST /requests/{id}/study-buddy` — solidarity opt-in

### TA staffing + Help Coach

- `GET /ta/queue/?course_id=` — auth; includes `help_coach` payload
- `GET /ta/load/?course_id=` — dual-TA depths
- `GET /ta/roster/`
- `POST /ta/claim/`, `/ta/work-status/`, `/ta/take-backup/`, `/ta/reply/`
- `POST /ta/assist/` — Help Coach
- `POST /ta/resolve/` — teaching draft → `pending_review`

### Knowledge / Study Agent / peer notes

- `GET|PATCH /knowledge/…`, `POST /knowledge/from-cluster`, materials upload,
  Canvas sync / status routes
- `POST /agent/ask` — approved KB only
- `GET|POST /peer-notes/…` — classmate notes (like / comment / download; not agent training)

### Rooms (classmate forum)

- `GET /help-room/community/?course_id=` — pulse + chapter grid (`chapter_source`)
- `GET|POST /help-room/` — rooms (named; `anonymous` is ignored)
- `POST /help-room/{id}/vote`, `/interest`, `/files`
- `POST /help-room/{id}/replies`, `/replies/{id}/helpful`, `/replies/{id}/accept`
- `GET /help-room/profile/{user_id}`, `GET /help-room/ranks/`
- Chapters: live Canvas modules, or demo syllabus if `OFFICEHOURS_DEMO=true`

### Actions / meetings / analytics / feedback

- `POST /actions/recommendations/` — optional `meeting_title|when|place` for
  shared cluster group meetings
- `GET /actions/recommendations/`, `…/calendar.ics`
- `GET /office-hours/`, `POST /office-hours/`, `DELETE /office-hours/{id}`
- Analytics: `GET /analytics/triage-metrics`,
  `/lifetime-confusion`, `/clusters`, `/struggle-heatmap`, `/escalations`,
  `/kb-hit-rate`, gold-labels `GET|POST`
- `POST /feedback/bugs` — account-menu bug/issue reports
- `WS /ws` — live events (`request.created`, `triage.*.done`, `ta.*`,
  `group.meeting.scheduled`, `knowledge.*`, …)

Full interactive catalog: http://127.0.0.1:8000/docs

## Clustering configuration

Request clustering uses `sentence-transformers` embeddings by default.

Optional environment variables:

- `OFFICEHOURS_EMBEDDING_MODEL` — defaults to `all-MiniLM-L6-v2`
- `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` — defaults to `0.72`
- `OFFICEHOURS_CLUSTERING_BACKEND=lexical` — lightweight backend for tests
- `OFFICEHOURS_ANALYZER_BACKEND=ml|rules` — defaults to `ml` on Ask Triage path
- `OFFICEHOURS_CLASSIFIER_BACKEND=rules|ml` — used by standalone classify helpers
- `OFFICEHOURS_CLASSIFIER_MODEL`, `OFFICEHOURS_MATCHER_MODEL`,
  `OFFICEHOURS_SYNTHESIZER_MODEL`, `OFFICEHOURS_TEACHING_BANK`,
  `OFFICEHOURS_LEARNING_STYLE_BACKEND`, `OFFICEHOURS_LEARNING_STYLE_MODEL`
- `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` — FYP default
- `OFFICEHOURS_DEMO=true|false` — seed Sara/Youssef + sample chapter outlines +
  local Canvas mirror. **False for community deploy.**
- `OFFICEHOURS_FRONTEND_URL` / `OFFICEHOURS_CORS_ORIGINS` — CORS allow-list
  (no `*`). WebSocket `/ws?token=&course_id=` is course-scoped.
- `OFFICEHOURS_RATE_LIMIT=false` — tests only; leave on for a host.
- `DATABASE_URL` — SQLite default; `postgresql://…` for campus (pool +
  `psycopg2`). See `docs/ops_scale.md`.
- `OFFICEHOURS_SMTP_*` — optional email when a TA claims / replies.
- `OFFICEHOURS_ALLOW_RETRAIN=true` — required before `POST /analytics/retrain`
  may rewrite Analyzer `.joblib`.
- `OFFICEHOURS_CANVAS_MODE=live|local|none` — optional override; live wins when
  `CANVAS_BASE_URL` + `CANVAS_API_TOKEN` are set

## Microsoft Entra ID sign-in (AUI accounts)

`Sign in with your AUI Microsoft account` appears on the login page once these
are set (get them from an Azure **App registration** in the AUI tenant):

- `OFFICEHOURS_MS_TENANT_ID` — AUI directory (tenant) ID
- `OFFICEHOURS_MS_CLIENT_ID` — Application (client) ID
- `OFFICEHOURS_MS_CLIENT_SECRET` — client secret value
- `OFFICEHOURS_MS_REDIRECT_URI` — must exactly match the registration's
  **Web** redirect URI; defaults to `http://127.0.0.1:8000/auth/microsoft/callback`
- `OFFICEHOURS_FRONTEND_URL` — where the browser lands after sign-in
  (defaults to `http://127.0.0.1:5180`)
- `OFFICEHOURS_MS_ALLOWED_DOMAIN` — allowed email domain, defaults to `aui.ma`

Flow: `GET /auth/microsoft/login` redirects to the Microsoft account picker;
the callback validates the id_token (audience + tenant + domain), creates the
user on first sign-in (no usable password), mints a normal app session, and
redirects to the SPA at `/sso#token=…`. Roles still come from course
memberships (Canvas), not from the Microsoft account.

## Canvas LTI 1.3 (real course tool)

The unsigned `/canvas/launch` simulator and `/canvas-demo` / `/demo/*` pages are
**off** when `OFFICEHOURS_DEMO` is not true. Production launch is signed LTI 1.3.

Ask AUI Canvas / IT for an **LTI 1.3 developer key** plus a course-level
**External tool** that uses it. Also set a Canvas API token so Rooms chapters
and the course agent read **that course’s modules**, not the local demo mirror.

### Developer key (paste from `GET /lti/config` once env is set)

- **OpenID Connect Initiation URL:** `https://YOUR-API/lti/login`
- **Target Link URI / Redirect URI:** `https://YOUR-API/lti/launch`
- **JWK method:** Public JWK URL `https://YOUR-API/lti/jwks`
- **Privacy:** Public (email must be in the launch)
- **Placement:** Course navigation (or assignment / module)

### Backend env

- `OFFICEHOURS_LTI_ISSUER` — Canvas issuer, e.g. `https://canvas.aui.ma`
- `OFFICEHOURS_LTI_CLIENT_ID` — developer key client_id
- `OFFICEHOURS_LTI_AUTH_LOGIN_URL` — optional; defaults to
  `{issuer}/api/lti/authorize_redirect`
- `OFFICEHOURS_LTI_JWKS_URL` — optional; defaults to
  `{issuer}/api/lti/security/jwks`
- `OFFICEHOURS_LTI_LAUNCH_URL` — must match the developer key redirect URI
- `OFFICEHOURS_LTI_DEPLOYMENT_ID` — optional; reject other deployments
- `CANVAS_BASE_URL` + `CANVAS_API_TOKEN` — live module/page/file sync
- `OFFICEHOURS_FRONTEND_URL` — SPA origin (launch lands on `/sso#token=…&course=`)
- `OFFICEHOURS_DEMO=false` — hides demo routes and unsigned `/canvas/launch`

Flow: student clicks **OfficeHours** in a Canvas course → OIDC login → signed
`id_token` → we provision user + course + role → sync live modules when the
API token is set → browser opens the matching workspace.

## Train models

```bash
cd backend
python3 scripts/train_classifier.py
python3 scripts/train_matcher.py
python3 scripts/train_synthesizer.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical python3 scripts/train_learning_style.py
```

See [`docs/training_data.md`](../docs/training_data.md).

## Demo vs community deploy

- **Demo / FYP walkthrough:** `OFFICEHOURS_DEMO=true` (default in
  `./scripts/run_product.sh`). Seeds Sara/Youssef/Alice, sample courses, and a
  sample chapter outline. Local Canvas mirror fills modules.
- **AUI community deploy:** `OFFICEHOURS_DEMO=false`. Do **not** seed demo
  people. Set `CANVAS_BASE_URL` + `CANVAS_API_TOKEN`. Users and courses come
  from Canvas launch; Rooms chapters are that course’s Canvas modules.

## Seed demo data

```bash
export OFFICEHOURS_DEMO=true
cd backend
python3 scripts/seed_demo_data.py --reset --limit 20
```

## Run tests

```bash
pytest
# or: venv/bin/python -m pytest
```

## Structure

```
backend/
├── app/
│   ├── main.py
│   ├── routes/          # HTTP + WebSocket
│   ├── models/
│   ├── services/        # ask_triage_service, help_coach_service, …
│   ├── database/
│   ├── realtime/
│   └── ai/              # Analyzer / Matcher / Synthesizer (custom-trained)
└── tests/
```
