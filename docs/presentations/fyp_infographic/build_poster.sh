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
timeout 50s google-chrome \
  --headless=new --disable-gpu --no-first-run --no-default-browser-check \
  --user-data-dir="$UD" --hide-scrollbars --no-pdf-header-footer \
  --print-to-pdf="$OUT_PDF" "$HTML"
if command -v pdftoppm >/dev/null 2>&1; then
  pdftoppm -png -r 150 "$OUT_PDF" /tmp/officehours-poster
  cp -f /tmp/officehours-poster-1.png "$OUT_PNG"
else
  timeout 130s google-chrome \
    --headless=new --disable-gpu --no-first-run --no-default-browser-check \
    --user-data-dir="$UD" --hide-scrollbars \
    --window-size=2176,2848 --force-device-scale-factor=1 \
    --screenshot="$OUT_PNG" "$HTML" || true
fi
pdfinfo "$OUT_PDF" | rg -i 'Pages|Page size' || true
cp -f "$OUT_PDF" "${HERE}/OfficeHours_AI_Proposal_Poster.pdf"
cp -f "$OUT_PNG" "${HERE}/OfficeHours_AI_Proposal_Poster.png"
cp -f "$OUT_PDF" "${HERE}/OfficeHours_AI_FYP_Poster.pdf"
cp -f "$OUT_PNG" "${HERE}/OfficeHours_AI_FYP_Poster.png"
cp -f "$OUT_PDF" "${HERE}/OfficeHours_AI_Proposal_WorkPlan.pdf"
cp -f "$OUT_PNG" "${HERE}/OfficeHours_AI_Proposal_WorkPlan.png"
cp -f "$OUT_PDF" "${HERE}/OfficeHours_AI_Proposal_Agents.pdf"
cp -f "$OUT_PNG" "${HERE}/OfficeHours_AI_Proposal_Agents.png"
cp -f "$OUT_PDF" "${HERE}/OfficeHours_AI_Proposal_Aligned.pdf"
cp -f "$OUT_PNG" "${HERE}/OfficeHours_AI_Proposal_Aligned.png"
ls -lh "$OUT_PDF" "$OUT_PNG" "${HERE}/OfficeHours_AI_Proposal_Aligned.pdf"
