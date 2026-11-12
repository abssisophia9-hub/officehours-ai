# Evidence register

Every number below is labeled. "Re-run now" means this session ran the command
on 28 October 2026 (Africa/Casablanca) and did not call a model. "From a saved
file" means the value was read from a file already in the repository and was
not produced by a live model call in this session. "UNVERIFIED" means this
session did not find a source that shows it.

The retrieval-only re-run wrote
`docs/eval_results/baseline_retrieval_only_20261028T110927Z.json` and then
that file was deleted so the saved baseline would not gain a second copy.
Category counts, the four filter modes, both backends, both sweeps, and both
separation blocks matched
`docs/eval_results/baseline_retrieval_only_20261010T180847Z.json`.
The figures read the saved file, not the deleted re-run.

Ambient shell variables at the start of the session included
`OFFICEHOURS_LLM_ENABLED=true`, `OFFICEHOURS_ALLOW_EXTERNAL_LLM=true`,
`OFFICEHOURS_DEMO=true`, `OFFICEHOURS_LLM_PROVIDER=gemini`, and
`OFFICEHOURS_GEMINI_FREE_TIER_ACK=true`. No `GEMINI_API_KEY` was set.
The baseline command set `OFFICEHOURS_LLM_ENABLED=false` and
`DATABASE_URL=sqlite:////tmp/orchestration-baseline.db`. The script also
forces `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` for a baseline. No key was
printed or stored.

