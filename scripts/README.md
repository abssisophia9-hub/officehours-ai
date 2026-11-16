# Scripts

| Script | Purpose |
| --- | --- |
| `run_product.sh` | Start backend + unified product app (`:8000` + `:5180`). Defaults `OFFICEHOURS_DEMO=true`. |
| `start-backend.ps1` | Windows: run uvicorn from `backend\venv` with demo defaults. |
| `start-frontend.ps1` | Windows: `npm run dev` from `frontend\officehours-app` only. |
| `generate_architecture_diagrams.py` | Regenerate PNGs under `diagrams/` (Ask Triage labels) |

```bash
./scripts/run_product.sh
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

```powershell
# Windows — two terminals from repo root
.\scripts\start-backend.ps1
.\scripts\start-frontend.ps1
```

See [`docs/glossary.md`](../docs/glossary.md) and [`diagrams/README.md`](../diagrams/README.md).
