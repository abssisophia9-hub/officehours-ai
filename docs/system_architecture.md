# System Architecture

## Overview
OfficeHours AI consists of four main components:

1. **Student Kiosk (frontend/student-kiosk)** — QR/NFC check-in + request submission UI
2. **Professor Dashboard (frontend/professor-dashboard)** — request triage, clustering view, recommendation cards
3. **Backend API (backend/)** — FastAPI service handling auth, requests, classification, clustering
4. **AI/NLP Layer (backend/app/ai)** — classification model, embedding generation, clustering logic

## Data Flow
1. Student submits a request via kiosk (anonymous or identified)
2. Request is sent to backend `/requests` endpoint
3. AI layer classifies request type + generates embedding
4. Clustering service groups it with similar existing requests
5. Recommendation engine suggests an action (FAQ / group session / TA / 1:1 / admin)
6. Professor dashboard displays clustered requests + recommended actions
7. Professor approves/edits the action; system logs outcome

## Diagram
See `diagrams/architecture.png` (to be added).

## Tech Stack Rationale
- **FastAPI**: async-friendly, fast to prototype, good typing support
- **SQLAlchemy + SQLite/Postgres**: easy local dev, swappable to Postgres for deployment
- **sentence-transformers + cosine similarity**: lightweight, no fine-tuning required for MVP clustering
- **React + Tailwind**: fast UI iteration for both kiosk and dashboard
