# Diagrams

Generated architecture visuals for OfficeHours AI:

| File | Description |
| --- | --- |
| `architecture.png` | System components: kiosk, dashboard, FastAPI, AI/NLP, orchestration |
| `workflow.png` | End-to-end request → classify → cluster → decide → status flow |
| `database_erd.png` | SQLite entities: requests, recommendation_decisions, office_hours_windows |

Regenerate:

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

Source narrative: `docs/system_architecture.md`.
