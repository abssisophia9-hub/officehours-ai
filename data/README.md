# Data fixtures

This folder contains lightweight CSV fixtures for prototyping the OfficeHours AI
classification, clustering, and recommendation pipeline.

## `synthetic_requests.csv`

Raw finals-week student requests.

Columns:

- `request_id` — stable synthetic ID, e.g. `FS001`
- `text` — student request text
- `timestamp` — ISO-like local timestamp for demo ordering
- `submission_type` — `anonymous` or `identified`

## `labeled_requests.csv`

Supervised labels for the same request IDs in `synthetic_requests.csv`.

Columns:

- `request_id`
- `text`
- `category` — initial classification target, such as
  `conceptual_question`, `exam_logistics`, `retake_request`,
  `emotional_stress`, `grading_dispute`, or `project_submission`
- `urgency` — `low`, `medium`, `high`, or `urgent`
- `label_source` — all current rows are `synthetic_finals_week`

## `demo_scenarios.csv`

Scenario-level expectations for demos and future tests.

Columns:

- `scenario_id`
- `description`
- `expected_cluster`
- `expected_action`

These rows are intentionally synthetic and should not be treated as real student
data. They are meant to exercise finals-week patterns before the project has
production data.
