# OfficeHours AI — Frontend

Two separate React apps:

- **student-kiosk/** — the check-in + request submission interface students use
- **professor-dashboard/** — the triage dashboard professors use to review clustered requests and approve recommended actions

## Planned Setup (per app)

```bash
cd frontend/student-kiosk      # or frontend/professor-dashboard
npm install
npm run dev
```

## Tech
- React
- Tailwind CSS
- Recharts (for dashboard visualizations)

## Status
- **student-kiosk/** — MVP built (Vite + React + Tailwind): anonymous/identified request submission wired to the backend `POST /requests/` endpoint.
- **professor-dashboard/** — scaffolding pending (see GitHub Issue #3).
