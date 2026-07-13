# Diagrams

Generated visuals for the **custom-trained Oracle** upgrade:

| File | Description |
| --- | --- |
| `architecture.png` | Three browser apps + FastAPI + Analyzer/Matcher/Synthesizer + curation gate |
| `workflow.png` | End-to-end submit → Oracle → TA → professor → student KB |
| `oracle_agents.png` | Per-agent models, training sizes, artifacts |
| `product_deployment.png` | What the final product is / is not |
| `database_erd.png` | SQLite ERD including KB, TA roster, Oracle fields |

Regenerate:

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

Narrative docs:

- `docs/system_architecture.md`
- `docs/product_overview.md`
- `docs/training_data.md`
- `docs/ai_nlp_design.md`
