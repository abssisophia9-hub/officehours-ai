# CFC Capstone E-Poster (9:16 portrait)

**Route:** `/poster` (public, no login)  
**Canvas:** fixed `1080×1920` stage, scaled to the viewport, zero page scroll  
**Palette:** Travertine `#F9F7F3` · AUI Emerald `#006838` · Canvas Blue `#008EE2` · Slate Ink `#2D3B45` · CFC Brass `#C59B5F`

## Local

```bash
./scripts/run_product.sh
# → http://127.0.0.1:5180/poster
```

Open `/poster` and press F11 for full-screen showcase.

## Contents (verified from repo)

1. Problem & motivation  
2. Multi-role surfaces from `AppShell` / page files  
3. Architecture toggle: `public/architecture-diagram.png` (from `diagrams/platform_architecture.png`) · Repository: `public/github-repo-diagram.png` + click-to-zoom  
4. Pipelines citing `ask_triage_service`, `kb_agent_service` / `agent_policy`, `help_coach_service`, `revision_service` / `course_ta_service`  
5. Benchmarks from `reports/final_report/*` + `docs/eval_results/with_check_*` + `test_no_ta_routing.py`  
6. Triage support bars + QR → GitHub · `./scripts/run_product.sh`

## Files

- `frontend/officehours-app/src/pages/CapstonePosterPage.jsx`
- `frontend/officehours-app/src/pages/capstone-poster.css`
- `frontend/officehours-app/public/architecture-diagram.png`
- `frontend/officehours-app/public/github-repo-diagram.png`
- `frontend/officehours-app/public/poster-demo-qr.png`
