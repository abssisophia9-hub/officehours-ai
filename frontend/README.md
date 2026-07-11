# OfficeHours AI — Frontend

Three separate React apps:

- **student-kiosk/** — check-in, request submission, status lookup, and KB agent (port **5173**)
- **professor-dashboard/** — triage, KB curation, heatmap, escalations (port **5174**)
- **ta-dashboard/** — live TA queue; resolutions feed the professor curation queue (port **5175**)

## Setup (per app)

```bash
cd frontend/student-kiosk      # or professor-dashboard / ta-dashboard
npm ci
npm run dev
```

Set `VITE_API_BASE=http://127.0.0.1:8000` (see each app's `.env.example`).

Professor and TA dashboards connect to `ws://127.0.0.1:8000/ws` for live updates (green **Live** indicator).

## Tech
- React
- Tailwind CSS
- Recharts (professor dashboard)
- WebSockets for live queue/curation updates

## Status
- **student-kiosk/** — MVP: barcode/manual check-in, anonymous/identified submit, status lookup, KB agent chat.
- **professor-dashboard/** — MVP: triage, recommendation cards, office hours, KB curation, struggle heatmap, escalations, WebSocket refresh.
- **ta-dashboard/** — MVP: live queue, learning-style–aware teaching drafts, resolve → `pending_review` curation queue.
