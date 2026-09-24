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
| **Revision Strategist** | Student | `POST /strategist/plan` | LLM (when allowed) + YouTube/article tools. Builds a learner dossier from how they ask, what they ask, struggles, and learning style; returns structured links. Does not invent URLs and does not quote the syllabus. |
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
| **FAQ / KB approve** | Professor | Later students get the answer via Study Agent |
| **Rooms** (API still `/help-room/`) | Students (course-scoped) | Stack Overflow hybrid: named Problem/Discussion/Article rooms, Canvas-module chapters, Express Interest, Hilbert-weighted ranks. Staff do not sit in the room. Quiet ask is the anonymous path to staff. Demo syllabus only if `OFFICEHOURS_DEMO=true`. |
| **Hilbert Weight ŵ / Node Points / ROOMS score** | Students (per course) | Quality-over-volume reputation. Score(W) is ŵ; Base is Node Points; podium uses ROOMS score. |
| **Express Interest** | Students | Offer to help on a room without it being a private chat. |
| **Review insights** | Professor | End-of-chapter question board from Quiet asks + Rooms chapters — emphasize / cover / draft FAQ / next-cohort note. |

## Status (student)

`GET /requests/{id}/status` (request code) can show:

- queue / TA helping / TA reply
- or **shared group meeting** (`meeting_title`, `meeting_when`, `meeting_place`)

No login required for the privacy-safe status view (kiosk); the product app also
has a status lookup panel.
