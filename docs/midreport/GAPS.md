# Gaps for the mid-term report

This is a list of what is missing or weak. It is not a claim that the missing
work was done.

## Questions

The saved with-check file has `human_written.n` = 0 and an empty question
list. Every scored question in that file is `author: agent_generated`. There
is no independent human-written set in that result. A report that says a
person wrote the 75 questions would be false. The questions are in
`docs/eval_questions/study_agent_questions.json`. This session did not
re-score them with a model.

## Prompt log

`docs/prompt_log.md` lines 18–19 say **Model**, **Exact prompt**, **Written
by**, and **What I changed or rejected and why** stay `TODO`. The log says
not to reconstruct a prompt from a commit message or a pull-request body.
This session did not find the model names or the exact prompts that produced
the merged pull requests. Those fields are empty on purpose. They cannot be
filled from memory in the report.

## One model, one prompt, one run

The saved Gemini result is one file: model `gemini-3.5-flash-lite`, prompt
version `study-answer-check-v1`, `created_at` `20261025T010745Z`. This session
did not find a second with-check file for another model, another prompt, or
a repeated run of the same questions. The 95% Wilson intervals in
`EVIDENCE.md` describe sampling uncertainty on these counts. They are not a
measurement of run-to-run variance. Counts stay the primary numbers.

The checker does not judge whether the short answer adds facts that are not
in the quote. `IJ13` in the saved file is harness-incorrect with checker
outcome `passed`. That is one observed case of a pass the harness rejected.
The quote text is not copied into this note.

## Invalid key

The task names a placeholder-key run: an invalid key, 3 failed-closed errors,
the breaker opened, and no invented answers. This session searched
`docs/eval_results` and the Markdown docs and did not find that run. It is
UNVERIFIED. The code path is real and was not executed here: `complete_gemini`
raises `RuntimeError` when `GEMINI_API_KEY` is missing, before `urlopen`, and
`verify_course_answer` records an unexpected exception as `api_error` without
a second prompt. An HTTP error from a rejected key is a different branch.
Neither branch was run. The report can describe the code. It cannot cite
"3 errors" as a result until a saved log exists.

The fake-client script in this branch does show a provider exception becoming
`api_error` and then, with the breaker threshold set to 1, the next question
returning busy with zero further model calls. That is a unit of the policy
with a scripted exception. It is not the invalid-key run.

## Equation-heavy PDFs

`backend/app/services/material_extract.py` extracts PDF pages with `pypdf`.
This session did not find a fixture, a test, or a result file for an
equation-heavy PDF. Extraction of that kind of page is untested here. Do not
write that it fails or that it succeeds.

## Other weaknesses

The Study Agent page replaces busy, the staff form, a model refusal, and a
failed check with one sentence, `No professor-approved material answers this.`
A reader of the API, or of `docs/AGENT_POLICY.md`, would expect four
different replies. `docs/midreport/CONSISTENCY.md` cites the lines.

The cache, the breaker, and the daily call and token counters are memory in
one process. A second process, or a restart, does not share them. The report
should not describe them as a campus-wide quota.

The token estimate that trips `input_tokens` is characters divided by four.
The Gemini usage totals in the saved file are the provider's reported tokens
on that one run. They are not the estimate.

`docs/AGENT_POLICY.md` still says `--rerun-errors` reloads the newest
with-check file, and its log section omits `provider_off` and `ack_off`.
Those are documentation bugs. This branch was not allowed to edit that file.

The approved title is written in `docs/proposal.md`, `docs/midreport/INTERIM_REPORT.md`, and `docs/midreport/CONSISTENCY.md`. The statement that a strategic planner and other role
agents are future work is not written in the repository docs. `README.md`
still opens on the triage system. Cover-page identity (student name, ID,
supervisor) was not found as a report fact in the repository.
`docs/product_overview.md` uses `S.Abssi@aui.ma` only as an example of email
shape. Do not copy that onto the cover unless it is the student's own record.

No literature review was written. Candidate references, if they are used,
still need the checklist in the report draft. None of them were opened in
this session.

The Gemini numbers were not re-run. There is no key in this environment, and
the task forbids a live call. Latency, tokens, and the 74/75 figure are only
as good as the saved file.
