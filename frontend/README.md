# OfficeHours AI — Frontend

Three **browser** React apps (not a native desktop installer):

| App | Port | Audience |
| --- | --- | --- |
| `student-kiosk/` | **5173** | Students (shared kiosk device or personal browser) |
| `professor-dashboard/` | **5174** | Professor desktop browser |
| `ta-dashboard/` | **5175** | TA desktop browser |

There is no SSO login yet — demo mode assumes trusted campus demo devices /
staff pick their TA name in the UI.

## Setup (per app)

```bash
cd frontend/student-kiosk      # or professor-dashboard / ta-dashboard
npm ci
npm run dev
```

Set `VITE_API_BASE=http://127.0.0.1:8000` (see each app's `.env.example`).

Professor and TA dashboards connect to `ws://127.0.0.1:8000/ws` for live updates.

## Visual design

AUI-branded glassmorphism: official logo, forest/teal/sand color atmosphere,
Fraunces + Sora typography, frosted panels, hover motion.

## Status

- **student-kiosk/** — check-in, Oracle submit confirmation, status lookup, KB agent
- **professor-dashboard/** — live triage, Oracle metrics, KB curation, heatmap, escalations
- **ta-dashboard/** — live queue, teaching draft editor, resolve → `pending_review`
