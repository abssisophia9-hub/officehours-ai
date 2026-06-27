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

## Clustering configuration

Request clustering uses `sentence-transformers` embeddings by default.

Optional environment variables:

- `OFFICEHOURS_EMBEDDING_MODEL` — defaults to `all-MiniLM-L6-v2`
- `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` — defaults to `0.72`
- `OFFICEHOURS_CLUSTERING_BACKEND=lexical` — lightweight deterministic backend
  for tests/local runs where you do not want to download the embedding model

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
