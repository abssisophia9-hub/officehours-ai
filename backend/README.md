# OfficeHours AI — Backend

FastAPI backend for the OfficeHours AI triage system.

## Setup

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

- `POST /requests/` — submit a student request; backend classifies, recommends,
  and assigns a cluster.
- `GET /requests/` — list requests for the professor dashboard.
- `GET /requests/{request_id}/status` — privacy-safe anonymous status lookup
  by request code (no student ID or request text returned).
- `POST /actions/recommendations/` — persist a professor recommendation-card
  decision and generate an action plan for agenda/status/notification next
  steps.
- `GET /actions/recommendations/` — list saved professor decisions/action plans.
- `GET /actions/recommendations/{decision_id}/calendar.ics` — download an
  iCalendar (`.ics`) file for approved group-session / 1:1 / TA-support plans
  when office-hour windows are configured.
- `GET /office-hours/` — list persisted professor office-hour windows.
- `POST /office-hours/` — add an office-hour window (day, start, end, location).
- `DELETE /office-hours/{window_id}` — remove an office-hour window.

## Clustering configuration

Request clustering uses `sentence-transformers` embeddings by default.

Optional environment variables:

- `OFFICEHOURS_EMBEDDING_MODEL` — defaults to `all-MiniLM-L6-v2`
- `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` — defaults to `0.72`
- `OFFICEHOURS_CLUSTERING_BACKEND=lexical` — lightweight deterministic backend
  for tests/local runs where you do not want to download the embedding model

## Seed demo data

Populate local SQLite with synthetic finals-week requests:

```bash
cd backend
python3 scripts/seed_demo_data.py --reset --limit 20
```

The seed script uses `OFFICEHOURS_CLUSTERING_BACKEND=lexical` by default for a
fast demo. To exercise semantic clustering during seeding:

```bash
OFFICEHOURS_CLUSTERING_BACKEND=sentence-transformers \
  python3 scripts/seed_demo_data.py --reset --limit 20
```

## Analyze pilot survey responses

Summarize demo survey CSVs in `data/survey_responses/`:

```bash
cd backend
python3 scripts/analyze_survey_responses.py
```

Outputs land in `reports/final_report/survey_evaluation_summary.{json,md}`.

## Run tests

```bash
pytest
```

## Structure

```
backend/
├── app/
│   ├── main.py        # FastAPI app entry point
│   ├── routes/        # API endpoints
│   ├── models/        # Pydantic / ORM models
│   ├── services/       # Business logic (classification → recommendation, etc.)
│   ├── database/      # DB session/engine setup
│   └── ai/            # Classification + clustering logic
└── tests/              # Pytest test suite
```
