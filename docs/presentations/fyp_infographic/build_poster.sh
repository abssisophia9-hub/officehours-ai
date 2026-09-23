#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
HTML="file://${HERE}/catalog.html"
OUT_PDF="${HERE}/OfficeHours_AI_Catalog_Poster.pdf"
OUT_PNG="${HERE}/OfficeHours_AI_Catalog_Poster.png"
UD="/tmp/chrome-catalog-design"
rm -rf "$UD"
mkdir -p "$UD"
timeout 40s google-chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$UD" --hide-scrollbars --no-pdf-header-footer \
  --print-to-pdf="$OUT_PDF" "$HTML"
timeout 45s google-chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$UD" --hide-scrollbars \
  --window-size=1392,1824 --force-device-scale-factor=1 \
  --screenshot="$OUT_PNG" "$HTML"
pdfinfo "$OUT_PDF" | rg -i 'Pages|Page size' || true
ls -lh "$OUT_PDF" "$OUT_PNG"
