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

Legacy separate kiosk/dashboard folders remain as optional web shells only
(not a physical kiosk / barcode / NFC path). **The unified app is what you send
for product testing**.

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
3. Sign in as student → **Quiet ask** or **Identify me** → pick message / face-to-face / online;
   optionally post in **Stuck Room** and mark a classmate reply “this unlocked it”
4. Sign in as Alice (`a.chen@aui.ma`) → TA queue filters **Assigned to me** /
   **I'm backup** / **All** → switch course picker to a **student** course
5. Sign in as professor (`a.benali@aui.ma`) → **TA load** panel + command center:
   - dual-TA primary/backup counts
   - repeated topic clusters (group review vs FAQ)
   - **Review insights** (chapter / ask-category board for the next review session)
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

**Community recommendation:** Canvas LTI 1.3 as primary. Not AUI portal scraping.
Manual admin entry only as a rare support escape hatch.

> **Demo honesty:** today’s `POST /canvas/launch` and `/canvas-demo` are an
> **unsigned** JIT simulator (optional lock via `OFFICEHOURS_CANVAS_LAUNCH_SECRET`).
> Do not claim signed LTI in a defense. See [`fyp_evidence.md`](fyp_evidence.md).

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

## Stuck Room (classmate help threads)

A **Reddit-style live chat is the wrong shape** for a course: integrity risk,
moderation load, and it overlaps Quiet ask + classmate notes. Stuck Room is
instead a **course-scoped thread**:

1. Student posts what they are stuck on (optional chapter label, optional
   “Classmate” anonymity)
2. Classmates reply with a simpler approach or missing perspective — not the
   homework write-up
3. Unique **“this unlocked it”** marks (no self-votes) become **helpful points**
   and a course rank
4. Grades, integrity, and crises are blocked → use **Quiet ask**

Staff (TA/professor) **do not read the social room**. Professors get aggregated
**review insights** instead.

API: `GET|POST /help-room/`, replies + helpful marks, `GET /help-room/ranks/`.

## Review insights (professor chapter board)

`GET /analytics/review-insights?course_id=` (professor auth) groups:

- Quiet ask / office-hours questions by Analyzer category (sensitive excluded)
- Stuck Room posts by student-labeled chapter

Each topic shows counts, sample question titles, and a **review hint** (emphasize
in the next session, tighten the explanation for the next cohort / related
chapter). This reuses the existing question corpus — it is not a second empty
database.

## TA staffing loop

TAs own a real office-hours loop — not only curation drafts:

1. **Claim** an ask  
2. **Start helping** (`in_progress`)  
3. **Help Coach** — similar open asks, approved KB neighbors, Socratic steps,
   draft / rewrite student reply, refresh teaching script (`POST /ta/assist/`)  
4. **Reply to student** (message mode — visible on request status immediately)  
5. **Done helping** or **Take as primary** (backup handoff)  
6. **Send teaching draft** to professor curation  

Triage context (difficulty, learning style, tags, sensitive, matcher) plus the
Help Coach panel show on the selected ask. Queue items include a **similar**
badge when classmates are stuck on the same cluster/category. Queue + load +
assist APIs require auth and TA/professor membership for the course.

## Shared group meetings (repeated concepts)

When many asks share a cluster / topic:

1. Professor (**Repeated Topics**) or TA (**Help Coach → Propose one group meeting**)
   sets one **title + when + where/link**
2. `POST /actions/recommendations/` stores a `group_session` decision with
   `meeting_*` fields attached to all `request_ids` in the cluster
3. Each student looks up their request code — status shows the **same** shared
   meeting time/place (`meeting_title`, `meeting_when`, `meeting_place`)

This is the intended face-to-face path for repeats: teach once as a group, not
copy a chat reply to every student.

## Packaging note

Today the deliverable is a **single web application package** (one frontend +
API) with authentication. Production entry should be **Canvas LTI** (plus optional
campus SSO later). The important product rule is already true: **one login,
role + course context, not three naked URLs**.

## Agent performance backlog

See [`docs/agent_performance.md`](agent_performance.md) and
[`docs/fyp_evidence.md`](fyp_evidence.md) for metrics, ceilings, and defense claims:

- Offline CV / silver holdout reports
- **Human gold labels** (`data/gold_labels/` + `evaluate_gold_labels.py`)
- **Per-course KB hit-rate** (`GET /analytics/kb-hit-rate`)
- Multi-department training (MTH / COM / ECO / ENG / GEN — not CSC-only)
- Ask Triage latency smoke (`measure_ask_triage_latency.py`)

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
