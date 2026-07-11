# OfficeHours AI

OfficeHours AI is a smart AI-powered office-hours triage system designed to help faculty manage finals-week student requests more efficiently while making help-seeking easier for students.

## Problem

During final exam periods, professors often receive a sudden overload of emails, Teams messages, office-hour requests, repeated academic questions, and retake/admin cases. At the same time, some students hesitate to contact professors directly because they feel shy, socially anxious, or unsure how to explain their confusion.

## Proposed Solution

OfficeHours AI provides a QR/NFC-enabled kiosk and web dashboard where students can submit academic requests anonymously or with identification. The AI classifies requests, groups repeated questions, infers learning style for teaching drafts, and recommends actions such as:

- quick FAQ response
- group review session
- TA-led review session
- one-to-one meeting
- admin/retake route

The professor remains in control and approves all final actions.

## Main Features

- QR/NFC student check-in
- Anonymous question submission
- AI request classification
- Similar question clustering
- Learning preference analysis
- Professor dashboard
- Action recommendations
- Calendar/session suggestions
- Finals-week demo scenario

## Tech Stack

### Frontend
- React
- Tailwind CSS
- Recharts

### Backend
- Python
- FastAPI
- SQLAlchemy
- SQLite / PostgreSQL

### AI/NLP
- LLM API or local NLP model
- sentence-transformers
- scikit-learn
- cosine similarity clustering

### Hardware
- NFC reader
- QR scanner
- laptop/tablet or Raspberry Pi kiosk

## Repository Structure

```
officehours-ai/
├── docs/              # Proposal, architecture, ethics, evaluation plans
├── backend/           # FastAPI app, routes, models, services, AI logic
├── frontend/          # Student kiosk + professor dashboard (React)
├── hardware/          # NFC/QR integration code + setup guide
├── data/              # Synthetic and labeled request datasets
├── notebooks/         # AI/NLP experimentation notebooks
├── diagrams/          # Architecture, workflow, and ERD diagrams
├── reports/           # Mid report, final report, paper draft
└── demo/              # Screenshots, demo script, video notes
```

## Getting Started

See [`backend/README.md`](backend/README.md) and [`frontend/README.md`](frontend/README.md) for setup instructions for each part of the stack.

## Research Question

Can an AI-assisted office-hours triage system reduce faculty communication overload and improve student comfort in seeking academic help during final exam periods?

## Status

MVP complete: student kiosk, professor dashboard, TA dashboard, curated knowledge
base + student KB agent, learning-style–aware teaching drafts, WebSockets, survey
evaluation, and LaTeX reports. See PR history and `reports/final_report/`.

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
