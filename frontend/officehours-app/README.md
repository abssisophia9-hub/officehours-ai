# OfficeHours AI — Unified Product App

This is the **packaged multi-role product** your supervisor should test:

- one login screen
- role detection from course membership (student / TA / professor)
- course switcher (a user can belong to multiple courses with different roles)

Legacy separate kiosk/dashboard apps remain for hardware demos, but **this app is the product**.

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

| Email | Role | Courses |
| --- | --- | --- |
| `student@aui.ma` | student | CS 400, CS 330 |
| `ta.alice@aui.ma` | TA | CS 400 |
| `ta.bob@aui.ma` | TA | CS 400, CS 330 |
| `professor@aui.ma` | professor | CS 400, CS 330 |

## Env

`VITE_API_BASE=http://127.0.0.1:8000`
