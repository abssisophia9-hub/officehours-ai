# Capstone Design Interim Report

This draft follows the section order of the School of Science and Engineering
interim-report template supplied for this project. It is Markdown because this
change adds no document toolchain. The university form still asks for Times
New Roman on the cover and in the body. Paste this text into that form.
Do not treat a heading below as a signed page.

Student name, student ID, and supervisor are not stored as a report identity
in the repository. `docs/product_overview.md` uses `S.Abssi@aui.ma` as an
example of how an AUI email is shaped. That example is not copied onto this
cover. Status of the cover identity: UNVERIFIED. The student fills it.

## Student conduct and copyright

The conduct and copyright page is the university form. It is not signed in
this file. The student signs that page. This draft does not claim a signature.

## Title

OfficeHours AI: A Professor-Approved, Course-Scoped Study Agent Integrated into a Unified Platform for Students, TAs, and Professors

## Capstone Report

Interim report. Fall 2026. The course code on the form is filled by the student.
This draft was assembled on 28 October 2026 (Africa/Casablanca) from the
repository at the merge of pull request 121 (`26c1095`) plus the notes in
`docs/midreport/`.

## Student Statement

The student writes and signs this statement. It is not invented here.

## Approved by Supervisor

The supervisor's name and signature are written on the form by the supervisor.
They are not invented here.

## ACKNOWLEDGEMENTS

The student writes this page. This draft does not invent thanks, a family
dedication, or a supervisor quotation.

## CONTENT

The numbered sections below are the template's contents. Page numbers are
assigned when the text is placed in the university document.

## LIST OF FIGURES

1. Study-agent architecture. `docs/midreport/figures/architecture.svg`. Built from the code path, not from a measurement.
2. Orchestration pipeline. `docs/midreport/figures/pipeline.svg`. Built from `run_study_agent`.
3. Outcome states. `docs/midreport/figures/outcomes.svg`. Built from the API strings and the Study Agent page.
4. Retrieval-only versus with-check. `docs/midreport/figures/retrieval_vs_check.svg`. Built from the two saved result files named on the figure.
5. Threshold sweep. `docs/midreport/figures/threshold_sweep.svg`. Built from the saved retrieval baseline. The production cutoff 0.42 is marked and was not changed.

## LIST OF TABLES

1. Control defaults, printed from the module. `docs/midreport/EVIDENCE.md` and `docs/ORCHESTRATION.md`.
2. Retrieval-only counts and the with-check counts, with 95% Wilson intervals beside them. `docs/midreport/EVIDENCE.md`.
3. Fake-client outcome trace. Printed by `scripts/demo_orchestration.py` in this session.

## ABSTRACT (ENGLISH)

OfficeHours AI is a course-scoped study agent inside one web application for
students, teaching assistants, and professors. A professor approves course
material before the agent may use it. Retrieval is local. A single policy
pipeline, `run_study_agent`, may then make at most one checker call. On the
saved Gemini run, which was not repeated in this draft, the harness scored
74 of 75 agent-generated questions correct. The checker was called 42 times,
refused 21, and skipped 33 because the top retrieval score was below 0.42.
It reported no failed-closed errors on that file. The retrieval-only baseline
on the same question file, re-run in this session without a model, scored
50 of 75 correct with both filters on and sentence-transformers. No cutoff
separated every correct in-document citation from every hard negative.
The quote check shows that a quote occurs in the cited chunk. It does not
show that the short answer adds no facts. There are no human-written
questions in the saved with-check file.

Keywords: course-scoped retrieval, professor approval, answer checking, study agent, office hours

## RESUME (FRENCH)

