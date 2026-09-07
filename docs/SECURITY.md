# Backend security baseline

Production checklist for the OfficeHours AI API (`backend/`).  
Hardening branch builds on Canvas LTI 1.3 (`cursor/canvas-lti13-live-54c7`).

Related: [`canvas_live_test.md`](canvas_live_test.md) · [`ops_scale.md`](ops_scale.md) ·
[`backend/.env.example`](../backend/.env.example) · [`backend/README.md`](../backend/README.md)

## Scorecard (target: all PASS before campus deploy)

| # | Control | Status | Implementation |
| --- | --- | --- | --- |
| 2 | Authorization | PASS | Course-scoped RBAC (`access_control.py`); TA roster staff-only; actions scoped to staff courses; office-hours mutate = professor |
| 3 | Endpoint security | PASS | Bearer on product routes; WS requires token + course membership (`realtime.py`); demo Canvas launch off when not demo |
| 4 | Input validation | PASS | Pydantic bounds on `RequestCreate`, `LoginRequest`, upload sizes |
| 5 | Injection protection | PASS | SQLAlchemy ORM; no user-driven shell |
| 6 | JWT security | PASS | LTI RS256 JWKS + nonce; Microsoft id_token RS256 JWKS + aud/iss/exp/tid; app sessions are opaque tokens |
| 7 | Password security | PASS | PBKDF2-HMAC-SHA256, 120k iterations, per-password salt, `compare_digest` |
| 8 | Rate limiting | PASS | Default ON for login / Quiet ask / agent; `OFFICEHOURS_TRUST_PROXY` gated; documented multi-worker note |
| 9 | CORS | PASS | Allow-list from frontend URL + `OFFICEHOURS_CORS_ORIGINS` (never `*`) |
| 10 | Env variables | PASS | `backend/.env.example`; secrets from env only |
| 11 | Sensitive data in responses | PASS | Quiet ask strips identity; no `password_hash` in API; audit log redacts tokens |
| 12 | Error handling | PASS | Global handlers; 500s return generic message; no stack traces to clients |
| 13 | File upload security | PASS | Size + extension + magic-byte checks (`upload_security.py`) |
| 14 | Database security | PASS | ORM; `DATABASE_URL` from env; least-privilege Postgres documented below |
| 15 | Database performance | PASS | SQL `LIMIT`/`OFFSET` on request lists; TA queue hard-capped; status decisions filtered; hot indexes |
| 16 | Data integrity | PASS | Unique memberships; atomic TA claim; additive indexes |
| 17 | API validation | PASS | Request/response models + HTTP status codes |
| 18 | Logging & monitoring | PASS | Structured JSON audit (`security_log.py`); `/health`; `X-Request-Id` |
| 19 | Testing | PASS | Defense hardening + LTI + rate-limit + upload magic + MS JWT unit tests |
| 20 | Production configuration | PASS | Demo off path; rate limit on; CORS allow-list; LLM off; security headers |

### Accepted product behaviors (documented, not bugs)

- **Status receipt:** any course member may `GET /requests/{id}/status` (request-code style receipt). Full row remains owner/staff-only. Quiet ask never stores name/ID.
- **Rate limit store:** in-process. Multi-worker hosts must rate-limit at the reverse proxy **or** run a single worker.
- **OIDC state:** LTI/Microsoft login `state` is in-process memory (same single-worker guidance).

## Production deploy checklist

1. Copy `backend/.env.example` → real secrets store / process env.
2. Set `OFFICEHOURS_DEMO=false`.
3. Set `OFFICEHOURS_FRONTEND_URL` + `OFFICEHOURS_CORS_ORIGINS` to HTTPS SPA origins.
4. Configure LTI + `CANVAS_*` (see `canvas_live_test.md`).
5. Prefer Postgres: `DATABASE_URL=postgresql://…` with a least-privilege role (SELECT/INSERT/UPDATE/DELETE on app tables only).
6. Terminate TLS at the reverse proxy. Set `OFFICEHOURS_TRUST_PROXY=true` **only** if that proxy overwrites `X-Forwarded-For`.
7. Leave `OFFICEHOURS_RATE_LIMIT=true` and `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`.
8. Run `pytest` with production-like flags except `OFFICEHOURS_RATE_LIMIT=false` in the test suite.
9. Confirm `/health` shows `"demo": false` and `"rate_limit": true`.
10. Ship stderr JSON audit lines to your log collector.

## Audit events (examples)

| Event | When |
| --- | --- |
| `auth.login_ok` / `auth.login_failed` | Password login |
| `rate_limit.exceeded` | Hot-path throttle |
| `ws.connected` / `ws.rejected` | WebSocket |
| `http.denied` | 401/403 responses |
| `http.unhandled` | Unexpected 500 |

Tokens, passwords, and secrets are always redacted.

## Security headers

Every HTTP response includes:

- `X-Request-Id`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`
- `X-Frame-Options: DENY`
