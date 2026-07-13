# OfficeHours AI — Frontend

## Product app (use this)

- **`officehours-app/`** — packaged multi-role product with login + course switcher (port **5180**)

```bash
cd frontend/officehours-app
npm ci
npm run dev
```

Demo password: `aui-demo`  
Accounts: `student@aui.ma`, `ta.alice@aui.ma`, `professor@aui.ma`

## Legacy specialized apps (optional)

These remain for hardware kiosk / isolated dashboard experiments:

| App | Port | Notes |
| --- | --- | --- |
| `student-kiosk/` | 5173 | Shared-device kiosk flow without account login |
| `professor-dashboard/` | 5174 | Legacy professor-only shell |
| `ta-dashboard/` | 5175 | Legacy TA-only shell |

Prefer **`officehours-app`** for supervisor testing.
