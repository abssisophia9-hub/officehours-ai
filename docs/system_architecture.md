# System Architecture

## Overview
OfficeHours AI consists of four main components:

1. **Student Kiosk (frontend/student-kiosk)** — QR/NFC check-in + request submission UI
2. **Professor Dashboard (frontend/professor-dashboard)** — request triage, clustering view, recommendation cards, professor office-hours setup
3. **Backend API (backend/)** — FastAPI service handling auth, requests, classification, clustering, professor decisions, and action plans
4. **AI/NLP Layer (backend/app/ai)** — classification model, embedding generation, clustering logic
5. **Action Orchestration Layer (backend/app/services)** — turns professor decisions into agenda, calendar, and student-status plans

## Data Flow
1. Professor configures office-hour windows in the dashboard settings/availability panel
2. Backend persists those office-hour windows so scheduling and recommendation logic can use them
3. Student submits a request via kiosk (anonymous or identified)
4. Request is sent to backend `/requests` endpoint
5. AI layer classifies request type + generates embedding
6. Clustering service groups it with similar existing requests
7. Recommendation engine suggests an action (FAQ / group session / TA / 1:1 / admin) using request context and professor availability
8. Professor dashboard displays clustered requests + recommended actions
9. Professor approves/edits/dismisses the action
10. Action orchestration generates a concrete next-step plan:
    - office-hours agenda item
    - student status update
    - calendar/export suggestion
    - privacy-safe delivery guidance for anonymous vs. identified students
11. System logs the professor decision and generated action plan

## Decision-to-action automation
The project should not stop at categorized and clustered requests. The next
layer is an action orchestration engine:

1. Recommendation card is approved, edited, or dismissed by the professor.
2. Backend stores the professor decision.
3. NLP summarization extracts cluster keywords and a readable action title.
4. The action engine creates a plan for:
   - group review sessions
   - FAQ/status updates
   - priority 1:1 follow-up
   - TA/project support blocks
   - private admin/grading/accommodation routes
5. Anonymous students receive request-code/status-board guidance, while
   identified students can later receive direct notifications.

This preserves open office hours: agenda blocks organize the room without
turning every student interaction into a strict appointment.

## Professor office-hours configuration
Professor office hours belong in the **Professor Dashboard** as an availability/settings workflow, backed by the **Backend API** as persisted scheduling data (`/office-hours` CRUD). Recommendation calendar export (`.ics`) uses these windows to place agenda blocks on real availability.

## Diagrams
- `diagrams/architecture.png` — system components
- `diagrams/workflow.png` — end-to-end request workflow
- `diagrams/database_erd.png` — SQLite entity relationships

Regenerate with `backend/venv/bin/python scripts/generate_architecture_diagrams.py`.

## Tech Stack Rationale
- **FastAPI**: async-friendly, fast to prototype, good typing support
- **SQLAlchemy + SQLite/Postgres**: easy local dev, swappable to Postgres for deployment
- **sentence-transformers + cosine similarity**: lightweight, no fine-tuning required for MVP clustering
- **React + Tailwind**: fast UI iteration for both kiosk and dashboard
