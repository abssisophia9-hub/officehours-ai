# OfficeHours AI

## Cursor Cloud specific instructions

### Scope of what is runnable

**Primary product (use this for demos and FYP testing):**

- **FastAPI backend** (`backend/`) — http://127.0.0.1:8000
- **Unified multi-role app** (`frontend/officehours-app/` :5180) — opening
  story, then one login + course picker (role is per course; TAs are staff)

Helper: `./scripts/run_product.sh`

CI builds **only** the backend and this app. Folders under
`frontend/student-kiosk/`, `professor-dashboard/`, and `ta-dashboard/` are
milestone archives — not product jobs.

### Backend environment

- Python deps are installed into a virtualenv at `backend/venv` (created during
  setup; the system package `python3.12-venv` is required to create it). The
  update script refreshes this venv.
- Installing `sentence-transformers` pulls in `torch` and the full NVIDIA CUDA
  wheel stack, so a clean dependency install downloads several GB and is slow.
  The running app uses `sentence-transformers` for request clustering unless
  `OFFICEHOURS_CLUSTERING_BACKEND=lexical` is set.
- Request clustering defaults to sentence-transformer embeddings
  (`OFFICEHOURS_EMBEDDING_MODEL`, default `all-MiniLM-L6-v2`). Tests set
  `OFFICEHOURS_CLUSTERING_BACKEND=lexical` to avoid model downloads.

### Backend run / test / lint (run from `backend/`)

- Dev server: `venv/bin/uvicorn app.main:app --reload` — serves
  http://127.0.0.1:8000 (root `/`, `/health`, Swagger UI at `/docs`).
- Tests: `venv/bin/python -m pytest` (see `backend/README.md`).
- Lint: no linter is configured in this repo (no ruff/flake8/black in
  `requirements.txt`); use `venv/bin/python -m py_compile` for a basic syntax
  check.

### Product app run / test (run from `frontend/officehours-app/`)

- Install: `npm ci`.
- Dev server: `npm run dev` (port **5180**).
- Build: `npm run build`.
- Dependency audit: `npm audit --audit-level=moderate`.

### Database

- Default DB is SQLite at `backend/officehours.db` (auto-created at startup via
  `Base.metadata.create_all`). Override with `DATABASE_URL`. Tests set
  `DATABASE_URL=sqlite:///:memory:`. Postgres: see `docs/ops_scale.md` and
  `docker-compose.postgres.yml`.

### Demo vs community deploy

- Local FYP helper `./scripts/run_product.sh` sets `OFFICEHOURS_DEMO=true`
  (Sara/Youssef accounts, sample chapter outlines, local Canvas mirror).
- Community deploy: `OFFICEHOURS_DEMO=false`, live Canvas credentials. Users
  and chapters come from the linked LMS course — not a hardcoded catalog.

### Product vocabulary

See [`docs/glossary.md`](docs/glossary.md). Intake pipeline is **Ask Triage**
(API fields may still say `oracle_*` — same pipeline). TA mid-session AI is
**Help Coach**. Student classmate forum is **Rooms** (API `/help-room/`).
Defense crib: [`docs/defense_crib.md`](docs/defense_crib.md). Gold-label lab:
[`docs/gold_label_lab.md`](docs/gold_label_lab.md).
