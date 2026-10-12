# Prompt log

## Purpose

This is a lab notebook for prompts that produced pull requests. Each entry should let a reader see what was asked, what the tool returned, and what a person kept or rejected. This first version only records facts that are still in the git history and on GitHub. It does not stand in for the missing prompts.

## Tools used

The filled fields below come from:

- `gh pr view` for pull request number, title, head branch, opened and merged times, file list with additions and deletions, and the check rollup (`Backend tests`, `Product app build and audit`)
- `git diff` between each merge commit's parents, limited to `backend/tests`, for `def test_` lines added or removed

Commit messages were not copied into the prompt fields.

## How entries are written

One entry per pull request, in number order: #99, #100, then #101 through #107. A field is filled only when the command above shows it. **Exact prompt**, **Model**, **Written by**, and **What I changed or rejected and why** stay `TODO`. Do not reconstruct a prompt from a commit message, a pull request body, or memory. The other narrative fields stay `TODO` until the person who wrote the prompt fills them.

Line counts are the GitHub file counts for that pull request (`+added/−deleted`). Dates are UTC.

## Entry template

- **Date:**
- **Tool and mode:**
- **Model:**
- **Goal:**
- **Exact prompt:**
- **Written by:**
- **Context given:**
- **Output:**
- **How I checked it:**
- **What I changed or rejected and why:**
- **Mistakes or surprises:**
- **Next prompt:**

Factual fields used in the entries below, when the history has them: pull request number, branch, files changed, tests added, CI result, and dates.

## Entries

### PR #99 — Document Cloud Agent environment install and boot ports

