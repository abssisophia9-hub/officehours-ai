# Professor Dashboard — Plan

## MVP built

- Fetches incoming requests from the backend `GET /requests/` endpoint.
- Shows summary cards for request count, pending review, active clusters, and group-session candidates.
- Shows Recharts visualizations for category mix and request clusters.
- Shows a triage table with request text, student identity status, category, cluster, recommended action, and submission time.
- Shows interactive recommendation cards for FAQ, group session, TA/project support, 1:1, admin route, and manual review actions.
- Supports approve / edit / dismiss actions on recommendation cards.
- Calls the backend action engine to generate agenda/status/notification next-step plans.
- Includes an office-hours setup panel where professors specify availability windows.

## Next steps

- Persist office-hour windows through the backend instead of local UI state.
- Add calendar export (`.ics`) for generated agenda items.
- Add a student-facing request-code status page for anonymous students.
- Add request volume over time once the backend returns enough historical data.

Run locally with:

```bash
npm ci
npm run dev
```
