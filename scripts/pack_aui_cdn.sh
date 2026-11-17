#!/usr/bin/env bash
# Build officehours-ai-aui-cdn.zip from the current tip (prebuilt CDN dist required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${1:-$ROOT/dist-aui-cdn}"
STAGE="$OUT_DIR/officehours-ai-aui-cdn"
ZIP_PATH="${2:-$OUT_DIR/officehours-ai-aui-cdn.zip}"

rm -rf "$STAGE"
mkdir -p "$STAGE"

# Frontend must already be built with VITE_ROOT_PATH=/officehours-ai
DIST="$ROOT/frontend/officehours-app/dist"
if [[ ! -f "$DIST/index.html" ]]; then
  echo "Missing $DIST/index.html — build with VITE_ROOT_PATH=/officehours-ai first" >&2
  exit 1
fi
if ! grep -q '/officehours-ai/assets/' "$DIST/index.html"; then
  echo "dist/index.html is not a CDN-prefixed build (expected /officehours-ai/assets/)" >&2
  exit 1
fi

copy_tree() {
  local src="$1" dest="$2"
  mkdir -p "$(dirname "$dest")"
  rsync -a --delete \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '.venv/' \
    --exclude '__pycache__/' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache/' \
    --exclude 'node_modules/' \
    --exclude '.env' \
    --exclude '.env.local' \
    --exclude '*.db' \
    --exclude '*.sqlite3' \
    --exclude 'peer_notes/' \
    --exclude 'resources_cache.json' \
    --exclude 'resources_cache.tmp' \
    --exclude 'screenshots/' \
    --exclude 'evidence/' \
    --exclude 'media/' \
    --exclude 'production-fix/' \
    --exclude '*.screenshot.png' \
    "$src" "$dest"
}

# Core app
copy_tree "$ROOT/backend/app/" "$STAGE/backend/app/"
copy_tree "$ROOT/backend/tests/" "$STAGE/backend/tests/"
copy_tree "$ROOT/backend/scripts/" "$STAGE/backend/scripts/"
copy_tree "$ROOT/backend/demo_data/" "$STAGE/backend/demo_data/"
copy_tree "$ROOT/backend/models/" "$STAGE/backend/models/"
cp -a "$ROOT/backend/requirements.txt" "$STAGE/backend/requirements.txt"
cp -a "$ROOT/backend/README.md" "$STAGE/backend/README.md"
cp -a "$ROOT/backend/.env.example" "$STAGE/backend/.env.example"
# Empty data dirs (no peer_notes contents)
mkdir -p "$STAGE/backend/data"
printf '%s\n' '# Runtime uploads (peer notes) — created on first demo seed; do not ship files.' \
  > "$STAGE/backend/data/README.md"

# Product frontend only (no legacy dashboards)
mkdir -p "$STAGE/frontend/officehours-app"
rsync -a \
  --exclude 'node_modules/' \
  --exclude '.env' \
  --exclude '.env.local' \
  "$ROOT/frontend/officehours-app/src/" "$STAGE/frontend/officehours-app/src/"
cp -a "$ROOT/frontend/officehours-app/index.html" \
  "$ROOT/frontend/officehours-app/package.json" \
  "$ROOT/frontend/officehours-app/package-lock.json" \
  "$ROOT/frontend/officehours-app/vite.config.js" \
  "$ROOT/frontend/officehours-app/README.md" \
  "$ROOT/frontend/officehours-app/.env.example" \
  "$STAGE/frontend/officehours-app/"
# Optional config files if present
for f in postcss.config.js postcss.config.mjs eslint.config.js jsconfig.json \
  components.json index.css; do
  [[ -e "$ROOT/frontend/officehours-app/$f" ]] && cp -a "$ROOT/frontend/officehours-app/$f" "$STAGE/frontend/officehours-app/"
done
rsync -a "$DIST/" "$STAGE/frontend/officehours-app/dist/"

# Training / seed CSVs
copy_tree "$ROOT/data/" "$STAGE/data/"