OfficeHours AI est un assistant d'étude limité à un cours, dans une seule
application pour les étudiants, les assistants et les professeurs. Le
professeur approuve le matériel avant que l'assistant puisse s'en servir.
La recherche documentaire est locale. Une seule politique, `run_study_agent`,
peut ensuite appeler le vérificateur au plus une fois. Dans le fichier Gemini
déjà enregistré, et non relancé pour ce brouillon, le harnais a compté 74
bonnes réponses sur 75 questions produites par un agent. Le vérificateur a
été appelé 42 fois, a refusé 21 questions et en a laissé 33 sans appel parce
que le meilleur score était sous 0,42. Ce fichier ne contient aucune erreur
fermée. La base de recherche seule, relancée dans cette session sans modèle,
a compté 50 bonnes réponses sur 75 avec les deux filtres et
sentence-transformers. Aucun seuil ne sépare toutes les bonnes citations des
négatifs difficiles. La vérification de la citation montre que le passage
existe dans le fragment. Elle ne montre pas que la réponse courte n'ajoute
aucun fait. Le fichier enregistré ne contient aucune question écrite par une
personne indépendante.

Mots clés : recherche limitée au cours, approbation du professeur, vérification de réponse, assistant d'étude, heures de bureau

## 1 INTRODUCTION

The approved title names one study agent: professor-approved, limited to the
student's course, and placed in the same application that students, teaching
assistants, and professors already use. On this commit the agent is
`POST /agent/ask`. The policy that decides whether a model is called is
`run_study_agent` in `backend/app/ai/agent_policy.py`, added in pull request
117, merged to `main` on 24 October 2026 at 23:12:41 (Africa/Casablanca).

Retrieval does not use Gemini. The include threshold is 0.35. The answer
cutoff is 0.42. Both were printed from the constants in this session. The
checker, when every guard allows it, is one call to Gemini or Claude. The
saved measurement used `gemini-3.5-flash-lite` and the prompt version
`study-answer-check-v1`.

This interim draft reports that design and the numbers that can be traced to
a file or to a command run on 28 October 2026. It does not add a literature
review.

## 2 PROBLEM STATEMENT

Students need answers that stay inside the material a professor has approved
for that course. A retrieval score alone does not do that. On the saved
sentence-transformers baseline, with both the approval filter and the course
filter on, 17 of 20 in-document questions received a correct citation and 11
of 20 hard negatives were answered spuriously. The same file shows that no
threshold separates those two sets: the lowest correct top-page score is
0.4208 and the highest hard-negative score is 0.625.

The study agent therefore keeps the retrieval cutoff and adds a closed check.
The model may only accept or refuse the supplied chunks. A failed check does
not fall back to the unread retrieval draft. The code does not claim that a
passed short answer is free of added facts. The saved row `IJ13` is the
observed case where the checker returned `passed` and the harness marked the
row spurious.

## 3 FUNCTIONAL AND NON-FUNCTIONAL REQUIREMENTS

Functional, as implemented on this commit:

- A professor's approval is the gate. `search_approved_entries` can require `status == approved`, the course id, and `entry_kind == course_material`. The study path sets `course_material_only=True`.
- A question whose best hit is missing or below 0.42 is not sent to a model.
- A question that passes the cutoff is either answered from the retrieval draft, when the kill switch or a guard blocks the call, or sent through one checker call.
- A passed check returns the short answer and the line `based on <file>, p.<page> approved by the professor`. The quote is not shown.
- A refusal, invalid JSON, a quote that is not in the chunk, an unknown chunk id, a provider error, or an answer over 600 characters returns `I couldn't confirm an answer in the approved course material.`
- Busy, when a limit or the breaker fires, returns the busy paragraph and does not show the draft.
- The Study Agent page currently replaces every seek-help response with one sentence. That is the behavior of `StudentAgentPage.jsx`. It is not the four API strings.

Non-functional, as implemented:

- The kill switch defaults to off. A key by itself does not call the model.
- Gemini also needs demo mode, the external-call flag, and `OFFICEHOURS_GEMINI_FREE_TIER_ACK`. The module warning says the free tier may use prompts to improve Google products and that only synthetic demo data may be sent.
- Budgets are the defaults printed in `docs/ORCHESTRATION.md`: 4 per user per minute, 30 per user per day, 150 per course per day, 200 calls and 200000 tokens per UTC day, and a breaker of 3 failures for 5 minutes.
- Those counters are in one process. They are not a campus quota.
- The model does not choose tools and does not loop. One checker invocation may retry a dropped connection once, and the Gemini client may retry HTTP 429 or 503 inside that same invocation.

