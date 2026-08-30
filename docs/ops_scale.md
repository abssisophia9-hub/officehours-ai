# Scale slice — Postgres, notify, pages, retrain

Due work for a real term. Defaults stay SQLite + no SMTP so the FYP demo
does not need Docker.

## Postgres

`DATABASE_URL` already selects the engine. SQLite is the default
(`sqlite:///./officehours.db`). Tests use `sqlite:///:memory:`.

For campus:

```bash
docker compose -f docker-compose.postgres.yml up -d
export DATABASE_URL=postgresql://officehours:officehours@127.0.0.1:5432/officehours
cd backend && venv/bin/uvicorn app.main:app
```

Non-SQLite URLs get `pool_pre_ping` and a small pool
(`OFFICEHOURS_DB_POOL_SIZE`, `OFFICEHOURS_DB_MAX_OVERFLOW`).
`GET /health` reports `"database": "postgresql"` or `"sqlite"`.

`psycopg2-binary` is in `backend/requirements.txt`. Schema still uses
`create_all` + additive `ensure_schema` (Postgres-safe column types).

## Email / push

When a TA **claims** or **replies**, the submitter (including Quiet ask — we
know `created_by_user_id` but staff never see the name) gets:

1. An inbox row (`GET /notifications/`)
2. A `notification.created` WebSocket event on that course
3. SMTP email **only if** configured

```
OFFICEHOURS_SMTP_HOST=smtp.office365.com
OFFICEHOURS_SMTP_PORT=587
OFFICEHOURS_SMTP_USER=officehours@aui.ma
OFFICEHOURS_SMTP_PASSWORD=...
OFFICEHOURS_SMTP_FROM=officehours@aui.ma
OFFICEHOURS_SMTP_STARTTLS=true
```

Without SMTP the demo still shows the inbox. That is the campus “push”
channel until IT adds a mobile APNs/FCM app.

## Pagination

List endpoints accept `limit` (1–200) and `offset`. **Omit `limit`** and the
response stays a raw array (existing tests). **Pass `limit`** and you get:

```json
{ "items": [], "total": 12, "limit": 50, "offset": 0, "has_more": false }
```

The product app sends `limit=50` on requests, TA queue, KB, and Rooms.

## Online retrain

`POST /analytics/retrain?course_id=&apply_models=false` (professor) evaluates
CSV gold + DB gold and writes `reports/final_report/gold_label_evaluation.json`.
It does **not** rewrite `.joblib` unless:

- `OFFICEHOURS_ALLOW_RETRAIN=true`, and
- `apply_models=true`

That second flag runs `scripts/train_classifier.py` (timeout 180s). Default
off. The professor desk button is **Evaluate gold now** — metrics only.
