# OfficeHours AI

## Cursor Cloud specific instructions

### Scope of what is runnable
- The **FastAPI backend** (`backend/`), **student kiosk frontend** (`frontend/student-kiosk/`), and **professor dashboard frontend** (`frontend/professor-dashboard/`) are runnable applications. `backend/app/ai/*` plus `backend/app/services/*` are docstring-only stubs that are not imported at runtime.

### Backend environment
- Python deps are installed into a virtualenv at `backend/venv` (created during setup; the system package `python3.12-venv` is required to create it). The update script refreshes this venv.
- Installing `sentence-transformers` pulls in `torch` and the full NVIDIA CUDA wheel stack, so a clean dependency install downloads several GB and is slow. The running app uses `sentence-transformers` for request clustering unless `OFFICEHOURS_CLUSTERING_BACKEND=lexical` is set.
- Request clustering defaults to sentence-transformer embeddings (`OFFICEHOURS_EMBEDDING_MODEL`, default `all-MiniLM-L6-v2`). Tests set `OFFICEHOURS_CLUSTERING_BACKEND=lexical` to avoid model downloads.

### Backend run / test / lint (run from `backend/`)
- Dev server: `venv/bin/uvicorn app.main:app --reload` — serves http://127.0.0.1:8000 (root `/`, `/health`, Swagger UI at `/docs`, request CRUD under `/requests/`).
- Tests: `venv/bin/python -m pytest` (see `backend/README.md`).
- Lint: no linter is configured in this repo (no ruff/flake8/black in `requirements.txt`); use `venv/bin/python -m py_compile` for a basic syntax check.

### Student kiosk run / test (run from `frontend/student-kiosk/`)
- Install: `npm ci`.
- Dev server: `npm run dev`.
- Build: `npm run build`.
- Dependency audit: `npm audit --audit-level=moderate`.

### Professor dashboard run / test (run from `frontend/professor-dashboard/`)
- Install: `npm ci`.
- Dev server: `npm run dev`.
- Build: `npm run build`.
- Dependency audit: `npm audit --audit-level=moderate`.

### Database
- Default DB is SQLite at `backend/officehours.db` (auto-created at startup via `Base.metadata.create_all`). Override with the `DATABASE_URL` env var. Tests set `DATABASE_URL=sqlite:///:memory:`.