The strategic planner and further role agents are not requirements of this
commit. They are future work. The repository docs do not yet say that.
Ask Triage and Help Coach are separate features that already exist. They are
not the study-agent checker.

## 4 RELATED WORK

No paper was opened for this draft. The lines below are candidates only.
Each one stays out of the reference list until the checklist is done.
This section is not a literature review.

| Candidate | Why it might be cited | Verification checklist | Status |
| --- | --- | --- | --- |
| The Gemini `generateContent` documentation for the endpoint in `backend/app/ai/gemini_client.py` (`https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`) | The checker calls that URL. | Open the current vendor page. Confirm the path, the `x-goog-api-key` header, and `responseFormat`. Record the date the page was read. Do not cite a URL that the page no longer serves. | UNVERIFIED. The endpoint string is in the code. The documentation page was not opened. |
| Sentence-BERT, Reimers and Gurevych, for the embedding model `all-MiniLM-L6-v2` | The baseline and the saved check use that model name when the backend is sentence-transformers. | Confirm authors, year, title, venue, and DOI from the paper itself. Confirm that `all-MiniLM-L6-v2` is the model the paper or its model card names. | UNVERIFIED |
| Wilson's score interval | The figures draw a 95% interval beside small counts. | Confirm the 1927 *Journal of the American Statistical Association* paper from a copy, including the title "Probable Inference, the Law of Succession, and Statistical Inference". Confirm the formula against that paper before calling the interval a Wilson interval in the final PDF. | UNVERIFIED as a citation. The arithmetic used in `build_figures.py` is the usual score interval with z = 1.959963984540054. |
| scikit-learn logistic regression, for Ask Triage | `docs/training_data.md` names `request_classifier.joblib` as embeddings plus logistic regression. | Confirm the artifact exists and that the report really needs this citation. Ask Triage is not the study-agent checker. | UNVERIFIED |

## 5 SYSTEM DESIGN

### 5.1 SOFTWARE DEVELOPMENT LIFECYCLE

The repository shows short pull requests merged to `main`, with backend tests
and a saved evaluation file. Pull request 103 merged the retrieval ablation
on 10 October 2026 at 18:19 (Africa/Casablanca). Pull request 117 merged the
one-call policy on 24 October 2026 at 23:12. Pull request 121, the commit
this report describes, merged on 27 October 2026 at 21:17. The formal
lifecycle name required by the syllabus is not written in the repository, so
it is not guessed here.

### 5.2 SYSTEM ARCHITECTURE

A professor upload becomes knowledge rows. The student question enters
`run_study_agent`. Search is local. The 0.42 rule runs before any model call.
Guards and budgets run before the cache. The cache, on a miss, is followed
by one call to `verify_course_answer`. The figure is
`docs/midreport/figures/architecture.svg`. The numbered pipeline is
`docs/midreport/figures/pipeline.svg`. The outcome figure is
`docs/midreport/figures/outcomes.svg`.

### 5.3 DATABASE DESIGN

The default database is SQLite at `backend/officehours.db`, created at startup
unless `DATABASE_URL` is set. Tests use `sqlite:///:memory:`. Course material
for the study agent is stored as `knowledge_entries`. The model in
`backend/app/models/knowledge.py` includes the course id, status, file name,
page, chunk index, `entry_kind`, and `answer_draft`. This draft does not
redraw every table. A full entity-relationship figure was not produced.

### 5.4 TECHNOLOGY STACK AND FRAMEWORKS

The running product is the FastAPI backend and `frontend/officehours-app`.
Retrieval embeddings are sentence-transformers `all-MiniLM-L6-v2`, or a
lexical backend when `OFFICEHOURS_CLUSTERING_BACKEND=lexical`. The product
script uses the lexical backend. The saved baseline and the saved Gemini file
used sentence-transformers. The checker is a direct HTTPS call in
`gemini_client.py`, or the Claude client, and only after the policy allows
it. No new dependency was added for this draft. matplotlib was not installed,
so the charts are SVG.

## 6 AI USE, EVALUATION AND EVIDENCE

### 6.1 AI TOOLS AND PURPOSE

Two different uses have to stay separate.

