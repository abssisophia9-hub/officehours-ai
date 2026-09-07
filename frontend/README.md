# OfficeHours AI — Frontend

## Product app (use this)

- **`officehours-app/`** — packaged multi-role product with login + course switcher (port **5180**)

```bash
cd frontend/officehours-app
npm ci
npm run dev
```

Demo password: `aui-demo` **when** `OFFICEHOURS_DEMO=true`  
Accounts: `s.elidrissi@aui.ma`, `a.chen@aui.ma`, `a.benali@aui.ma`  
(AUI email shape: `Initial.Lastname@aui.ma` — role is from membership, not email.)

## Archives (not the product, not in CI)

`student-kiosk/`, `professor-dashboard/`, and `ta-dashboard/` are mid-report
shells kept in the tree. **CI does not build them.** Do not demo them.

Physical kiosk / barcode / NFC hardware is **out of scope**.
