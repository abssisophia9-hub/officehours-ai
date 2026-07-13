# Product overview — what supervisors test

## The product

**OfficeHours AI is one packaged multi-role campus application**, not three
separate URL demos.

Users **log in** as themselves. Memberships decide whether they act as a
**student**, **TA**, or **professor** **per course**. A professor can teach
multiple courses; a course can have one or more TAs; a student can enroll in
several courses and switch between them.

Primary app:

- `frontend/officehours-app` (dev port **5180**)
- Launch helper: `./scripts/run_product.sh`

Legacy separate kiosk/dashboard folders remain for hardware/kiosk experiments,
but **the unified app is what you send for product testing**.

## Demo accounts

Password for all: `aui-demo`

| Email | Role | Courses |
| --- | --- | --- |
| `student@aui.ma` | student | CS 400, CS 330 |
| `student2@aui.ma` | student | CS 330 |
| `ta.alice@aui.ma` | TA | CS 400 |
| `ta.bob@aui.ma` | TA | CS 400, CS 330 |
| `professor@aui.ma` | professor | CS 400, CS 330 |

## What a supervisor does

1. Run `./scripts/run_product.sh` (or start backend + `officehours-app`)
2. Open **http://127.0.0.1:5180**
3. Sign in as student → submit a CS 400 question
4. Sign in as TA Alice → resolve it
5. Sign in as professor → approve the knowledge draft
6. Switch courses with the course picker to see multi-course behavior

## Packaging note

Today the deliverable is a **single web application package** (one frontend +
API) with authentication. It can later be wrapped as a desktop installer
(Electron) or deployed behind AUI SSO. The important product rule is already
true: **one login, role + course context, not three naked URLs**.
