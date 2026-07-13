# OfficeHours AI

Campus office-hours triage system for **Al Akhawayn University** (FYP).

Students submit questions on a kiosk/browser page. Custom-trained **Oracle**
agents (Analyzer → Matcher → Synthesizer) triage and draft help. TAs and the
professor work in browser dashboards. The professor remains the gate for what
students can retrieve from the knowledge base.

## What is the final product?

A **packaged multi-role campus application** with login:

- students / TAs / professors sign in
- course memberships decide their role per course
- one app workspace (`frontend/officehours-app`)

Not three separate URL demos. Full answer: [`docs/product_overview.md`](docs/product_overview.md).


## Oracle agents (custom-trained)

| Agent | Model | Training data |
| --- | --- | --- |
| Analyzer | embeddings + LogReg | 120 labeled synthetic requests |
| Matcher | embeddings + LogReg | 120 silver TA labels |
| Synthesizer | RAG + style ranker | 50 curated teaching-bank rows |

No prompted Claude / no `USE_MOCK_CLAUDE` on the assessed path. Details:
[`docs/training_data.md`](docs/training_data.md).

## Problem

Finals week floods faculty with repeated questions while some students hesitate
to ask for help.

## Solution highlights

- Anonymous or identified kiosk submission
- Live WebSocket dashboards (professor + TA)
- Custom-trained multi-agent triage
- Professor-approved knowledge base + student KB agent
- Recommendation cards, office hours, `.ics` export

## Tech stack

- React + Tailwind (kiosk `5173`, professor `5174`, TA `5175`)
- FastAPI + SQLAlchemy + SQLite
- sentence-transformers + scikit-learn
- WebSockets for live push

## Repository structure

```
officehours-ai/
├── docs/              # Architecture, product overview, training data, ethics
├── backend/           # FastAPI + custom Oracle models
├── frontend/          # student-kiosk, professor-dashboard, ta-dashboard
├── data/              # Synthetic / silver / curated training CSVs
├── diagrams/          # Architecture, workflow, agents, deployment, ERD
├── reports/           # Mid/final report materials
└── demo/              # Demo scripts / screenshots
```

## Getting started

**Product app (supervisor testing):**

```bash
./scripts/run_product.sh
# open http://127.0.0.1:5180
# password: aui-demo
# student@aui.ma | ta.alice@aui.ma | professor@aui.ma
```

Details: [`docs/product_overview.md`](docs/product_overview.md) ·
[`frontend/officehours-app/README.md`](frontend/officehours-app/README.md)

Backend / legacy frontends: [`backend/README.md`](backend/README.md),
[`frontend/README.md`](frontend/README.md).


## Status

MVP + custom-trained Oracle upgrade on `main`: kiosk, professor/TA dashboards,
KB curation, WebSockets, local ML agents, AUI glass UI, updated diagrams.

## License

MIT — see [LICENSE](LICENSE).
