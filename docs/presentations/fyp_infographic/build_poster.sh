#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
PY="${HERE}/../../../backend/venv/bin/python"
"$PY" fill_catalog_poster.py

HTML="file://${HERE}/poster.html"
OUT_PDF="${HERE}/OfficeHours_AI_FYP_Poster.pdf"
OUT_PNG="${HERE}/OfficeHours_AI_FYP_Poster.png"
UD="/tmp/chrome-fyp-poster"
rm -rf "$UD"
mkdir -p "$UD"
timeout 40s google-chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$UD" --hide-scrollbars --no-pdf-header-footer \
  --print-to-pdf="$OUT_PDF" "$HTML"
timeout 45s google-chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$UD" --hide-scrollbars \
  --window-size=2304,3456 --force-device-scale-factor=1 \
  --screenshot="$OUT_PNG" "$HTML"
pdfinfo "$OUT_PDF" | rg -i 'Pages|Page size' || true
pdfinfo "${HERE}/OfficeHours_AI_Catalog_Poster.pdf" | rg -i 'Pages|Page size' || true
echo "ports leftover:"
rg -n ':[0-9]{3,5}' poster.html fill_catalog_poster.py build_catalog_figures.py || echo "none"
ls -lh "$OUT_PDF" "$OUT_PNG" "${HERE}/OfficeHours_AI_Catalog_Poster".{docx,pdf}
