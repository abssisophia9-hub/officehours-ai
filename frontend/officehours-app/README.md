# OfficeHours AI — Unified Product App

This is the **packaged multi-role product** your supervisor should test:

- one login screen
- role detection from course membership (student / TA / professor)
- course switcher (a user can belong to multiple courses with different roles)
- **Ask Triage** on submit · **Help Coach** in the TA workspace · Study Agent +
  Stuck Room + classmate notes

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

Or use the helper:

```bash
./scripts/run_product.sh
```

## Demo accounts (password `aui-demo`)

AUI format: `Initial.Lastname@aui.ma` — role comes from course membership.

| Email | Roles | Courses (examples) |
| --- | --- | --- |
| `s.elidrissi@aui.ma` | student | ~7 courses (CSC 2302… + MTH 1304 + COM 1301) |
| `a.chen@aui.ma` | **TA + student** | TA of CSC 2302; student in other courses |
| `b.martinez@aui.ma` | **TA + student** | TA of CSC 2302 / 3323 / 3374; student elsewhere |
| `a.benali@aui.ma` | professor | CSC 2302, 3323, 3374 |

Full table: [`docs/product_overview.md`](../../docs/product_overview.md).  
Vocabulary: [`docs/glossary.md`](../../docs/glossary.md).

## Env

`VITE_API_BASE=http://127.0.0.1:8000`