| Claim | Value | Source | Date produced | Who | Status |
| --- | --- | --- | --- | --- | --- |
| Test suite on this branch | `266 passed, 18 warnings in 124.30s`. Exit 0. Warnings are deprecation warnings from Starlette and scikit-learn, not failures. | `venv/bin/python -m pytest -q` from `backend/`. Log mtime 28 October 2026, 11:11:17 Africa/Casablanca. | 28 October 2026, 11:11 Africa/Casablanca | This agent session | Re-run now |
| New demo-script test | `1 passed in 3.64s` | `venv/bin/python -m pytest tests/test_demo_orchestration.py -q` | 28 October 2026, before 11:10 Africa/Casablanca | This agent session | Re-run now |
| Kill switch default | `llm_enabled=False` | Import of `app.ai.agent_policy` after unsetting `OFFICEHOURS_LLM_ENABLED` | 28 October 2026, before 11:10 Africa/Casablanca | This agent session | Re-run now |
| Question length default | 2000 | `max_question_chars()` with the Orchestrator variables unset | same print | This agent session | Re-run now |
| Chunks sent | 3 | `max_chunks()` | same print | This agent session | Re-run now |
| Input-token estimate cap | 3000 | `max_input_tokens()` | same print | This agent session | Re-run now |
| Output-token cap | 400 | `max_output_tokens()` | same print | This agent session | Re-run now |
| Answer-length cap | 600 | `max_answer_chars()` | same print | This agent session | Re-run now |
| Checker timeout | 10 seconds | `timeout_seconds()` | same print | This agent session | Re-run now |
| Per user per minute | 4 | `user_per_minute()` | same print | This agent session | Re-run now |
| Per user per day | 30 | `user_per_day()` | same print | This agent session | Re-run now |
| Per course per day | 150 | `course_per_day()` | same print | This agent session | Re-run now |
| Global calls per UTC day | 200 | `global_calls_per_day()` | same print | This agent session | Re-run now |
| Global tokens per UTC day | 200000 | `global_tokens_per_day()` | same print | This agent session | Re-run now |
| Breaker | 3 failures, then 5 minutes | `breaker_failures()`, `breaker_minutes()` | same print | This agent session | Re-run now |
| Cache TTL | 3600 seconds | `cache_ttl_seconds()` | same print | This agent session | Re-run now |
| Prompt version | `study-answer-check-v1` | `PROMPT_VERSION` | same print | This agent session | Re-run now |
| Answer cutoff | 0.42 | `WEAK_MATCH_CONFIDENCE` | same print | This agent session | Re-run now |
| Search include threshold | 0.35 | `DEFAULT_SEARCH_THRESHOLD` | same print | This agent session | Re-run now |
| Gemini model default | `gemini-3.5-flash-lite` | `DEFAULT_GEMINI_MODEL` | same print | This agent session | Re-run now |
| Transport attempts inside one check | 2 | `ANSWER_CHECK_ATTEMPTS` | same print | This agent session | Re-run now |
| Gemini client requests per minute | 5. A non-positive or non-numeric value also falls back to 5. The client sleeps. It does not return busy. Claude does not read this variable. | `OFFICEHOURS_LLM_RPM` default in `gemini_client._rpm` | Read from the module in this session. Not part of the Orchestrator-defaults print. | This agent session | Read from the source this session. The function was not called. |
| Retrieval questions, agent-generated | 75 per backend | Saved baseline `sections.agent_generated.n`, and the re-run | Saved file `created_at` `20261010T180847Z` (10 October 2026, 18:08:47 Africa/Casablanca). Re-run stamp `20261028T110927Z` (28 October 2026, 11:09:27 Africa/Casablanca). | Saved file git author Cursor Agent, commit `58e50a8` (10 October 2026, 18:10:07 Africa/Casablanca). Re-run: this agent session. | Re-run now, and it matched the saved file |
| Production cutoff during retrieval | 0.42, `cutoff_changed` false | Saved baseline and the re-run | same | same | Re-run now, matched the saved file |
| Sentence-transformers, both filters, in-document | correct 17/20, wrong source 3, spurious 0, hidden page 0 | `backends.sentence-transformers...modes.both_on.counts.in_document` | same | same | Re-run now, matched the saved file |
| Sentence-transformers, both filters, hard negative | correct 9/20, spurious 11/20 | same `hard_negative` cell | same | same | Re-run now, matched the saved file |
| Sentence-transformers, both filters, unapproved only | correct 7/10, spurious 3/10 | same `unapproved_only` cell | same | same | Re-run now, matched the saved file |
| Sentence-transformers, both filters, other course | correct 5/10, spurious 5/10 | same `other_course_only` cell | same | same | Re-run now, matched the saved file |
| Sentence-transformers, both filters, injection | correct 12/15, spurious 3/15 | same `injection` cell | same | same | Re-run now, matched the saved file |
| Retrieval-only correct total, sentence-transformers, both filters | 50/75 | Sum of the five `correct` cells above | Computed in this session from those cells | This agent session | Re-run now, matched the saved file |
| 95% Wilson interval, retrieval in-document 17/20 | 0.6396 to 0.9476 | `docs/midreport/figures/build_figures.py` | 28 October 2026, Africa/Casablanca | This agent session, from the saved counts | Computed now from the saved file. The interval is not a second experiment. |
| 95% Wilson, retrieval hard negative 9/20 | 0.2582 to 0.6579 | same script | same | same | Computed now from the saved file |
| 95% Wilson, retrieval unapproved 7/10 | 0.3968 to 0.8922 | same script | same | same | Computed now from the saved file |
| 95% Wilson, retrieval other course 5/10 | 0.2366 to 0.7634 | same script | same | same | Computed now from the saved file |
| 95% Wilson, retrieval injection 12/15 | 0.5481 to 0.9295 | same script | same | same | Computed now from the saved file |
| Ablation, approval off, unapproved-only, sentence-transformers | correct 1/10, hidden page 9, cited unapproved 9 | `modes.approval_off.counts.unapproved_only` | Baseline dates above | same | Re-run now, matched the saved file |
| Ablation, course filter off, other-course, sentence-transformers | correct 1/10, hidden page 7, cited other course 7 | `modes.course_off.counts.other_course_only` | same | same | Re-run now, matched the saved file |
| Ablation, both filters off, injection, sentence-transformers | correct 7/15, hidden page 7 | `modes.both_off.counts.injection` | same | same | Re-run now, matched the saved file |
| Lexical, both filters, in-document | correct 16/20, wrong source 3 | `backends.lexical...both_on.counts.in_document` | same | same | Re-run now, matched the saved file |
| Lexical, both filters, hard negative | correct 9/20, spurious 11 | same `hard_negative` cell | same | same | Re-run now, matched the saved file |
| Sweep at 0.42, sentence-transformers | in-document correct citation 17/20, hard-negative answered 11/20, spurious 22/55 | `threshold_sweep` where `threshold` is 0.42, and the re-run printout | same | same | Re-run now, matched the saved file |
| Sweep at 0.42, lexical | in-document 16/20, hard-negative answered 11/20, spurious 23/55 | same | same | same | Re-run now, matched the saved file |
| Separation | `separates=false` for both backends. Sentence-transformers: lowest correct top-page score 0.4208, highest hard-negative 0.625, correct top pages 17/20. Lexical: lowest 0.3846, highest hard-negative 1.0, correct top pages 17/20. | `separation` in the saved file and the re-run printout | same | same | Re-run now, matched the saved file |
| Gemini check file | `with_check`, provider and checker `gemini`, model `gemini-3.5-flash-lite`, prompt `study-answer-check-v1`, embedding `sentence-transformers`, cutoff 0.42, `cutoff_changed` false | `docs/eval_results/with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json` | File `created_at` `20261025T010745Z` (25 October 2026, 01:07:45 Africa/Casablanca). Git commit `d69bf39` at 25 October 2026, 01:17:43 Africa/Casablanca. | Git author Cursor Agent. Not this session. | From the saved results file, not re-run |
| Gemini questions | 75 agent-generated, 0 human-written | `sections.agent_generated.n` and `sections.human_written.n` | same saved file | same | From the saved results file, not re-run |
| Gemini harness-correct | in-document 20/20, hard negative 20/20, unapproved 10/10, other course 10/10, injection 14/15, total 74/75 | `sections.agent_generated.counts` | same | same | From the saved results file, not re-run |
| 95% Wilson, with-check in-document 20/20 | 0.8389 to 1.0000 | `build_figures.py` on those saved counts | 28 October 2026 | This agent session | Computed now from the saved file, not a re-run of Gemini |
| 95% Wilson, with-check hard negative 20/20 | 0.8389 to 1.0000 | same | same | same | Computed now from the saved file |
| 95% Wilson, with-check unapproved 10/10 | 0.7225 to 1.0000 | same | same | same | Computed now from the saved file |
| 95% Wilson, with-check other course 10/10 | 0.7225 to 1.0000 | same | same | same | Computed now from the saved file |
| 95% Wilson, with-check injection 14/15 | 0.7018 to 0.9881 | same | same | same | Computed now from the saved file |
| 95% Wilson, with-check 74/75 | 0.9283 to 0.9976 | same | same | same | Computed now from the saved file |
| Checker outcomes on those 75 | `passed` 21, `not_answerable` 21, `below_cutoff` 33. Called 42 times. `failed_closed_error` 0. `refused_by_model` 21. | Top-level fields and a count of `questions[].check.outcome` in the saved file | same saved file | Counted in this session from the saved file | From the saved results file, not re-run |
| Where the 21 passes and 21 refusals sit | All 20 in-document items `passed`. Hard negative: 9 `below_cutoff`, 11 `not_answerable`. Unapproved: 7 `below_cutoff`, 3 `not_answerable`. Other course: 5 and 5. Injection: 12 `below_cutoff`, 2 `not_answerable`, 1 `passed`. | Same question array | same | This session, from the saved file | From the saved results file, not re-run |
| The one harness miss | `IJ13`, category `injection`, checker outcome `passed`, called true, retrieved `demo_kettle_notes.pdf` page 4 chunk 4, similarity 0.4448, `spurious_answer` true. Saved quote length 60 characters. Saved short answer length 14 characters. The question text is in the file and is not copied here. | That question object | same | This session, from the saved file | From the saved results file, not re-run |
| Gemini latency | median 674.56 ms, worst 5413.82 ms, median of calls 857.98 ms, worst of calls 5413.82 ms | `usage` in the saved file | same | Cursor Agent git author | From the saved results file, not re-run |
| Gemini tokens | input 19740, output 1846, per question 263.2 input and 24.61 output, over 75 questions and 42 calls | `usage` in the saved file | same | same | From the saved results file, not re-run |
| Orchestration demo, fake client | 23 rows. Two model calls for a verified pass: the quote check and the entailment yes. One model call for a refusal, invalid JSON, a bad quote, an unknown chunk, a provider error, and an over-long answer. Two calls for a timeout. Zero calls for cutoff, cache, every busy limit, the kill switch, and every guard. | `backend/venv/bin/python scripts/demo_orchestration.py`, asserted by `tests/test_demo_orchestration.py`. | 3 November 2026, Africa/Casablanca | This agent session | Re-run for the entailment gate. No network and no key. |
| Pull request 102 merged to main | 10 October 2026, 18:01:14 Africa/Casablanca | `gh pr view 102` `mergedAt` `2026-10-10T18:01:14Z`, base `main` | that timestamp | GitHub, read this session | From GitHub, not re-run |
| Pull request 103 merged to main | 10 October 2026, 18:19:00 Africa/Casablanca | `gh pr view 103`, base `main` | `2026-10-10T18:19:00Z` | GitHub, read this session | From GitHub |
| Pull request 115 merged to main | 24 October 2026, 16:41:28 Africa/Casablanca | `gh pr view 115`, base `main` | `2026-10-24T16:41:28Z` | GitHub, read this session | From GitHub |
| Pull request 116 merged to main | 24 October 2026, 22:29:51 Africa/Casablanca | `gh pr view 116`, base `main` | `2026-10-24T22:29:51Z` | GitHub, read this session | From GitHub |
| Pull request 117 merged to main | 24 October 2026, 23:12:41 Africa/Casablanca. Title: Add a study-agent policy that budgets one model call. | `gh pr view 117`, base `main`, merge commit `21db97ef` | `2026-10-24T23:12:41Z` | GitHub, read this session | From GitHub |
| Pull request 120 merged to main | 27 October 2026, 20:35:27 Africa/Casablanca | `gh pr view 120`, base `main` | `2026-10-27T20:35:27Z` | GitHub, read this session | From GitHub |
| Pull request 121 merged to main | 27 October 2026, 21:17:25 Africa/Casablanca. This branch's `main` is that merge, commit `26c1095`. | `gh pr view 121` and `git log -1` | `2026-10-27T21:17:25Z` | GitHub, read this session | From GitHub |
| Pull requests 122 and 125 | Merged into `cursor/study-conversations-a8bd`, not into `main`. They are not the code this note describes. | `gh pr view` `baseRefName` | 122 at `2026-10-27T21:52:58Z`. 125 at `2026-10-28T08:43:26Z`. | GitHub, read this session | From GitHub |
| Invalid-key run of three failed-closed errors and an open breaker | Not found in `docs/eval_results` or in a committed log. | Search of the repository in this session | none | unknown | UNVERIFIED |
| Student name, ID, and supervisor | Not stored as a report identity in this repository. `docs/product_overview.md` uses `S.Abssi@aui.ma` as an email-shape example. | Repository search | none | unknown | UNVERIFIED as a cover-page identity |
