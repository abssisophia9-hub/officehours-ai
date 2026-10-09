# OfficeHours AI — Unified Product App

This is the **packaged multi-role product** your supervisor should test:

- guest opening page (Student → TA → Professor story) then **Sign in**
- role detection from course membership (one role per course; TAs are staff)
- course switcher (a user can belong to multiple courses with different roles)
- **Ask Triage** on submit · **Help Coach** in the TA workspace · Study Agent +
  **Rooms** + classmate notes

Legacy separate kiosk/dashboard apps remain as optional web shells only
(**no** physical hardware path), but **this app is the product**.

## Run

```bash
# terminal 1
cd backend
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/uvicorn app.main:app --reload --port 8000

# terminal 2
cd frontend/officehours-app
npm ci
npm run dev
```

Open **one** app: http://127.0.0.1:5180

`./scripts/run_product.sh` sets `OFFICEHOURS_DEMO=true` (demo accounts + sample
Rooms chapters). Community deploy: `OFFICEHOURS_DEMO=false` and live Canvas.

Or use the helper:

```bash
./scripts/run_product.sh
```

## Demo accounts (password `aui-demo`, only if `OFFICEHOURS_DEMO=true`)

AUI format: `Initial.Lastname@aui.ma` — role comes from course membership.

| Email | Roles | Courses (examples) |
| --- | --- | --- |
| `s.elidrissi@aui.ma` | student | ~7 courses (CSC 2302… + MTH 1304 + COM 1301) |
| `a.chen@aui.ma` | **TA** | Staff on CSC 2302 (a course she already took) |
| `b.martinez@aui.ma` | **TA** | Staff on CSC 2302 / 3323 / 3374 |
| `a.benali@aui.ma` | professor | CSC 2302, 3323, 3374 |

Full table: [`docs/product_overview.md`](../../docs/product_overview.md).  
Vocabulary: [`docs/glossary.md`](../../docs/glossary.md).

## Env

`VITE_API_BASE=http://127.0.0.1:8000`
