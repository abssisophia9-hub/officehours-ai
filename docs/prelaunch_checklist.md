# Pre-launch checklist — resolved against this repo

The checklist below was written from a diagram that does not match OfficeHours AI.
This file is the resolution: what is already true, and what must not be built
before hosting.

Product shape: one React app (`frontend/officehours-app`) talking to one
FastAPI process (`backend/`). Ask Triage, Help Coach, and Study Agent are
**local models** (MiniLM + scikit-learn + approved-KB retrieval), behind one
model interface. The external Claude API is allowed for the MVP with demo
data only. Do not send real student data or real course material without
further approval. Self-hosting a model is not required.

Protocol: REST for requests, WebSocket `/ws` for live course events.
See [`system_architecture.md`](system_architecture.md) and [`SECURITY.md`](SECURITY.md).

## P0

| Item | Verdict |
| --- | --- |
| Close the AI response loop | **Already closed.** `POST /requests/` runs Analyzer → Matcher → Synthesizer and returns the row (hint, TA, category) in the HTTP response, then pushes `triage.*` on `/ws`. Help Coach is `POST /ta/assist/`. Study Agent is `POST /agent/ask` and quotes stamped KB only. Action plans are `POST /actions/recommendations/`. |
| Add an external LLM provider | **Allowed for the MVP, demo data only.** One Claude interface, gated by `OFFICEHOURS_ALLOW_EXTERNAL_LLM`. No real student data and no real course material without further approval. `analyzer_agent.py` still refuses Claude when that flag is false. |
| Celery / RQ / SQS for LLM calls | **Do not.** There is no remote LLM call on the request path. Intake is an in-process joblib predict. |
| Auth must go through `client.js` | **Already true.** `AuthContext.jsx` and `LoginPage.jsx` call `api()` from `frontend/officehours-app/src/api/client.js`. `App.jsx` only declares routes. |
| Role checks on every route | **Already true.** `access_control.py` checks course membership (student / TA / professor). WebSocket `/ws` requires a token and that course. Quiet-ask status is the documented exception in `SECURITY.md`. |
| Failure paths | **Already true for the app.** Global handlers hide stack traces. LTI and login failures return HTTP errors. Unclassifiable text becomes category `uncategorized` and still reaches a TA. DB failures surface as 500s with a generic body plus `http.unhandled` audit log. A failed Canvas launch does not invent a session. |

## P1

| Item | Verdict |
| --- | --- |
| Database ownership | **One database, tables split by module.** Auth and memberships: `models/auth.py`. Asks: `models/request.py`. KB: `models/knowledge.py`. Rooms: `models/help_room.py`. Notes: `models/peer_notes.py`. Engine only: `database/session.py`. |
| Live Event Hub | **Decided.** In-process WebSocket hub (`realtime/hub.py`). Course-scoped. Not a second database. Not durable across process restarts. Multi-worker hosts need one worker or a proxy, same note as rate limiting. |
| API gateway | **Not a separate service.** The frontend calls one FastAPI origin. Rate limit and auth sit in that process. A campus reverse proxy terminates TLS. |
| Rate limiting | **On by default** for `/auth/login`, `/requests/`, and `/agent/ask` (`services/rate_limit.py`). In-process buckets. |
| What `request.py` is | **The student ask ticket.** One row per submission: text, triage fields, assigned TA, hint, KB link. Not an audit log (that is `security_log.py`). |
| What `session.py` is | **The SQLAlchemy engine and `get_db()`.** It does not store business rows. Login sessions are opaque tokens in `services/session_tokens.py`. |
| REST vs WebSocket | **REST for commands, WebSocket for live push.** No GraphQL. |

## P2

| Item | Verdict |
| --- | --- |
| Redis cache | **Not required to host.** KB reads are course-scoped SQL. Add a cache only if a live course shows read latency. |
| Schema doc | ERD: `diagrams/database_erd.png`. Regenerate with `scripts/generate_architecture_diagrams.py`. |
| LLM latency monitoring | **N/A for an external API.** Local predict time can be sampled with `backend/scripts/measure_ask_triage_latency.py`. Audit log covers auth, rate limit, websocket, 401/403, and 500s. |
| Four backend clusters | **One process.** Routes live under `backend/app/routes/`. Scale by moving `DATABASE_URL` to Postgres (`docs/ops_scale.md`), not by splitting into four services. |
| Ask Intake vs Ask Triage | **One pipeline.** `POST /requests/` is the intake endpoint. Ask Triage is the Analyzer / Matcher / Synthesizer that runs inside it (`ask_triage_service.py`). |

## What actually blocks a campus host

These are credential and deploy steps, not missing subsystems. Full list: [`SECURITY.md`](SECURITY.md).

1. `OFFICEHOURS_DEMO=false`
2. Canvas LTI 1.3 key and API token from campus IT
3. HTTPS origin in `OFFICEHOURS_FRONTEND_URL` and `OFFICEHOURS_CORS_ORIGINS`
4. Postgres via `DATABASE_URL` when leaving the laptop
5. Claude for the MVP may set `OFFICEHOURS_ALLOW_EXTERNAL_LLM=true`, demo data only, through that single interface. Leave the flag false once real student data or real course material is in play and that use is not approved. Leave `OFFICEHOURS_RATE_LIMIT=true`.
