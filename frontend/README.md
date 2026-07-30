# OfficeHours AI — Frontend

## Product app (use this)

- **`officehours-app/`** — packaged multi-role product with login + course switcher (port **5180**)

```bash
cd frontend/officehours-app
npm ci
npm run dev
```

Demo password: `aui-demo`  
Accounts: `s.elidrissi@aui.ma`, `a.chen@aui.ma`, `a.benali@aui.ma`  
(AUI email shape: `Initial.Lastname@aui.ma` — role is from membership, not email.)

## Legacy specialized apps (optional)

Older single-role web shells kept for reference only — **not** a hardware path:

| App | Port | Notes |
| --- | --- | --- |
| `student-kiosk/` | 5173 | Shared-device web flow without account login |
| `professor-dashboard/` | 5174 | Legacy professor-only shell |
| `ta-dashboard/` | 5175 | Legacy TA-only shell |

Prefer **`officehours-app`** for supervisor testing. Physical kiosk / barcode /
NFC hardware is **out of scope**.
