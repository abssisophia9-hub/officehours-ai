# OfficeHours AI — AUI CDN deploy guide

Target public URL: **https://cdn.aui.ma/officehours-ai/**

One `uvicorn` process serves the API, WebSocket, `/health`, and the built SPA
under `OFFICEHOURS_ROOT_PATH=/officehours-ai`. Local Windows scripts on ports
**5180 / 8000** are unchanged when that env var is left empty.

## Prerequisites

| Item | Notes |
| --- | --- |
| Python | **3.12** with `venv` |
| Postgres | 14+ (compose file included). App also runs on SQLite for smoke tests only. |
| Reverse proxy | TLS terminator that supports **WebSocket Upgrade** |
| Disk / RAM | ~1.2 GB disk for CPU torch + deps + MiniLM; ~2 GB RAM |
| Outbound HTTPS | Canvas (required for community). Optional: Hugging Face (only if MiniLM not pre-placed), Gemini/YouTube if enabled later |

## What the app does on boot

1. **`Base.metadata.create_all`** creates missing tables (no Alembic required).
2. **`ensure_schema`** applies additive column renames/fixes.
3. If `OFFICEHOURS_DEMO=true`, **`ensure_demo_accounts`** seeds Sara / Alice / Prof Benali (`aui-demo`).

Optional SQL under `deploy/` (not required when using create_all):

- `deploy/schema.sql` — empty table DDL from Postgres 16
- `deploy/demo_seed.sql` — optional dump after demo seed (prefer create_all + demo flag)

## Clustering vs embeddings (honest tradeoff)

| Setting | Effect |
| --- | --- |
| `OFFICEHOURS_CLUSTERING_BACKEND=lexical` (**recommended for IT**) | Request clustering uses a lightweight lexical backend (no MiniLM for clusters). |
| Ask Triage ML classifiers | Still use **`all-MiniLM-L6-v2`** embeddings when joblib models are present. |

**Optional companion** `officehours-ai-minilm-offline.tar` holds MiniLM
(kept separate so the main ZIP stays small). Unpack with
`tar -xf officehours-ai-minilm-offline.tar`, copy its `huggingface/` folder to
`deploy/huggingface/`, then set **all three** of `HF_HOME`,
`TRANSFORMERS_OFFLINE=1`, and `HF_HUB_OFFLINE=1` (see
`.env.production.example`). If the snapshot is **not** unpacked, leave those
three commented so the first Ask Triage ML classify can reach `huggingface.co`.

Do **not** install CUDA torch wheels. Use the CPU index (below).

## Step-by-step

### 1. Unpack

```bash
unzip officehours-ai-aui-cdn.zip -d /opt/officehours-ai
cd /opt/officehours-ai
```

### 2. Postgres

Using the included compose file (Docker) **or** any managed Postgres:

```bash
docker compose -f docker-compose.postgres.yml up -d
# DATABASE_URL=postgresql://officehours:officehours@127.0.0.1:5432/officehours
```

Create an empty database and role; the app creates tables on start.

### 3. Python venv (CPU torch first)

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 4. Environment

Copy `.env.production.example` → process env / secrets store (names only in the
example — never commit real values). Minimum for a demo host behind the CDN path:

```bash
export OFFICEHOURS_ROOT_PATH=/officehours-ai
export OFFICEHOURS_SERVE_FRONTEND=true
export OFFICEHOURS_DEMO=true
export OFFICEHOURS_CLUSTERING_BACKEND=lexical
export OFFICEHOURS_FRONTEND_URL=https://cdn.aui.ma/officehours-ai
export OFFICEHOURS_CORS_ORIGINS=https://cdn.aui.ma
export OFFICEHOURS_TRUST_PROXY=true
export DATABASE_URL=postgresql://officehours:CHANGE_ME@127.0.0.1:5432/officehours
# Optional if MiniLM companion ZIP was unpacked under deploy/huggingface:
# export HF_HOME=/opt/officehours-ai/deploy/huggingface
# export TRANSFORMERS_OFFLINE=1
# export HF_HUB_OFFLINE=1
```

Community later: set `OFFICEHOURS_DEMO=false`, add Canvas LTI + `CANVAS_*`, and
register redirect URIs **with** the `/officehours-ai` prefix.

### 5. Start command

