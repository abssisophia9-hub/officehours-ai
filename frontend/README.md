# OfficeHours AI — Frontend

Two separate React apps:

- **student-kiosk/** — the check-in + request submission interface students use
- **professor-dashboard/** — the triage dashboard professors use to review clustered requests and approve recommended actions

## Planned Setup (per app)

```bash
cd frontend/student-kiosk      # or frontend/professor-dashboard
npm ci
npm run dev
```

## Tech
- React
- Tailwind CSS
- Recharts (for dashboard visualizations)

## Status
- **student-kiosk/** — MVP built (Vite + React + Tailwind): anonymous/identified request submission wired to the backend `POST /requests/` endpoint.
- **professor-dashboard/** — MVP built (Vite + React + Tailwind + Recharts): request triage dashboard wired to the backend `GET /requests/` endpoint, with an office-hours setup panel.
