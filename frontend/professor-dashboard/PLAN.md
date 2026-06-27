# Professor Dashboard — Plan

## MVP built

- Fetches incoming requests from the backend `GET /requests/` endpoint.
- Shows summary cards for request count, pending review, active clusters, and group-session candidates.
- Shows Recharts visualizations for category mix and request clusters.
- Shows a triage table with request text, student identity status, category, cluster, recommended action, and submission time.
- Includes an office-hours setup panel where professors specify availability windows.

## Next steps

- Persist office-hour windows through the backend instead of local UI state.
- Add approve / edit / dismiss actions for recommendations.
- Add richer recommendation cards (FAQ / group session / TA / 1:1 / admin route).
- Add request volume over time once the backend returns enough historical data.

Run locally with:

```bash
npm ci
npm run dev
```
