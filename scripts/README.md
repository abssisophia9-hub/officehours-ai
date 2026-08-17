# Scripts

| Script | Purpose |
| --- | --- |
| `run_product.sh` | Start backend + unified product app (`:8000` + `:5180`). Defaults `OFFICEHOURS_DEMO=true`. |
| `generate_architecture_diagrams.py` | Regenerate PNGs under `diagrams/` (Ask Triage labels) |

```bash
./scripts/run_product.sh
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

See [`docs/glossary.md`](../docs/glossary.md) and [`diagrams/README.md`](../diagrams/README.md).
