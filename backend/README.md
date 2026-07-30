# OfficeHours AI — Backend

FastAPI backend for the OfficeHours AI Ask Triage system.

## Ask Triage multi-agent pipeline (custom-trained models)

On `POST /requests/`, the backend runs **local trained models only** (FYP path —
no prompted Claude calls, no `USE_MOCK_CLAUDE` mocks):

1. **Analyzer** — fine-tuned small classifier (embeddings + logistic regression)
   (`OFFICEHOURS_ANALYZER_BACKEND=ml`). Produces category, difficulty, tags,
   estimated minutes. Train/refresh with:
   `python3 scripts/train_classifier.py`
   Optional professor-feedback export:
   `python3 scripts/export_analyzer_training_data.py`
2. **Matcher** — trained TA assignment classifier (embeddings + logistic
   regression + queue-depth penalty). Train with:
   `python3 scripts/train_matcher.py`
3. **Synthesizer** — RAG over curated teaching bank / professor-approved KB +
   trained learning-style ranker (no LLM). Train with:
   `python3 scripts/train_synthesizer.py`

Professor curation remains the gate: TA resolve → `pending_review` → professor approve → student KB / lifetime confusion agent.

Useful endpoints:

- `GET /ta/roster/`
- `GET /analytics/oracle-metrics`
- `GET /analytics/lifetime-confusion`
- `WS /ws` live events including `oracle.analyzer.done`, `oracle.matcher.done`, `oracle.synthesizer.done`

External LLM calls are disabled by default (`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`).

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
  assigns a cluster, persists urgency, and seeds a `pending_review` knowledge
  draft for professor curation.
- `GET /requests/` — list requests for the professor dashboard.
- `GET /requests/{request_id}/status` — privacy-safe anonymous status lookup
  by request code (no student ID or request text returned).
- `GET /knowledge/` — list knowledge-base entries (`?status=pending_review|approved|rejected`).
- `PATCH /knowledge/{id}` — professor approve / edit / reject a KB draft.
- `POST /agent/ask` — student-facing KB agent; answers only from **approved** entries
  via semantic similarity search.
- `GET /ta/queue/` — open TA queue (hides approved/rejected KB items).
- `POST /ta/resolve/` — TA saves teaching notes; entry stays `pending_review` for professor curation.
- `WS /ws` — live events (`request.created`, `knowledge.*`, `ta.resolved`, `escalation`).
- `GET /analytics/struggle-heatmap` — weekly category aggregation for the professor heatmap.
- `GET /analytics/escalations` — auto-flagged aging / high-urgency / recurring topics.
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
- `OFFICEHOURS_ANALYZER_BACKEND=ml|rules` — Analyzer backend; defaults to `ml`
- `OFFICEHOURS_CLASSIFIER_BACKEND=rules|ml` — defaults to `rules`; set `ml` to
  use the trained embedding classifier in `backend/models/request_classifier.joblib`
- `OFFICEHOURS_CLASSIFIER_MODEL` — optional override path to the saved ML model
- `OFFICEHOURS_MATCHER_MODEL` — optional path to Matcher classifier
  (`backend/models/matcher_classifier.joblib`)
- `OFFICEHOURS_SYNTHESIZER_MODEL` — optional path to Synthesizer style ranker
  (`backend/models/synthesizer_ranker.joblib`)
- `OFFICEHOURS_TEACHING_BANK` — optional path to Synthesizer teaching-bank CSV
- `OFFICEHOURS_LEARNING_STYLE_BACKEND=rules|ml` — defaults to `rules`
- `OFFICEHOURS_LEARNING_STYLE_MODEL` — optional path to learning-style classifier
- `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` — keep external Claude disabled (FYP default)

## Train ML classifier (Analyzer)

Train/evaluate the embedding + logistic regression classifier on labeled CSVs:

```bash
cd backend
python3 scripts/train_classifier.py
```

Metrics are written to `reports/final_report/classifier_evaluation.{json,md}`.
Labeled data lives in `data/labeled_requests*.csv`.

## Train Matcher

```bash
cd backend
python3 scripts/train_matcher.py
```

Labeled data: `data/matcher_training.csv`. Model:
`backend/models/matcher_classifier.joblib`.

## Train Synthesizer

```bash
cd backend
python3 scripts/train_synthesizer.py
```

Teaching bank: `data/synthesizer_teaching_bank.csv`. Model:
`backend/models/synthesizer_ranker.joblib`.

## Train learning-style classifier

Infers how a student prefers to understand a topic (`example_driven`,
`step_by_step`, `visual_structural`, `conceptual`, `unknown`) so the custom
Synthesizer can prefer matching teaching-bank entries:

```bash
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical python3 scripts/train_learning_style.py
```

Labeled data: `data/labeled_learning_styles.csv`.

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
│   └── ai/            # Custom-trained Analyzer / Matcher / Synthesizer
└── tests/              # Pytest test suite
```
