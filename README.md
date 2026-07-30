# OfficeHours AI

Campus office-hours triage system for **Al Akhawayn University** (FYP).

Students, TAs, and professors use **one packaged web app**. Custom-trained
**Oracle** agents (Analyzer → Matcher → Synthesizer) triage and draft help.
The professor remains the gate for what students can retrieve from the
knowledge base.

## What is the final product?

A **multi-role campus application** with login (or Canvas launch):

- role is **per course** (a TA can also be a student in other courses)
- Quiet ask or Identify me; message / face-to-face / online meeting
- one workspace: `frontend/officehours-app` (port **5180**)

**Community deploy path:** Canvas LTI (not AUI portal scraping, not manual
enrollment as the main model).

Start here:

- [`docs/product_overview.md`](docs/product_overview.md) — how to demo
- [`docs/fyp_evidence.md`](docs/fyp_evidence.md) — what to claim in a defense
- [`docs/project_journey.md`](docs/project_journey.md) — day 1 → this upgrade
- [`docs/system_architecture.md`](docs/system_architecture.md) — components + diagrams
- [`diagrams/`](diagrams/) — architecture / workflow / Canvas / journey PNGs

```bash
./scripts/run_product.sh
# → http://127.0.0.1:5180   password for seeded accounts: aui-demo
```


## Oracle agents (custom-trained)

| Agent | Model | Training data |
| --- | --- | --- |
| Analyzer | embeddings + LogReg | Labeled synthetic + CSC topic rows |
| Matcher | embeddings + LogReg | Silver TA labels + CSC supplement |
| Synthesizer | RAG + style ranker | Teaching-bank + CSC supplement |

No prompted Claude / no `USE_MOCK_CLAUDE` on the assessed path. Details:
[`docs/training_data.md`](docs/training_data.md),
[`docs/agent_performance.md`](docs/agent_performance.md).

## Problem

Finals week floods faculty with repeated questions while some students hesitate
to ask for help.

## Solution highlights

- Anonymous or identified asks
- Face-to-face / online meeting preference for staff scheduling
- Live WebSocket queues (TA + professor)
- Custom-trained multi-agent triage
- Professor-approved knowledge base + student KB agent
- Canvas materials sync + launch provisioning (LTI hardening next)

## Tech stack

- React + Tailwind — product app `5180` (legacy kiosk `5173`, professor `5174`, TA `5175`)
- FastAPI + SQLAlchemy + SQLite
- sentence-transformers + scikit-learn
- WebSockets for live push