# Docs linked from README (+ deploy guides)
mkdir -p "$STAGE/docs"
README_DOCS=(
  docs/product_overview.md
  docs/glossary.md
  docs/README.md
  docs/SECURITY.md
  docs/training_data.md
  docs/fyp_evidence.md
  docs/AGENT_POLICY.md
  docs/DEMO.md
  docs/canvas_live_test.md
  docs/ops_scale.md
)
for rel in "${README_DOCS[@]}"; do
  cp -a "$ROOT/$rel" "$STAGE/$rel"
done

# Top-level package files
cp -a "$ROOT/README.md" "$STAGE/README.md"
cp -a "$ROOT/AGENTS.md" "$STAGE/AGENTS.md"
cp -a "$ROOT/LICENSE" "$STAGE/LICENSE"
cp -a "$ROOT/DEPLOY.md" "$STAGE/DEPLOY.md"
cp -a "$ROOT/.env.production.example" "$STAGE/.env.production.example"
cp -a "$ROOT/docker-compose.postgres.yml" "$STAGE/docker-compose.postgres.yml"
cp -a "$ROOT/.gitignore" "$STAGE/.gitignore"

# Root requirements helpers (CPU torch note)
cp -a "$ROOT/backend/requirements.txt" "$STAGE/requirements.txt"
cat > "$STAGE/requirements-cpu-torch.txt" <<'EOF'
# Install CPU torch BEFORE requirements.txt on hosts without NVIDIA:
#   pip install torch --index-url https://download.pytorch.org/whl/cpu
# Then:
#   pip install -r requirements.txt
# Do not pip install torch from PyPI afterward (CUDA wheel may replace CPU).
EOF

mkdir -p "$STAGE/scripts" "$STAGE/deploy"
cp -a "$ROOT/scripts/run_product.sh" "$STAGE/scripts/run_product.sh"
cp -a "$ROOT/scripts/start-backend.ps1" "$STAGE/scripts/start-backend.ps1"
cp -a "$ROOT/scripts/start-frontend.ps1" "$STAGE/scripts/start-frontend.ps1"
cp -a "$ROOT/deploy/IT_SMOKE_TEST.md" "$STAGE/deploy/IT_SMOKE_TEST.md"
[[ -f "$ROOT/deploy/README.md" ]] && cp -a "$ROOT/deploy/README.md" "$STAGE/deploy/README.md"

# Record tip
git -C "$ROOT" rev-parse HEAD > "$STAGE/deploy/GIT_COMMIT.txt"
git -C "$ROOT" log -1 --oneline >> "$STAGE/deploy/GIT_COMMIT.txt"

# Safety scan: refuse secrets / peer_notes / legacy frontends / reports
if find "$STAGE" -type f \( -name '.env' -o -name '*.db' -o -name '*.sqlite3' \) | grep -q .; then
  echo "Refusing to pack secrets or db files" >&2
  exit 1
fi
if [[ -d "$STAGE/backend/data/peer_notes" ]] && find "$STAGE/backend/data/peer_notes" -type f | grep -q .; then
  echo "Refusing to pack peer_notes files" >&2
  exit 1
fi
for banned in student-kiosk professor-dashboard ta-dashboard reports notebooks; do
  if find "$STAGE" -type d -name "$banned" | grep -q .; then
    echo "Refusing to pack banned path: $banned" >&2
    exit 1
  fi
done

mkdir -p "$(dirname "$ZIP_PATH")"
rm -f "$ZIP_PATH"
( cd "$OUT_DIR" && zip -qr "$(basename "$ZIP_PATH")" officehours-ai-aui-cdn )
echo "Wrote $ZIP_PATH ($(du -h "$ZIP_PATH" | awk '{print $1}'))"
find "$STAGE" -type f | sed "s|^$STAGE/||" | sort > "$OUT_DIR/aui-cdn-file-list.txt"
echo "File list: $OUT_DIR/aui-cdn-file-list.txt ($(wc -l < "$OUT_DIR/aui-cdn-file-list.txt") files)"
