# Training data for custom Oracle agents

All current training fixtures are **synthetic / silver / curated** for the FYP.
They are **not** scraped private student emails or real AUI transcripts.

## Models on disk (`backend/models/`)

| Artifact | Agent | Algorithm |
| --- | --- | --- |
| `request_classifier.joblib` | Analyzer | `all-MiniLM-L6-v2` embeddings + logistic regression |
| `matcher_classifier.joblib` | Matcher | embeddings + logistic regression over TA names |
| `synthesizer_ranker.joblib` | Synthesizer | embeddings + logistic regression over learning styles + RAG bank |
| `learning_style_classifier.joblib` | Style cue | embeddings + logistic regression |

Train scripts (from `backend/`):

```bash
python3 scripts/train_classifier.py
python3 scripts/train_matcher.py
python3 scripts/train_synthesizer.py
python3 scripts/train_learning_style.py
```

## Analyzer data — labeled requests

Union of:

| File | Rows | Provenance |
| --- | --- | --- |
| `data/labeled_requests.csv` | 40 | `synthetic_finals_week` |
| `data/labeled_requests_extended.csv` | 40 | `synthetic_finals_week_v2` |
| `data/labeled_requests_extra.csv` | 40 | `synthetic_finals_week_v3` |
| `data/labeled_requests_csc.csv` | 15 | `synthetic_csc_topics` (AUI CSC demos) |
| `data/analyzer_training_export.csv` | optional | professor-approved KB export |

**Columns:** `request_id`, `text`, `category`, `urgency`, `label_source`

**Categories covered:** `conceptual_question`, `exam_logistics`, `project_submission`,
`retake_request`, `grading_dispute`, `emotional_stress`, `accessibility_accommodation`,
`office_hours_access`, `academic_integrity`, `uncategorized`

CSC supplement covers hashing, red-black trees, mergesort, scheduling, distributed RPC,
and related triage for demo courses (`CSC 2302`, `3323`, `3351`, `3374`, …).

## Matcher data — silver TA labels

| File | Rows | Provenance |
| --- | --- | --- |
| `data/matcher_training.csv` | 120 | `silver_label_from_expertise_overlap` |
| `data/matcher_training_csc.csv` | 15 | `silver_csc_topics` |

**Columns:** `text`, `category`, `assigned_ta`, `alternative_ta`, `source`

Silver labels align question text / category with TA expertise tags from
`data/ta_roster_seed.csv` (kept in sync with `DEFAULT_TA_ROSTER`):

| TA | Example expertise tags |
| --- | --- |
| Alice Chen | trees, red-black, deletion, rotations, conceptual |
| Bob Martinez | recursion, DP, memoization, algorithms |
| Priya Nair | hashing, arrays, search, exam logistics, projects |
| Sam Ortiz | debugging, grading, stress, accommodations, integrity, access |

`train_matcher.py` writes holdout metrics to `reports/final_report/matcher_evaluation.json`.
Treat silver holdout as **demo metrics**, not gold TA judgment.

## Synthesizer data — teaching banks

| File | Rows | Provenance |
| --- | --- | --- |
| `data/synthesizer_teaching_bank.csv` | 50 | `curated_training_bank` (category × style) |
| `data/synthesizer_teaching_bank_csc.csv` | 8 | `curated_csc_bank` (topic-specific) |

**Columns:** `entry_id`, `category`, `learning_style`, `topic`, `student_hint`,
`teaching_approach`, `source`

Runtime loads both banks. Prefer professor-approved KB RAG first; weak matches
steer students to Quiet ask instead of hallucinating.

## Learning-style data — 40 labels

| File | Rows |
| --- | --- |
| `data/labeled_learning_styles.csv` | 40 (8 per style) |

Default backend is **`ml`** (`OFFICEHOURS_LEARNING_STYLE_BACKEND`).

## Performance backlog

See [`docs/agent_performance.md`](agent_performance.md) for ranked upgrades and
honest ceilings.

## What was intentionally removed

Prompted Claude calls and `USE_MOCK_CLAUDE` deterministic mocks are **not** on the
assessed FYP runtime path. External LLM remains gated behind
`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` (default).
