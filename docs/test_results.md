# Software test results — OfficeHours AI

**Date:** 2026-11-12  
**Branch:** `cursor/canvas-settings-token-db64` (PR #133; not merged)  
**Command (run once from `backend/`):**

```bash
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
OFFICEHOURS_ALLOW_EXTERNAL_LLM=false \
OFFICEHOURS_DEMO=true \
./venv/bin/python -m pytest -q --tb=line
```

**Result line:** `277 passed, 18 warnings in 126.77s (0:02:06)` — exit code **0**.

No existing tests were weakened, skipped, or deleted. Retrieval / Study Agent ranking code was **not** changed.

---

## What was tested

Full backend pytest suite under `backend/tests/` — **51** modules, **277** collected cases. Areas covered by module names:

| Area | Modules (representative) |
| --- | --- |
| Auth / roles / SSO / LTI | `test_auth_courses`, `test_lti13`, `test_microsoft_sso`, `test_demo_mode`, `test_defense_hardening`, `test_security_hardening` |
| Request intake | `test_main`, `test_ask_identity_and_meetings`, `test_request_status`, `test_request_status_service` |
| Ask Triage | `test_ask_triage`, `test_analyzer_agent`, `test_classifier`, `test_ml_classifier`, `test_custom_agents`, `test_agent_quality`, `test_learning_style`, `test_no_ta_routing` |
| Canvas (mocked / local mirror) | `test_canvas_kb`, `test_canvas_launch`, `test_room_chapters` |
| Study Agent / KB gate | `test_knowledge`, `test_study_approval`, `test_study_retrieval_modes`, `test_study_conversations`, `test_answer_check`, `test_agent_policy`, `test_study_eval` |
| TA queue / realtime / Help Coach | `test_ta_staffing`, `test_ta_and_realtime`, `test_help_coach`, `test_dual_ta_social`, `test_group_meeting` |
| Rooms / notes / feedback / ops | `test_help_room`, `test_peer_notes`, `test_feedback`, `test_scale_slice`, `test_seed_demo_data`, … |

Full module list: `test_actions`, `test_agent_metrics`, `test_agent_policy`, `test_agent_quality`, `test_analyzer_agent`, `test_analyze_survey_responses`, `test_answer_check`, `test_ask_identity_and_meetings`, `test_ask_triage`, `test_audit_fixes`, `test_auth_courses`, `test_canvas_kb`, `test_canvas_launch`, `test_chaos_command_center`, `test_classifier`, `test_clustering`, `test_custom_agents`, `test_defense_hardening`, `test_demo_mode`, `test_demo_orchestration`, `test_dual_ta_social`, `test_feedback`, `test_group_meeting`, `test_help_coach`, `test_help_room`, `test_ics_calendar`, `test_knowledge`, `test_learning_style`, `test_lti13`, `test_main`, `test_material_uploads`, `test_microsoft_sso`, `test_ml_classifier`, `test_ml_demo_seed`, `test_no_ta_routing`, `test_office_hours`, `test_peer_notes`, `test_request_status`, `test_request_status_service`, `test_room_chapters`, `test_room_reputation`, `test_scale_slice`, `test_security_hardening`, `test_seed_demo_data`, `test_study_approval`, `test_study_conversations`, `test_study_eval`, `test_study_retrieval_modes`, `test_ta_and_realtime`, `test_ta_staffing`, `test_upload_status`.

---

## Pass / fail (actual)

| Metric | Count |
| --- | --- |
| Collected | 277 |
| Passed | **277** |
| Failed | **0** |
| Skipped | **0** |
| Errors | **0** |
| Warnings | 18 (Starlette `BlockingPortal` deprecation; SciPy/sklearn `disp`/`iprint` deprecations) |

---

## Coverage summary

**[VERIFY]** — `pytest-cov` / `coverage` are **not** in `backend/requirements.txt` and were not installed for this run. No line/% coverage report was produced. Do not invent a coverage percentage.

---

## Task a Study Agent (live Canvas smoke — not pytest)

Source: `/cursor/stores/self/docs/task-a-canvas-study-evidence.md`  
Course: FA26-CSC430701 Agile Software Engineering and DevO (Canvas id `16517`); 10/16 files synced → 120 chunks stamped approved.

### How Task a sync actually ran

- **Live Canvas API**, not local fixtures: smoke used settings `CANVAS_BASE_URL` + `CANVAS_API_TOKEN` (from `backend/.env` via pydantic-settings). `list_canvas_files_by_id` pulled real modules/files for Canvas course `16517`, then `ingest_course_material` wrote KB rows.
- **Approval was smoke bulk stamp**, not the professor UI: pending rows were approved with repeated `update_entry(..., KnowledgeEntryUpdate(status="approved"))` in the smoke script — **not** `PATCH` from the professor Material UI and **not** `POST /knowledge/uploads/{upload_id}/approve`.
- **`canvas_mode=local` on running uvicorn was a stale process** started without loading `.env`; the smoke script itself reported `canvas_mode=live`. **[VERIFY after restart]** that `:8000` `/auth/config` shows live once the API is restarted with Canvas env loaded.

| # | Result |
| --- | --- |
| Q1 Unit 1 / agile SE | **correct** |
| Q2 Lecture 4 requirements & architecture | **correct** |
| Q3 Lecture 1 part I | **incorrect** |
| Score | **2 / 3** |

### Known limitation — Q3 ranking miss

- **Symptom:** Asked for Agile lecture **1** part I; Study Agent cited Agile lecture **2** (Part I/II) among synced titles.
- **Cause:** Retrieval **ranking miss** among synced titles — not a failed sync and not missing materials.
- **Action taken for Task b:** Recorded only. **No retrieval code changes** to force a pass.

---

## Other known limitations

| Item | Status |
| --- | --- |
| Frontend (`frontend/officehours-app`) automated tests | **None** — known limitation; not run |
| Line coverage % | **[VERIFY]** (tooling absent) |
| Live Canvas HTTP tests inside pytest | Not part of this suite (local/mirror + mocks only); live sync evidence is Task a |
| Full product UI / browser E2E | **[VERIFY]** — not run in Task b |
| CI matrix beyond this local full suite | **[VERIFY]** relative to this machine run (PR #133 CI was green earlier for settings commit) |

---

## Secrets

`CANVAS_API_TOKEN` was not printed, logged, or committed for this task.
