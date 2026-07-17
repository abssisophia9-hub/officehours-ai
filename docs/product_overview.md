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

AUI emails look like `S.Abssi@aui.ma` (first initial + `.` + last name).
**Role is never encoded in the email** — it comes from `course_memberships`.

| Email | Role (via membership) | Courses |
| --- | --- | --- |
| `s.elidrissi@aui.ma` | student | CS 400, CS 330 |
| `y.amrani@aui.ma` | student | CS 330 |
| `a.chen@aui.ma` | TA | CS 400 |
| `b.martinez@aui.ma` | TA | CS 400, CS 330 |
| `a.benali@aui.ma` | professor | CS 400, CS 330 |

## What a supervisor does

1. Run `./scripts/run_product.sh` (or start backend + `officehours-app`)
2. Open **http://127.0.0.1:5180**
3. Sign in as student → use **Quiet ask (anonymous)** by default, or identify yourself
4. Sign in as TA (`a.chen@aui.ma`) → resolve a queue item
5. Sign in as professor (`a.benali@aui.ma`) → use the **Office-hours command center**:
   - repeated topic clusters (group review vs FAQ)
   - urgent/sensitive flags
   - **Sync Canvas materials into KB** (or paste slides)
   - approve pending FAQ/KB drafts
6. Switch courses with the course picker to see multi-course behavior

## Packaging note

Today the deliverable is a **single web application package** (one frontend +
API) with authentication. It can later be wrapped as a desktop installer
(Electron) or deployed behind AUI SSO. The important product rule is already
true: **one login, role + course context, not three naked URLs**.

## Canvas / course materials

Each course has a `canvas_course_id`. Professors sync LMS content with
`POST /knowledge/canvas/sync` (auth required, professor role):

- **Live Canvas:** set `CANVAS_BASE_URL` + `CANVAS_ACCESS_TOKEN` — pulls pages
  and text files from Canvas REST API into the course KB.
- **Local mirror (default for demos):** seeded Canvas-style files per course
  (same ingest path) so supervisors can test without AUI Canvas credentials.

Manual paste still works via `POST /knowledge/materials` (professor auth,
required `course_id`). Chunks are course-scoped and searchable by
`POST /agent/ask` with the same `course_id`.
