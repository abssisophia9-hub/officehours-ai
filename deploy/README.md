# Deploy helpers (AUI CDN)

## App-managed schema (preferred)

On startup the API runs:

1. `Base.metadata.create_all` — creates empty tables if missing
2. `ensure_schema` — additive renames/columns
3. `ensure_demo_accounts` — only when `OFFICEHOURS_DEMO=true`

You do **not** need hand-applied SQL for a normal install.

## IT smoke

See [`IT_SMOKE_TEST.md`](IT_SMOKE_TEST.md) (~5 minutes of curl checks).

## Optional MiniLM companion

Unpack `officehours-ai-minilm-offline.tar` and point `HF_HOME` at its
`huggingface/` folder. Set `TRANSFORMERS_OFFLINE=1` and `HF_HUB_OFFLINE=1`
**only** when that snapshot is present; otherwise leave those three unset so
`huggingface.co` remains reachable for the first classify.
