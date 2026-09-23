#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY="${HERE}/../../../backend/venv/bin/python"
"$PY" build_figures.py
HTML="file://${HERE}/poster.html"
OUT_PDF="${HERE}/OfficeHours_AI_FYP_Poster.pdf"
OUT_PNG="${HERE}/OfficeHours_AI_FYP_Poster.png"
UD="/tmp/chrome-fyp-poster"
rm -rf "$UD"
mkdir -p "$UD"
timeout 40s google-chrome \
  --headless=new \
  --disable-gpu \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$UD" \
  --hide-scrollbars \
  --no-pdf-header-footer \
  --print-to-pdf="$OUT_PDF" \
  "$HTML"
timeout 45s google-chrome \
  --headless=new \
  --disable-gpu \
  --no-first-run \
  --no-default-browser-check \
  --user-data-dir="$UD" \
  --hide-scrollbars \
  --window-size=2304,3456 \
  --force-device-scale-factor=1 \
  --screenshot="$OUT_PNG" \
  "$HTML"
ls -lh "$OUT_PDF" "$OUT_PNG"
echo "WORD_COUNT $(python3 - <<'PY'
import re, pathlib
html = pathlib.Path("poster.html").read_text()
text = re.sub(r"<style[\s\S]*?</style>", " ", html)
text = re.sub(r"<[^>]+>", " ", text)
words = re.findall(r"[A-Za-z0-9&·×/%.-]+", text)
print(len(words))
PY
)"