The product's checker, when it is armed, sends the question and at most three
approved chunks to Gemini or Claude and accepts a JSON object with a boolean,
a chunk id, a short answer, and a quote. The saved run used Gemini
`gemini-3.5-flash-lite`. This session did not call it. No API key was present,
and none was added.

Development of the repository has used Cursor agents. The saved result files
are committed by the git author "Cursor Agent". `docs/prompt_log.md` leaves
the model name and the exact prompt as `TODO`. This draft does not reconstruct
those prompts.

### 6.2 AI ASSISTED DEVELOPMENT ACTIVITIES

What is recorded is the pull-request history, not the prompts. The prompt log
covers pull requests 99 through 107 and says the exact prompt was not kept.
Later pull requests through 121 are on `main`. Pull requests 122 and 125 are
on `cursor/study-conversations-a8bd` and are not part of the code this draft
describes. The activities that can be stated are the merges and the tests,
not a transcript of what a model was asked.

### 6.3 AI OUTPUT EVALUATION

Counts are the primary numbers. The intervals only show how wide a 95% score
interval is on a sample this small. Retrieval counts were re-run in this
session and matched the saved file. Gemini counts are from the saved file,
not re-run.

Retrieval-only, sentence-transformers, both filters, 75 questions:

| Category | Correct | 95% Wilson interval on the rate |
| --- | --- | --- |
| In document | 17/20 | 0.6396 to 0.9476 |
| Hard negative | 9/20 | 0.2582 to 0.6579 |
| Unapproved only | 7/10 | 0.3968 to 0.8922 |
| Other course | 5/10 | 0.2366 to 0.7634 |
| Injection | 12/15 | 0.5481 to 0.9295 |
| Total | 50/75 | not a single binomial trial of one kind of question; the interval is not reported for the mixture |

With-check, saved Gemini file, same 75 questions, harness `correct`:

| Category | Correct | 95% Wilson interval on the rate |
| --- | --- | --- |
| In document | 20/20 | 0.8389 to 1.0000 |
| Hard negative | 20/20 | 0.8389 to 1.0000 |
| Unapproved only | 10/10 | 0.7225 to 1.0000 |
| Other course | 10/10 | 0.7225 to 1.0000 |
| Injection | 14/15 | 0.7018 to 0.9881 |
| Total | 74/75 | 0.9283 to 0.9976 |

On that file the checker outcome was `passed` for 21 questions, all 20
in-document questions plus injection `IJ13`. It was `not_answerable` for 21
and `below_cutoff` for 33. Calls: 42. Input tokens: 19740. Output tokens:
1846. Median latency 674.56 ms. Worst latency 5413.82 ms. Median latency of
the calls that were made: 857.98 ms. `failed_closed_error` is 0.
`human_written` is 0.

The ablation on the same retrieval file shows what the filters do. With
approval off, sentence-transformers, the unapproved-only cell is 1/10 correct
and 9 cited-unapproved. With the course filter off, the other-course cell is
1/10 correct and 7 cited from the other course. With both filters on, those
hidden-page counts are 0. The re-run matched these cells.

The sweep does not find a separating cutoff. At 0.42, sentence-transformers
still has 17/20 in-document correct citations, 11/20 hard negatives answered,
and 22/55 spurious answers. `separates` is false.

### 6.4 CRITICAL REFLECTION AND LIMITATIONS

The with-check gain is on 75 agent-generated questions and one run. The
Wilson intervals on the 10-question and 20-question cells are wide. A second
run could move them. The quote check can pass while the harness still marks
the answer spurious, as `IJ13` does. The page hides the difference between
busy, a weak match, a refusal, and a failed check. Equation-heavy PDF
extraction is untested. The invalid-key story of three failed-closed errors
is not in a saved file. The prompt log does not contain the prompts.

### 6.5 SUPORTING AI EVIDENCE

The template spells the heading this way. The evidence is:

- `docs/eval_results/baseline_retrieval_only_20261010T180847Z.json`
- `docs/eval_results/with_check_gemini_gemini-3.5-flash-lite_20261025T010745Z.json`
- `docs/midreport/EVIDENCE.md`
- `docs/midreport/figures/`
- `scripts/demo_orchestration.py` and `backend/tests/test_demo_orchestration.py`
- `docs/prompt_log.md`, which records that the exact prompts are missing

