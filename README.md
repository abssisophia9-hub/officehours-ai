# OfficeHours AI

Campus office-hours triage system for **Al Akhawayn University** (FYP).

Students submit questions on a kiosk/browser page. Custom-trained **Oracle**
agents (Analyzer → Matcher → Synthesizer) triage and draft help. TAs and the
professor work in browser dashboards. The professor remains the gate for what
students can retrieve from the knowledge base.

## What is the final product?

A **web system** (three React apps + FastAPI), not a native desktop App Store
app and not AUI SSO login yet. Demo day = run backend + open the three URLs on
campus devices. Full answer: [`docs/product_overview.md`](docs/product_overview.md).

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

- Backend: [`backend/README.md`](backend/README.md)
- Frontends: [`frontend/README.md`](frontend/README.md)
- Architecture: [`docs/system_architecture.md`](docs/system_architecture.md)

## Status

MVP + custom-trained Oracle upgrade on `main`: kiosk, professor/TA dashboards,
KB curation, WebSockets, local ML agents, AUI glass UI, updated diagrams.

## License

MIT — see [LICENSE](LICENSE).