From `backend/` (working directory matters for relative paths):

```bash
cd /opt/officehours-ai/backend
OFFICEHOURS_ROOT_PATH=/officehours-ai \
OFFICEHOURS_SERVE_FRONTEND=true \
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
OFFICEHOURS_DEMO=true \
DATABASE_URL='postgresql://officehours:CHANGE_ME@127.0.0.1:5432/officehours' \
OFFICEHOURS_FRONTEND_URL=https://cdn.aui.ma/officehours-ai \
venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Use **one worker** (in-process WebSocket hub + rate-limit memory). Restart on
failure via systemd/`Restart=always` or equivalent.

### 6. Reverse proxy (nginx sketch)

Forward **without stripping** the `/officehours-ai` prefix. Enable WebSocket.

```nginx
# Prefer matching the whole prefix and forwarding the original URI unchanged.
location ^~ /officehours-ai {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_read_timeout 3600;
}
```

Note: some nginx builds normalize `../` / `%2e%2e` **before** location
matching, so a probe may get nginx `404` instead of the SPA shell. That is
still safe (no file leak). The uvicorn app itself returns the SPA index for
those probes and never serves files outside `dist/`.

Health check URL: `GET https://cdn.aui.ma/officehours-ai/health`  
WebSocket: `wss://cdn.aui.ma/officehours-ai/ws?token=…&course_id=…`

### 7. Ports

| Port | Binding | Notes |
| --- | --- | --- |
| 8000 | `127.0.0.1` only | uvicorn; public TLS on 443 via proxy |
| 5432 | private | Postgres |

Do not expose 8000 publicly.

## Outbound hosts (allow-list)

| Host | When |
| --- | --- |
| AUI Canvas base / issuer | Community / LTI / live materials |
| `login.microsoftonline.com` | Optional Microsoft SSO |
| `generativelanguage.googleapis.com` | Only if Gemini enabled |
| `www.googleapis.com` (YouTube) | Only if `YOUTUBE_API_KEY` set |
| `huggingface.co` | Only if MiniLM snapshot not used |

With `HF_HUB_OFFLINE=1` + the MiniLM companion ZIP unpacked, Hugging Face is not required.

## Env var names IT must set

See `.env.production.example`. Critical names:

`OFFICEHOURS_ROOT_PATH`, `OFFICEHOURS_SERVE_FRONTEND`, `OFFICEHOURS_DEMO`,
`OFFICEHOURS_CLUSTERING_BACKEND`, `OFFICEHOURS_FRONTEND_URL`,
`OFFICEHOURS_CORS_ORIGINS`, `OFFICEHOURS_TRUST_PROXY`, `DATABASE_URL`,
`HF_HOME` (if using packaged MiniLM), plus Canvas / Microsoft / LLM secrets
when those features are enabled.

## Switch demo → community

1. `OFFICEHOURS_DEMO=false`
2. Provision Canvas LTI paths under the prefix (`/officehours-ai/lti/login|launch|jwks`)
3. Set `CANVAS_BASE_URL` + `CANVAS_API_TOKEN`
4. Optional: Microsoft redirect `…/officehours-ai/auth/microsoft/callback`
5. Leave LLM flags off unless campus policy allows

## Troubleshooting

| Symptom | Check |
| --- | --- |
| 404 on `/officehours-ai/health` | `OFFICEHOURS_ROOT_PATH`, proxy `proxy_pass` includes prefix |
| Assets 404 | Rebuild used `VITE_ROOT_PATH=/officehours-ai` (prebuilt `dist/` in this ZIP already does) |
| WS fails | Upgrade headers; single worker; path `/officehours-ai/ws` |
| CORS errors | `OFFICEHOURS_FRONTEND_URL` / `OFFICEHOURS_CORS_ORIGINS` HTTPS origins |
| Slow first ask / embedder error | `HF_HOME` + offline flags, or allow Hugging Face once |
| CUDA / huge download | Reinstall CPU torch from the pytorch.org CPU index before `requirements.txt` |
| Empty Resources | Expected when Gemini/YouTube keys absent — UI shows empty state |

## Local Windows (unchanged)

Leave `OFFICEHOURS_ROOT_PATH` unset. Use `scripts/start-backend.ps1` and
`scripts/start-frontend.ps1` (ports **8000** / **5180**).
