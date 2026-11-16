# Glossary — product language

Short names used in demos, UI, and docs. Implementation identifiers now match
the product names (the historical `oracle_*` prefix was renamed to `triage_*`).

## Roles (per course)

| Role | Who | Workspace |
| --- | --- | --- |
| **Student** | Enrolled learner | Ask · Study Agent · **Rooms** · classmate notes · status lookup |
| **TA** | Course teaching assistant | Queue · Help Coach · staffing · optional group meeting |
| **Professor** | Course instructor | Clusters · **review insights** · KB gate · Canvas sync · group meetings · metrics |

The same login can staff one course and be a student in a **different** course.
A TA is not a classmate in the section they staff.

## AI surfaces

| Name | Audience | When | What |
| --- | --- | --- | --- |
| **Ask Triage** | Everyone (runs at submit) | `POST /requests/` | Analyzer → Matcher → Synthesizer. Internal module: `ask_triage_service.py`; columns/API use `triage_*` (renamed from historical `oracle_*`). |
| **Help Coach** | TA (while helping) | `POST /ta/assist/` | Similar opens, KB neighbors, Socratic steps, draft/rewrite reply, refresh teaching script. |
| **Study Agent** | Student | `POST /agent/ask` | Answers only from **professor-approved** KB / materials. |
| **Pedagogy Agent** | Student | `POST /revision/plan` (route `/student/revision`) | 7-day focus plan from on-device practice scores + preference; web/KB resources. Internal IDs stay `revision_*`. |
| **Lifetime confusion** | Professor analytics | `/analytics/lifetime-confusion` | Hotspots from approved KB topics. |

## Help modes

| Mode | Student expectation | How staff respond |
| --- | --- | --- |
| **message** | Written answer | TA **Reply** → visible on request status |
| **face_to_face** | In-person help | Claim / help in person; for repeats use a **shared group meeting** |
| **online_meeting** | Remote call | Staff share link/time (or group meeting place = link) |

## Repeated concepts

| Mechanism | Owner | Outcome |
| --- | --- | --- |
| **Cluster** | System (`cluster_id`) | Groups similar asks |
| **Similar badge / Help Coach** | TA | Cue to help as a group |
| **Shared group meeting** | TA or professor | One title + when + place on **all** linked request statuses |
| **Material approve** | Professor | Approved **course material** feeds Study Agent (Orchestration Layer). FAQ/staff drafts may still exist in the API for TA coaching — not shown as Suggested answers in the product UI. |
| **Rooms** (API still `/help-room/`) | Students (course-scoped) | Stack Overflow hybrid: named Problem/Discussion/Article rooms, Canvas-module chapters, Express Interest, classmate leaderboard. Staff do not sit in the room. Quiet ask is the anonymous path to staff. Demo syllabus only if `OFFICEHOURS_DEMO=true`. |
| **Rooms board / classmate points (ŵ)** | Students (per course) | Quality-over-volume reputation on the Rooms board. ŵ is the playful point unit. |
| **Express Interest** | Students | Offer to help on a room without it being a private chat. |
| **Review insights** | Professor | End-of-chapter question board from Quiet asks + Rooms chapters — emphasize / cover / draft FAQ / next-cohort note. |

## Status (student)

`GET /requests/{id}/status` (request code) can show:

- queue / TA helping / TA reply
- or **shared group meeting** (`meeting_title`, `meeting_when`, `meeting_place`)

No login required for the privacy-safe status view (kiosk); the product app also
has a status lookup panel.
