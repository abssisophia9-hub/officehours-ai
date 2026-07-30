# Glossary — product language

Short names used in demos, UI, and docs. Implementation identifiers that still
say `oracle_*` are noted where they differ.

## Roles (per course)

| Role | Who | Workspace |
| --- | --- | --- |
| **Student** | Enrolled learner | Ask · Study Agent · classmate notes · status lookup |
| **TA** | Course teaching assistant | Queue · Help Coach · staffing · optional group meeting |
| **Professor** | Course instructor | Clusters · KB gate · Canvas sync · group meetings · metrics |

The same login can be TA in one course and student in another.

## AI surfaces

| Name | Audience | When | What |
| --- | --- | --- | --- |
| **Ask Triage** | Everyone (runs at submit) | `POST /requests/` | Analyzer → Matcher → Synthesizer. Internal module: `oracle_service.py`; columns/API often `oracle_*`. |
| **Help Coach** | TA (while helping) | `POST /ta/assist/` | Similar opens, KB neighbors, Socratic steps, draft/rewrite reply, refresh teaching script. |
| **Study Agent** | Student | `POST /agent/ask` | Answers only from **professor-approved** KB / materials. |
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

## Status (student)

`GET /requests/{id}/status` (request code) can show:

- queue / TA helping / TA reply
- or **shared group meeting** (`meeting_title`, `meeting_when`, `meeting_place`)

No login required for the privacy-safe status view (kiosk); the product app also
has a status lookup panel.