- **Date:** Opened 2026-10-08T20:24:48Z. Merged 2026-10-09T16:14:21Z. Merge commit `c82f4d2b9b28f8d0c1364774b2182b6f8ce9682b`.
- **Pull request:** [#99](https://github.com/abssisophia9-hub/officehours-ai/pull/99)
- **Branch:** `cursor/cloud-agent-env-notes-e6f9`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `AGENTS.md` (modified, +11/−2)
- **Tests added:** None. No file under `backend/tests/` changed.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-09T16:07:59Z. Product app build and audit completed 2026-10-09T16:03:23Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #100 — Clear the source-map-js high audit finding

- **Date:** Opened 2026-10-09T15:52:42Z. Merged 2026-10-09T16:02:02Z. Merge commit `8f208bd91377e497a8124ca19e670e71339a5388`.
- **Pull request:** [#100](https://github.com/abssisophia9-hub/officehours-ai/pull/100)
- **Branch:** `cursor/fix-source-map-js-audit-a8bd`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `frontend/officehours-app/package-lock.json` (modified, +3/−3)
- **Tests added:** None. No file under `backend/tests/` changed.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-09T15:57:39Z. Product app build and audit completed 2026-10-09T15:53:02Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #101 — Course-scoped study agent vertical slice

- **Date:** Opened 2026-10-09T17:33:53Z. Merged 2026-10-10T03:11:53Z. Merge commit `f9a3855eb5394b4c8f620e48010bb04d378fe219`.
- **Pull request:** [#101](https://github.com/abssisophia9-hub/officehours-ai/pull/101)
- **Branch:** `cursor/vertical-slice-study-agent`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `backend/app/database/migrate.py` (modified, +17/−0)
  - `backend/app/models/knowledge.py` (modified, +18/−0)
  - `backend/app/routes/knowledge.py` (modified, +72/−3)
  - `backend/app/services/kb_agent_service.py` (modified, +23/−3)
  - `backend/app/services/knowledge_service.py` (modified, +70/−7)
  - `backend/app/services/material_extract.py` (modified, +31/−14)
  - `backend/demo_data/demo_kettle_notes.pdf` (added; GitHub line counts +0/−0)
  - `backend/tests/test_canvas_launch.py` (modified, +8/−5)
  - `backend/tests/test_defense_hardening.py` (modified, +9/−1)
  - `backend/tests/test_knowledge.py` (modified, +15/−19)
  - `backend/tests/test_material_uploads.py` (modified, +83/−0)
  - `backend/tests/test_study_approval.py` (added, +147/−0)
  - `backend/tests/test_study_retrieval_modes.py` (added, +172/−0)
  - `scripts/run_study_slice.py` (added, +197/−0)
- **Tests added:**
  - `backend/tests/test_study_approval.py`: `test_one_call_approves_every_chunk_of_an_upload`, `test_student_and_ta_cannot_approve_an_upload`, `test_auto_approve_rejected_when_demo_mode_is_off`
  - `backend/tests/test_study_retrieval_modes.py`: `test_plain_mode_sees_pending_row_filtered_mode_does_not`, `test_plain_mode_sees_other_course_row_filtered_mode_does_not`, `test_study_agent_skips_faq_drafts_even_in_plain_mode`, `test_agent_route_does_not_accept_retrieval_flags`
  - `backend/tests/test_material_uploads.py`: `test_pdf_citation_uses_filename_page_and_chunk`
  - `backend/tests/test_canvas_launch.py`, `backend/tests/test_defense_hardening.py`, and `backend/tests/test_knowledge.py` changed and added no new `def test_` function.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-09T17:45:39Z. Product app build and audit completed 2026-10-09T17:41:04Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #102 — Study-agent eval harness: filtered vs plain RAG

- **Date:** Opened 2026-10-10T03:24:00Z. Merged 2026-10-10T18:01:14Z. Merge commit `554f9acf366cab31d84395dc91d253eddcefc758`.
- **Pull request:** [#102](https://github.com/abssisophia9-hub/officehours-ai/pull/102)
- **Branch:** `cursor/eval-harness`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `backend/app/eval/__init__.py` (added, +1/−0)
  - `backend/app/eval/study_harness.py` (added, +423/−0)
  - `backend/demo_data/eval/csc2302_draft_exam_notice.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc2302_exam_prep.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc2302_lecture_notes.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc2302_pending_lab_extension.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc2302_policy_sheet.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc3323_lecture_notes.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/csc3323_policy_sheet.pdf` (added; GitHub line counts +0/−0)
  - `backend/demo_data/eval/manifest.json` (added, +18/−0)
  - `backend/tests/test_study_eval.py` (added, +136/−0)
  - `docs/eval_questions/study_agent_questions.json` (added, +84/−0)
  - `docs/eval_results/SOURCES.md` (added, +50/−0)
  - `docs/eval_results/study_eval_20261010T032204Z.json` (added, +5001/−0)
  - `scripts/build_eval_corpus.py` (added, +186/−0)
  - `scripts/run_study_eval.py` (added, +91/−0)
- **Tests added:**
  - `backend/tests/test_study_eval.py`: `test_question_file_meets_the_schema_and_keeps_authors_apart`, `test_corpus_ingests_approved_and_pending_on_two_courses`, `test_runner_scores_filtered_and_plain_separately`
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-10T03:29:48Z. Product app build and audit completed 2026-10-10T03:24:17Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #103 — Retrieval-only eval ablation and score sweep

- **Date:** Opened 2026-10-10T18:10:20Z. Merged 2026-10-10T18:19:00Z. Merge commit `e55affa52ac8dcf077c338adab281b85f8ac2131`.
- **Pull request:** [#103](https://github.com/abssisophia9-hub/officehours-ai/pull/103)
- **Branch:** `cursor/eval-ablation`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `backend/app/eval/study_harness.py` (modified, +380/−102)
  - `backend/tests/test_study_eval.py` (modified, +126/−9)
  - `docs/eval_questions/HOW_TO_WRITE_QUESTIONS.md` (added, +71/−0)
  - `docs/eval_results/baseline_retrieval_only_20261010T180847Z.json` (added, +28584/−0)
  - `scripts/run_study_eval.py` (modified, +38/−20)
- **Tests added:**
  - `backend/tests/test_study_eval.py`: `test_runner_scores_four_modes_without_merging_authors`, `test_threshold_sweep_uses_recorded_scores_only`
  - The same diff removes `test_runner_scores_filtered_and_plain_separately` from that file.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-10T18:14:23Z. Product app build and audit completed 2026-10-10T18:10:37Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #104 — Add a laptop demo guide for the study agent

- **Date:** Opened 2026-10-10T18:25:35Z. Merged 2026-10-10T18:32:42Z. Merge commit `e5faf583080c751f10bce4c820559b70dea42151`.
- **Pull request:** [#104](https://github.com/abssisophia9-hub/officehours-ai/pull/104)
- **Branch:** `cursor/demo-laptop-guide-a8bd`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `docs/DEMO.md` (added, +177/−0)
- **Tests added:** None. No file under `backend/tests/` changed.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-10T18:29:53Z. Product app build and audit completed 2026-10-10T18:25:54Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #105 — Route asks to the professor when a course has no TA

- **Date:** Opened 2026-10-10T23:42:26Z. Merged 2026-10-11T16:31:12Z. Merge commit `c2bb9cb7c2e9527ea52b5a0f07d155fc6dd81ebc`.
- **Pull request:** [#105](https://github.com/abssisophia9-hub/officehours-ai/pull/105)
- **Branch:** `cursor/no-ta-routing`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `backend/app/database/migrate.py` (modified, +2/−0)
  - `backend/app/models/request.py` (modified, +6/−0)
  - `backend/app/routes/requests.py` (modified, +56/−9)
  - `backend/app/services/ask_triage_service.py` (modified, +28/−10)
  - `backend/app/services/course_ta_service.py` (modified, +95/−0)
  - `backend/app/services/demo_accounts.py` (modified, +9/−0)
  - `backend/app/services/notify_service.py` (modified, +38/−17)
  - `backend/app/services/request_serializer.py` (modified, +1/−0)
  - `backend/app/services/request_status_service.py` (modified, +8/−0)
  - `backend/tests/test_auth_courses.py` (modified, +2/−1)
  - `backend/tests/test_canvas_launch.py` (modified, +10/−8)
  - `backend/tests/test_no_ta_routing.py` (added, +268/−0)
  - `frontend/officehours-app/src/pages/LoginPage.jsx` (modified, +2/−2)
  - `frontend/officehours-app/src/pages/StudentAsksPage.jsx` (modified, +17/−6)
  - `frontend/officehours-app/src/pages/StudentWorkspace.jsx` (modified, +23/−0)
- **Tests added:**
  - `backend/tests/test_no_ta_routing.py`: `test_course_with_ta_still_assigns_a_ta`, `test_no_ta_course_assigns_professor_and_hides_quiet_ask_identity`, `test_several_professors_uses_lowest_user_id`, `test_course_with_neither_returns_error_and_stores_nothing`, `test_student_can_open_labeled_demo_course`
  - `backend/tests/test_auth_courses.py` and `backend/tests/test_canvas_launch.py` changed and added no new `def test_` function.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-10T23:46:35Z. Product app build and audit completed 2026-10-10T23:42:43Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #106 — Make the Study Agent the student home

- **Date:** Opened 2026-10-10T23:52:22Z. Merged 2026-10-11T16:46:27Z. Merge commit `673cc239ed69586071c894e64df8078f9aca0231`.
- **Pull request:** [#106](https://github.com/abssisophia9-hub/officehours-ai/pull/106)
- **Branch:** `cursor/study-agent-first-ui`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `frontend/officehours-app/src/App.jsx` (modified, +3/−1)
  - `frontend/officehours-app/src/components/AccountMenu.jsx` (modified, +6/−6)
  - `frontend/officehours-app/src/pages/StuckRoomPage.jsx` (modified, +2/−2)
  - `frontend/officehours-app/src/pages/StudentAgentPage.jsx` (added, +254/−0)
  - `frontend/officehours-app/src/pages/StudentAsksPage.jsx` (modified, +1/−1)
  - `frontend/officehours-app/src/pages/StudentWorkspace.jsx` (modified, +180/−710)
  - `frontend/officehours-app/src/shell/AppShell.jsx` (modified, +13/−11)
  - `frontend/officehours-app/src/styles.css` (modified, +313/−0)
- **Tests added:** None. No file under `backend/tests/` changed.
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-11T16:42:59Z. Product app build and audit completed 2026-10-11T16:39:12Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO

### PR #107 — Show professors when an upload is waiting for approval

- **Date:** Opened 2026-10-11T02:04:53Z. Merged 2026-10-11T16:29:59Z. Merge commit `a33767f76438e0c60401202ddf52992f15e9b79b`.
- **Pull request:** [#107](https://github.com/abssisophia9-hub/officehours-ai/pull/107)
- **Branch:** `cursor/professor-upload-status`
- **Tool and mode:** TODO
- **Model:** TODO
- **Goal:** TODO
- **Exact prompt:** TODO
- **Written by:** TODO
- **Context given:** TODO
- **Output:** TODO
- **Files changed:**
  - `backend/app/models/knowledge.py` (modified, +20/−0)
  - `backend/app/routes/knowledge.py` (modified, +57/−0)
  - `backend/app/services/knowledge_service.py` (modified, +61/−3)
  - `backend/tests/test_upload_status.py` (added, +157/−0)
  - `frontend/officehours-app/src/pages/ProfessorWorkspace.jsx` (modified, +315/−52)
  - `frontend/officehours-app/src/styles.css` (modified, +34/−0)
- **Tests added:**
  - `backend/tests/test_upload_status.py`: `test_upload_list_groups_one_row_per_file_and_tracks_status`, `test_students_and_tas_cannot_list_or_reject_uploads`
- **CI result:** Both checks succeeded. Backend tests completed 2026-10-11T02:49:04Z. Product app build and audit completed 2026-10-11T02:44:49Z.
- **How I checked it:** TODO
- **What I changed or rejected and why:** TODO
- **Mistakes or surprises:** TODO
- **Next prompt:** TODO
