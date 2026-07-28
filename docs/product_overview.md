# Product overview — what supervisors test

## The product

**OfficeHours AI is one packaged multi-role campus application**, not three
separate URL demos.

Users **log in** as themselves. Memberships decide whether they act as a
**student**, **TA**, or **professor** **per course**. A professor can teach
multiple courses; a course can have one or more TAs; a student can enroll in
several courses and switch between them.

**A TA is also a student on campus.** The same account can be TA in one course
and student in others — the course picker switches the workspace with the role.

Primary app:

- `frontend/officehours-app` (dev port **5180**)
- Launch helper: `./scripts/run_product.sh`

Legacy separate kiosk/dashboard folders remain for hardware/kiosk experiments,
but **the unified app is what you send for product testing**.

Full history: [`project_journey.md`](project_journey.md).

## Demo accounts

Password for all: `aui-demo`

AUI emails look like `S.Abssi@aui.ma` (first initial + `.` + last name).
**Role is never encoded in the email** — it comes from the membership for each
course.

AUI is an English-language, American-style liberal-arts university (Ifrane).
SSE course codes look like **CSC 3374**; a typical undergrad load is **~6–7
courses** per term.

| Email | Roles (by course) | Courses |
| --- | --- | --- |
| `s.elidrissi@aui.ma` | student | CSC 2302, 3323, 3374, 3326, 3324 + MTH 1304 + COM 1301 (7) |
| `y.amrani@aui.ma` | student | CSC 3323, 3374 + MTH 1304 |
| `a.chen@aui.ma` | **TA + student** | TA: CSC 2302 · Student: CSC 3323, MTH 1304, COM 1301 |
| `b.martinez@aui.ma` | **TA + student** | TA: CSC 2302, 3323, 3374 · Student: MTH 1304, COM 1301 |
| `a.benali@aui.ma` | professor | CSC 2302, 3323, 3374 |

## What a supervisor does

1. Run `./scripts/run_product.sh` (or start backend + `officehours-app`)
2. Open **http://127.0.0.1:5180**
3. Sign in as student → **Quiet ask** or **Identify me** → pick message / face-to-face / online
4. Sign in as Alice (`a.chen@aui.ma`) → TA queue on CSC 2302 → switch course picker to a **student** course
5. Sign in as professor (`a.benali@aui.ma`) → **Office-hours command center**:
   - repeated topic clusters (group review vs FAQ)
   - urgent/sensitive flags
   - **Sync Canvas materials into KB** (or paste slides)
   - approve pending FAQ/KB drafts
6. Optional: open **`/canvas-demo`** and launch as Karim (TA in OS, student in Data Structures)

## How courses appear on login

Courses are **not typed in by hand each session**. For demos, a seed script
attaches enrollments to each account. For community deploy, **Canvas** is the
source:

| Source | When | What happens |
| --- | --- | --- |
| **Demo seed** (local) | App startup / login | `ensure_demo_accounts()` creates AUI-style users + courses + memberships |
| **Canvas launch** (intended SaaS path) | Click **Open OfficeHours AI** inside a Canvas course | Auto-provision course + membership from Canvas role, mint session |
| **Live Canvas materials** | Professor syncs | `CANVAS_BASE_URL` + `CANVAS_ACCESS_TOKEN` (else local AUI Canvas mirror) |

**Community recommendation:** Canvas LTI as primary. Not AUI portal scraping.
Manual admin entry only as a rare support escape hatch.

## Asking for help (identity + meeting preference)

Students choose:

1. **Quiet ask (anonymous)** — no name/ID stored; staff see a request code only  
2. **Identify me** — uses the logged-in display name + student ID so staff can
   follow up directly  

And separately:

- **Message / async** — answer in the queue / FAQ  
- **Face-to-face meeting** — request an in-person office-hours slot  
- **Online meeting** — request Zoom/Teams  

TA and professor queues show who asked (or Anonymous) and the help mode so staff
know whether to reply in writing or schedule a meeting.

## Packaging note

Today the deliverable is a **single web application package** (one frontend +
API) with authentication. Production entry should be **Canvas LTI** (plus optional
campus SSO later). The important product rule is already true: **one login,
role + course context, not three naked URLs**.

## Agent performance backlog

See [`docs/agent_performance.md`](agent_performance.md) for what limits Analyzer /
Matcher / Synthesizer / KB quality today and the ranked upgrade plan.

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
