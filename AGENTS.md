# OfficeHours AI

## Cursor Cloud specific instructions

### Scope of what is runnable

**Primary product (use this for demos and FYP testing):**

- **FastAPI backend** (`backend/`) — http://127.0.0.1:8000
- **Unified multi-role app** (`frontend/officehours-app/` :5180) — students, TAs,
  professors in one login + course picker

Helper: `./scripts/run_product.sh`

**Legacy shells** (hardware / older demos only — not the product package):

- Student kiosk (`frontend/student-kiosk/` :5173)
- Professor dashboard (`frontend/professor-dashboard/` :5174)
- TA dashboard (`frontend/ta-dashboard/` :5175)

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

### Legacy frontends (optional)

Same install / `npm run dev` / `npm run build` / `npm audit` pattern from each
folder (`student-kiosk` 5173, `professor-dashboard` 5174, `ta-dashboard` 5175).

### Database

- Default DB is SQLite at `backend/officehours.db` (auto-created at startup via
  `Base.metadata.create_all`). Override with the `DATABASE_URL` env var. Tests
  set `DATABASE_URL=sqlite:///:memory:`.

### Product vocabulary

See [`docs/glossary.md`](docs/glossary.md). Intake pipeline is **Ask Triage**
(implementation often still named `oracle_*`). TA mid-session AI is **Help Coach**.
