# Diagrams

Generated visuals for the **unified product + Canvas** era. Narrative:
[`docs/project_journey.md`](../docs/project_journey.md).

| File | Description |
| --- | --- |
| `platform_architecture.png` | **Complete platform** — all 5 layers, core services, databases, external integrations, role paths, and numbered data flows |
| `architecture.png` | Product app + FastAPI + Canvas + Analyzer/Matcher/Synthesizer + Rooms + curation |
| `workflow.png` | Identity + help mode → Ask Triage → TA → professor → KB / meetings |
| `oracle_agents.png` | Ask Triage Analyzer / Matcher / Synthesizer (filename historical) |
| `product_deployment.png` | Canvas-first community deploy vs portal / manual |
| `database_erd.png` | Auth, memberships, requests (`help_mode`), KB, roster |
| `canvas_enrollment.png` | JIT Canvas launch + per-course role (TA is staff) |
| `project_journey.png` | Phase timeline from proposal to this upgrade |

Regenerate:

```bash
backend/venv/bin/python scripts/generate_architecture_diagrams.py
```

Related docs:

- `docs/system_architecture.md`
- `docs/product_overview.md`
- `docs/project_journey.md`
- `docs/training_data.md`
- `docs/ai_nlp_design.md`
- `docs/agent_performance.md`
