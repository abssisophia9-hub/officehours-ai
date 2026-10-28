# Consistency notes

The approved project title for the mid-term report is:

OfficeHours AI: A Professor-Approved, Course-Scoped Study Agent Integrated into a Unified Platform for Students, TAs, and Professors

The strategic planner and the other role agents are future work. This file
lists statements that conflict with each other or with the study-agent design
on `main` (merge of pull request 121, commit `26c1095`). None of these files
were edited.

Line numbers are from that commit.

## Title and what the product is

| File and line | What it says | Conflict |
| --- | --- | --- |
| `README.md` line 1 and lines 3–8 | The heading is "OfficeHours AI". The next paragraph calls it a "Campus office-hours triage system" and says custom-trained Ask Triage agents (Analyzer, Matcher, Synthesizer) classify each ask. The approved title is not used. The study agent is not named in that opening. | Conflicts with the approved title, which centers a professor-approved, course-scoped study agent. Ask Triage and Help Coach do exist in the code. The conflict is the title and the opening emphasis, not a claim that those modules are absent. |
| `docs/proposal.md` line 4 | "OfficeHours AI: An AI-Assisted Triage System for Finals-Week Academic Support" | A different title from the approved one. |
| `docs/presentations/README.md` lines 19 | A one-sentence pitch that names Quiet ask, Rooms, Help Coach, and the professor stamp on the Study Agent. | Does not use the approved title. It does describe the study-agent gate. Listed because a report that copies this sentence would not match the approved title. |

## Names that no longer match the code

| File and line | What it says | Conflict |
| --- | --- | --- |
| `README.md` lines 10–12 | Product docs say Ask Triage, while "some API fields, DB columns, and the service module still use the historical prefix `oracle_*` / `oracle_service.py`". | `docs/glossary.md` lines 3–4 say the historical `oracle_*` prefix was renamed to `triage_*` and that implementation identifiers now match the product names. A search of this commit did not find `oracle_service.py`. Screenshot filenames and `frontend/professor-dashboard/src/components/OracleIntelligencePanel.jsx` still use the old word. The README and the glossary disagree about whether the rename is finished. |
| `docs/ai_nlp_design.md` lines 7–9 | "docs, UI, and code all say Ask Triage" and the `oracle_*` prefix was renamed. | Same disagreement with `README.md` lines 10–12. |

## Local models only, versus the study-agent checker

| File and line | What it says | Conflict |
| --- | --- | --- |
| `docs/ai_nlp_design.md` lines 13–15 | "The assessed runtime path uses custom-trained local models only." Prompted Claude calls are disabled by default. | The default is still off: with the policy variables unset, `llm_enabled()` is false. The sentence "only" conflicts with the current study-agent path. When the kill switch, the external flag, demo mode, a provider, and for Gemini the free-tier acknowledgement are on, `run_study_agent` calls Gemini or Claude. |
| `docs/prelaunch_checklist.md` lines 9–10 | Ask Triage, Help Coach, and the Study Agent are "local models (MiniLM + scikit-learn + approved-KB retrieval), behind one model interface. The external Claude API is allowed for the MVP". | Groups the Study Agent with local models, then names Claude as the external API. The study-agent checker on this commit is Gemini or Claude, selected by `OFFICEHOURS_LLM_PROVIDER`, and Gemini is the default model name in `gemini_client.py`. |
| `docs/prelaunch_checklist.md` line 21 | "Study Agent is `POST /agent/ask` and quotes stamped KB only." | `_checked_answer` does not show the quote. A failed check returns `CHECK_MISS_ANSWER` and does not quote the chunk. The retrieval draft, used when the kill switch or a guard blocks the call, does paste the chunk. |
| `docs/prelaunch_checklist.md` lines 22–23 | "One Claude interface." "There is no remote LLM call on the request path. Intake is an in-process joblib predict." | Intake is local. `POST /agent/ask` can make a remote call. "One Claude interface" does not mention Gemini. "No remote LLM call" is false of the armed study-agent path. |
| `docs/system_architecture.md` lines 83–86 | The tech stack is FastAPI, SQLite, sentence-transformers, scikit-learn, React, and WebSockets. "External LLM disabled by default". | The default is true of the code. The stack list does not mention `run_study_agent` or the Gemini and Claude checker, so it does not describe the current study-agent path. |

## What the student is said to see

| File and line | What it says | Conflict |
| --- | --- | --- |
| `docs/AGENT_POLICY.md` lines 24–31 | "The student sees one of four replies," and the table gives four different strings: the checked answer, `I couldn't confirm an answer in the approved course material.`, the staff paragraph, and the busy paragraph. | The API returns those strings. `frontend/officehours-app/src/pages/StudentAgentPage.jsx` line 6 sets `NOT_FOUND` to `No professor-approved material answers this.` Line 212 uses that string when `should_seek_help` is true or `matched_count` is 0. Busy, staff, refusal, and failed-closed all have those flags, so the page shows one sentence. |
| `docs/AGENT_POLICY.md` line 28 and line 73 | Line 28 says the quote stays in the check and is not shown. Line 73 says "The student-facing answer is a sentence or two plus a quote that was checked." | The two sentences conflict. `_checked_answer` discards the quote and does not append it. Line 28 matches the code. Line 73 does not. |
| `docs/AGENT_POLICY.md` lines 7–8 | The numbered pipeline says retrieve "with the existing search (same arguments, same 0.42 cutoff, same filters)" and then check budgets. | `run_study_agent` calls `search_approved_entries` without passing 0.42. The search default is `DEFAULT_SEARCH_THRESHOLD` 0.35. The 0.42 comparison is `WEAK_MATCH_CONFIDENCE` after search. Question length, the cutoff, the kill switch, and the guards run before the breaker and the budgets. |
| `docs/AGENT_POLICY.md` lines 134–136 | The log outcome list ends with "The older guards log `flag_off` or `demo_off`." | `_log` also accepts `provider_off` and `ack_off`, and `run_study_agent` logs those names. |
| `docs/AGENT_POLICY.md` lines 159–162 | "`--rerun-errors` ... reloads the newest `docs/eval_results/with_check_*.json`". | `scripts/run_study_eval.py` takes the path given to `--rerun-errors`. It does not search for the newest with-check file. `newest_baseline_file` is used for the baseline path, not for that flag. |

## Future work that the docs do not state

A search of `docs/` and other Markdown for "strategist", "planner agent", and "role agent" found no page that says a strategic planner, or role agents beyond the current Ask Triage, Help Coach, and Study Agent, are future work.

`docs/proposal.md` line 23 lists "Multi-language support (future work)" and does not mention the planner.

Ask Triage (Analyzer, Matcher, Synthesizer) and Help Coach are implemented. They are not the future role agents in the sentence above. The conflict is that the approved boundary is not written in the docs, while `README.md` lines 3–8 present the triage pipeline as the description of the product.
