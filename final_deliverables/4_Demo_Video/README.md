# Capstone Demo Video (1920×1080)

Keynote-grade live product walkthrough for OfficeHours AI.

## Outputs

| File | Purpose |
| --- | --- |
| `generate_demo.py` | Playwright recorder + FFmpeg mastering |
| `capstone_demo_1080p.mp4` | Final mastered video (gitignored locally; also copied to Project store) |
| `audit/*.png` | Frame-audit stills (intro / landing / student / TA / professor / outro) |

## Secrets

API keys live only in untracked repo `.env` / `backend/.env` (never committed, never written into this README, store docs, ZIP, MP4 metadata, or logs). The script prints key *presence* flags only.

## Boot (demo seats + Gemini for live Study / Pedagogy / Resources)

```bash
# from repo root — .env already gitignored
set -a && . ./.env && set +a
# backend loads backend/.env via env_bootstrap
./scripts/run_product.sh
```

Confirm: `GET /health` → `demo: true` and Gemini key presence `set`.

Demo seats (password `aui-demo`):

- Student `s.elidrissi@aui.ma`
- TA `a.chen@aui.ma`
- Professor `a.benali@aui.ma`

Course spine: **CSC 2302**.

## Record + master

```bash
cd final_deliverables/4_Demo_Video
.venv/bin/python generate_demo.py
```

Flags: `--skip-record` / `--skip-master` for remaster-only loops.

## Narrative

1. Landing Experience — full opening story scroll → Sign in  
2. Student AI Workspace — Study Agent (refuse + live Q), Pedagogy plan, Quiet ask, My asks, Rooms, Notes  
3. TA Operations — Dashboard, Live Queue (Claim + Help Coach + reply), Past asks  
4. Professor Analytics & Control — Material, Insights, Desk, Team  

Intro / outro cards credit **Sophia Abssi**, supervised by **Dr. Oumaima Hourrane**, **Al Akhawayn University**.
