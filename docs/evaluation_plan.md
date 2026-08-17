# Evaluation Plan

This file is the **historical** pilot evaluation plan. It is kept so the original
study design remains readable. **New campus surveys are not required for
graduation.** See [surveys/README.md](surveys/README.md) and
[fyp_evidence.md](fyp_evidence.md).

| Item | Detail |
| --- | --- |
| **When surveys were used** | Optional. Historical paper forms exist under `docs/surveys/`. |
| **Historical Likert** | 5-point (1 = strongly disagree, 5 = strongly agree) |
| **Historical scales** | Perceived Usefulness (PU) and Perceived Ease of Use (PEOU) from TAM |
| **Historical extra items** | Trust, fairness, wait-time perception, AI-helpfulness, privacy comfort |
| **Historical analysis** | Mean, SD, Cronbach’s α, optional paired t-test / Wilcoxon, thematic coding of free text |

## Historical data collection

| Wave | Instrument | Audience |
| --- | --- | --- |
| Pre | [pre_survey.md](surveys/pre_survey.md) | Students + TAs (historical) |
| Post | [post_survey.md](surveys/post_survey.md) | Students + TAs (historical) |
| Professor | [professor_interview.md](surveys/professor_interview.md) | Course instructors (historical) |
| Optional unified demo | [surveys/unified_product_post_demo_survey.md](surveys/unified_product_post_demo_survey.md) | Students, TAs, professors after a `:5180` demo — includes Rooms (named classmate forum + Hilbert leaderboard) |

## Metrics (logs, not surveys)

| Metric | Source | Success idea |
| --- | --- | --- |
| Wait time | `requests.created_at` → `helped_at` | Mean wait ↓ vs baseline / control |
| Queue length | Snapshot of waiting requests | Peak and average queue ↓ |
| Time-to-first-help | Same as wait, plus TA `helping` timestamps | Faster first contact |
| Repeat visitors | Distinct students with >1 request | Engagement, not a vanity metric |
| Resolution rate | `status=helped` / total | High completion |
| AI deflection | Ask Triage resolved / total Ask Triage chats | Honest rate; not a KPI to maximize |
| Clustering quality | Manual audit of `request_groups` | Groups make sense to a TA |
| Fairness | Wait time by student / topic | No systematic delay for a subgroup |

## Historical protocol (do not treat as a remaining gate)

1. IRB / department ethics approval if collecting identifiable survey answers.
2. Baseline week: office hours as usual, log wait if possible.
3. Intervention week: run the system, same course if possible.
4. Pre-survey at the start of the intervention window.
5. Post-survey + professor interview at the end.
6. Export logs (anonymize student identifiers before sharing outside the course).
7. Analyze Likert + logs; write Results + Limitations.

**Capstone evidence** is the running product, tests, logs, and this repository —
not a new survey campaign. See [fyp_evidence.md](fyp_evidence.md).