## 7 IMPLEMENTATION

The orchestration is documented in `docs/ORCHESTRATION.md`. The implementation
this draft relies on is already on `main`. This interim change does not modify
application code, the cutoff, the filters, or the saved result files. The one
new program is `scripts/demo_orchestration.py`. It stubs retrieval, injects a
fake checker, blocks `urlopen`, and prints a row for each outcome. A test
runs that script.

## 8 TESTING

On 28 October 2026 at 11:11 (Africa/Casablanca), from `backend/`:

`venv/bin/python -m pytest -q`

The suite printed `266 passed, 18 warnings in 124.30s` and exited 0. The
warnings are deprecation warnings. One of the 266 tests is
`test_demo_orchestration_script`, which was also run alone and printed
`1 passed in 3.64s`.

The retrieval baseline and its sweep were re-run with the kill switch off,
no API key, and a temporary database. Exit 0. The stamp on the file it wrote
was `20261028T110927Z`. Every filter mode, both embedding backends, both
sweeps, and both separation blocks matched the saved baseline. That new file
was deleted so the repository keeps a single saved baseline.

The Gemini file was not re-run.

## 9 DISCUSSION AND ANALYSIS

The cutoff 0.42 is a policy choice on overlapping scores, not a point that
makes the two classes separable. The checker is what moves the hard-negative,
unapproved, and other-course cells from partial scores to 20/20, 10/10, and
10/10 on this one file. Most of that movement is either a score below 0.42,
which never calls the model, or a model refusal. The 20 in-document questions
were all `passed` on the saved file. The remaining error is one injection
that the checker accepted.

Those sentences are about this sample. They are not a claim about a live
course, a second model, or a human-written set. The free-tier warning in the
Gemini client forbids sending real student data or real course material on
that tier. The report should keep the synthetic corpus and the saved file
attached to every Gemini number.

## 10 CONCLUSION

On this commit the study agent is a fixed pipeline in front of one optional
checker. Retrieval-only, re-run here, scores 50/75 with both filters and
sentence-transformers, and the score ranges overlap. The saved Gemini check,
not re-run here, scores 74/75 on the same agent-generated questions, with 42
calls, 21 refusals, 33 cutoff skips, and no failed-closed count in that file.
The pipeline fails closed instead of showing an unchecked draft. The quote
check does not certify the short answer. The evidence register is the source
for any number copied into the university form.

## 11 FUTURE WORK

The student has set the strategic planner and the other role agents as future
work. They are not in this commit, and the docs do not yet say so.

Also still open, and weak for this report until they exist:

- An independent human-written question set. The saved file has none.
- The exact prompts and model names in `docs/prompt_log.md`.
- A second model, a second prompt, or a repeated run.
- A saved log of an invalid-key run, if that result is going to be cited.
- A test of equation-heavy PDF extraction.
- A page that shows the four API outcomes instead of one sentence.
- A quota that survives a process restart, if a campus deployment needs one.

## REFERENCES

No reference is listed. Section 4 is a checklist of candidates that are still
UNVERIFIED. APA 7 entries are added only after that checklist is done. The
template's APA guidance was not re-fetched in this session.

## APPENDIX A CODE

The policy entry is `run_study_agent` in `backend/app/ai/agent_policy.py`.
The checker is `verify_course_answer` in `backend/app/ai/claude_client.py`.
The Gemini request is `complete_gemini` in `backend/app/ai/gemini_client.py`.
The student strings are in `backend/app/services/kb_agent_service.py`.
The page substitution is in `frontend/officehours-app/src/pages/StudentAgentPage.jsx`.
The offline trace is `scripts/demo_orchestration.py`.
This appendix does not paste those files.

## APPENDIX B

Supporting tables and the command log live in `docs/midreport/EVIDENCE.md`,
`docs/midreport/CONSISTENCY.md`, `docs/midreport/GAPS.md`, and
`docs/midreport/FIGURES.md`.
