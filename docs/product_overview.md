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
| `p.nair@aui.ma` | **TA + student** | TA: CSC 3323, 3326 · Student: MTH 1304 |
| `s.ortiz@aui.ma` | **TA + student** | TA: CSC 3374, 3324 · Student: COM 1301 |
| `a.benali@aui.ma` | professor | CSC 2302, 3323, 3374 |

Dual-TA sections (primary + backup Matcher): CSC 2302 (Alice/Bob), CSC 3323
(Bob/Priya), CSC 3374 (Bob/Sam).

## What a supervisor does

1. Run `./scripts/run_product.sh` (or start backend + `officehours-app`)
2. Open **http://127.0.0.1:5180**
3. Sign in as student → **Quiet ask** or **Identify me** → pick message / face-to-face / online
4. Sign in as Alice (`a.chen@aui.ma`) → TA queue filters **Assigned to me** /
   **I'm backup** / **All** → switch course picker to a **student** course
5. Sign in as professor (`a.benali@aui.ma`) → **TA load** panel + command center:
   - dual-TA primary/backup counts
   - repeated topic clusters (group review vs FAQ)
   - urgent/sensitive flags
   - **Sync Canvas materials into KB** (or paste slides)
   - approve pending FAQ/KB drafts
6. After two similar conceptual asks, student sees solidarity (“you're not alone”)
   and can **opt in to study-buddy** (never for stress/sensitive)

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

## Classmate notes (peer study feed)

Under **Study Agent**, students get a course-scoped **Classmate notes** feed:

1. Enter a **title** and **what the notes are about** (required before upload)
2. Optional caption + quiet post (hide name as “Classmate”)
3. Upload PDF / DOCX / TXT / MD / images
4. Classmates can **like**, **comment**, and **download** for their own use

This is peer sharing — it does **not** train the study agent. Professor-approved
KB stays separate.

API: `GET|POST /peer-notes/`, like/comment/download under `/peer-notes/{id}/…`
(auth + course membership required).

## TA staffing loop

TAs own a real office-hours loop — not only curation drafts:

1. **Claim** an ask  
2. **Start helping** (`in_progress`)  
3. **Reply to student** (message mode — visible on request status immediately)  
4. **Done helping** or **Take as primary** (backup handoff)  
5. **Send teaching draft** to professor curation  

Ask Triage teaching context (difficulty, learning style, tags, sensitive, matcher)
is shown on the selected ask. Queue + load APIs require auth and TA/professor
membership for the course.

## Packaging note

Today the deliverable is a **single web application package** (one frontend +
API) with authentication. Production entry should be **Canvas LTI** (plus optional
campus SSO later). The important product rule is already true: **one login,
role + course context, not three naked URLs**.

## Agent performance backlog

See [`docs/agent_performance.md`](agent_performance.md) for metrics and upgrades:

- Offline CV / silver holdout reports
- **Human gold labels** (`data/gold_labels/` + `evaluate_gold_labels.py`)
- **Per-course KB hit-rate** (`GET /analytics/kb-hit-rate`)
- Multi-department training (MTH / COM / ECO / ENG / GEN — not CSC-only)

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
