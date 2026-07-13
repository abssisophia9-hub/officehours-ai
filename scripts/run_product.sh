#!/usr/bin/env bash
# Launch the packaged OfficeHours AI product (backend + unified app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export OFFICEHOURS_CLUSTERING_BACKEND="${OFFICEHOURS_CLUSTERING_BACKEND:-lexical}"
export OFFICEHOURS_ALLOW_EXTERNAL_LLM="${OFFICEHOURS_ALLOW_EXTERNAL_LLM:-false}"

cd "$ROOT/backend"
if [[ ! -x venv/bin/uvicorn ]]; then
  echo "Missing backend/venv. Create it and pip install -r requirements.txt first."
  exit 1
fi

venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACK_PID=$!

cd "$ROOT/frontend/officehours-app"
if [[ ! -d node_modules ]]; then
  npm ci
fi
npm run dev -- --host 127.0.0.1 --port 5180 &
FRONT_PID=$!

cleanup() {
  kill "$BACK_PID" "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo ""
echo "OfficeHours AI product is starting:"
echo "  Backend API : http://127.0.0.1:8000"
echo "  Product app : http://127.0.0.1:5180"
echo "  Demo password: aui-demo"
echo "  Logins: student@aui.ma | ta.alice@aui.ma | professor@aui.ma"
echo ""
wait
