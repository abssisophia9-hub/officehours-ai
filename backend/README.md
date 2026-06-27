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
