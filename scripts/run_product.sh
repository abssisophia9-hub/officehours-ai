#!/usr/bin/env bash
# Launch the packaged OfficeHours AI product (backend + unified app).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

export OFFICEHOURS_CLUSTERING_BACKEND="${OFFICEHOURS_CLUSTERING_BACKEND:-lexical}"
# Local FYP walkthroughs. Community deploy: OFFICEHOURS_DEMO=false and live Canvas.
export OFFICEHOURS_DEMO="${OFFICEHOURS_DEMO:-true}"
# Study Agent calls a provider only when that provider is selected.
# Gemini also needs the free-tier acknowledgement and GEMINI_API_KEY.
# A key by itself stays retrieval-only. Demo off refuses the call.
if [[ -z "${OFFICEHOURS_ALLOW_EXTERNAL_LLM+x}" ]]; then
  if [[ ( "${OFFICEHOURS_DEMO}" == "true" || "${OFFICEHOURS_DEMO}" == "1" ) \
      && "${OFFICEHOURS_LLM_PROVIDER:-}" == "gemini" \
      && ( "${OFFICEHOURS_GEMINI_FREE_TIER_ACK:-}" == "true" || "${OFFICEHOURS_GEMINI_FREE_TIER_ACK:-}" == "1" ) \
      && -n "${GEMINI_API_KEY:-}" ]]; then
    export OFFICEHOURS_ALLOW_EXTERNAL_LLM=true
  elif [[ ( "${OFFICEHOURS_DEMO}" == "true" || "${OFFICEHOURS_DEMO}" == "1" ) \
      && "${OFFICEHOURS_LLM_PROVIDER:-}" == "claude" \
      && -n "${ANTHROPIC_API_KEY:-}" ]]; then
    export OFFICEHOURS_ALLOW_EXTERNAL_LLM=true
  else
    export OFFICEHOURS_ALLOW_EXTERNAL_LLM=false
  fi
fi
# The policy kill switch stays off until a provider call is actually armed.
if [[ -z "${OFFICEHOURS_LLM_ENABLED+x}" ]]; then
  if [[ "${OFFICEHOURS_ALLOW_EXTERNAL_LLM}" == "true" ]]; then
    export OFFICEHOURS_LLM_ENABLED=true
  else
    export OFFICEHOURS_LLM_ENABLED=false
  fi
fi

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
echo "  Demo mode     : ${OFFICEHOURS_DEMO} (set OFFICEHOURS_DEMO=false for community deploy)"
if [[ "${OFFICEHOURS_DEMO}" == "true" || "${OFFICEHOURS_DEMO}" == "1" ]]; then
  echo "  Demo password: aui-demo"
  echo "  Logins: s.elidrissi@aui.ma | a.chen@aui.ma | a.benali@aui.ma"
  echo "  (AUI emails: Initial.Last@aui.ma — role from course membership)"
  if [[ "${OFFICEHOURS_LLM_ENABLED:-}" == "true" && "${OFFICEHOURS_ALLOW_EXTERNAL_LLM}" == "true" && "${OFFICEHOURS_LLM_PROVIDER:-}" == "gemini" ]]; then
    echo "  Study Agent: Gemini answer check on synthetic demo material (key is not printed)"
  elif [[ "${OFFICEHOURS_LLM_ENABLED:-}" == "true" && "${OFFICEHOURS_ALLOW_EXTERNAL_LLM}" == "true" && "${OFFICEHOURS_LLM_PROVIDER:-}" == "claude" ]]; then
    echo "  Study Agent: Claude answer check on synthetic demo material (key is not printed)"
  else
    echo "  Study Agent: retrieval only. For Gemini set GEMINI_API_KEY, OFFICEHOURS_LLM_PROVIDER=gemini, OFFICEHOURS_GEMINI_FREE_TIER_ACK=true, and OFFICEHOURS_LLM_ENABLED=true."
  fi
else
  echo "  Community deploy: users/courses from Canvas; chapters from Canvas modules."
fi
echo ""
wait
