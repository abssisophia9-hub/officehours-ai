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

## Analyzer data — 120 labeled requests

Union of:

| File | Rows | Provenance |
| --- | --- | --- |
| `data/labeled_requests.csv` | 40 | `synthetic_finals_week` |
| `data/labeled_requests_extended.csv` | 40 | `synthetic_finals_week_v2` |
| `data/labeled_requests_extra.csv` | 40 | `synthetic_finals_week_v3` |

**Columns:** `request_id`, `text`, `category`, `urgency`, `label_source`

**Categories covered:** `conceptual_question`, `exam_logistics`, `project_submission`,
`retake_request`, `grading_dispute`, `emotional_stress`, `accessibility_accommodation`,
`office_hours_access`, `academic_integrity`, `uncategorized`

These are handwritten finals-week style questions designed to stress office-hours
triage (concepts, logistics, stress, integrity, etc.).

## Matcher data — 120 silver TA labels

| File | Rows | Provenance |
| --- | --- | --- |
| `data/matcher_training.csv` | 120 | `silver_label_from_expertise_overlap` |

**Columns:** `text`, `category`, `assigned_ta`, `alternative_ta`, `source`

Silver labels were produced by aligning question text / category with TA expertise
tags from `data/ta_roster_seed.csv`:

| TA | Example expertise tags |
| --- | --- |
| Alice Chen | trees, red-black, deletion, rotations, conceptual |
| Bob Martinez | recursion, DP, memoization, algorithms |
| Priya Nair | hashing, arrays, search, exam logistics, projects |
| Sam Ortiz | debugging, grading, stress, accommodations, integrity, access |

Holdout from `train_matcher.py` (last run): ~96% accuracy / ~0.94 macro-F1 on a
stratified-ish 20% holdout (synthetic silver labels — treat as demo metrics).

## Synthesizer data — 50 teaching-bank rows

| File | Rows | Provenance |
| --- | --- | --- |
| `data/synthesizer_teaching_bank.csv` | 50 | `curated_training_bank` |

**Columns:** `entry_id`, `category`, `learning_style`, `topic`, `student_hint`,
`teaching_approach`, `source`

Balanced across 10 categories × 5 learning styles
(`example_driven`, `step_by_step`, `visual_structural`, `conceptual`, `unknown`).

At runtime the Synthesizer:

1. Prefer **professor-approved KB** hits (true RAG over curated course knowledge)
2. Else retrieve nearest teaching-bank entries by embedding similarity + style/category boost
3. Compose non-spoiler `student_hint` + numbered `teaching_approach`
4. Uses the style ranker when the student style is unknown

## Learning-style data — 40 labels

| File | Rows |
| --- | --- |
| `data/labeled_learning_styles.csv` | 40 (8 per style) |

Used so drafts adapt teaching approach language to how the student asked.

## What was intentionally removed

Prompted Claude calls and `USE_MOCK_CLAUDE` deterministic mocks are **not** on the
assessed FYP runtime path. External LLM remains gated behind
`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` (default).
