# Orchestration Layer

The Study Agent **Orchestration Layer** (short: the **Orchestrator**) has one
entry point, `run_study_agent` in `backend/app/ai/agent_policy.py`. The
pipeline is closed:

1. Validate the question.
2. Retrieve with the existing search (same arguments, same 0.42 cutoff, same filters).
3. Check budgets and the circuit breaker.
4. Quote check: accept one supplied chunk and copy a quote, or refuse.
5. Entailment check: one yes-or-no verdict that the quote fully supports the answer.
6. Only when entailment says no, one recovery choice, then another attempt.
7. Choose a response and write one log line.

Nothing is shown unless all three gates pass: retrieval at or above 0.42,
a faithful quote, and entailment `supports: true`. The model does not choose
search, the staff form, or busy. It chooses only inside the quote check
(accept or refuse), the entailment verdict (yes or no), and, after a no,
one recovery action.

A dropped connection (`TimeoutError` or `URLError`) is retried once inside
the quote check only. Entailment and recovery are one call each, with no
retry. Invalid JSON, a bad quote, an unknown chunk, and any other error
fail closed and do not start a recovery.

## Outcomes

The student sees one of four replies:

| Outcome | When | Reply |
| --- | --- | --- |
| Answer with citation | The quote check accepts one chunk, the quote is verbatim, the answer is within the length cap, and entailment says the quote fully supports the answer | Short answer, then `based on <file>, p.<page> approved by the professor`. The quote stays in the check and is not shown. |
| Refuse | The quote check refuses, validation fails, entailment says no until the attempt cap, or recovery abstains | `I couldn't confirm an answer in the approved course material.` An abstain uses `This isn't covered in the course materials.` |
| Staff form | Retrieval is below 0.42, before any model call | Today's "I don't have professor-approved course material…" plus Quiet ask |
| Assistant busy | A limit fired or the circuit breaker is open | "The study assistant is busy right now…" plus the same staff hint |

Busy and a failed check do not fall back to the unverified retrieval draft.
The draft is returned only when the kill switch is off, or when a guard
refuses the call before any model request: the external-call flag, demo
mode, an unset provider, or a missing Gemini free-tier acknowledgement.

## Kill switch

`OFFICEHOURS_LLM_ENABLED` defaults to **false**.

While it is false, a question at or above 0.42 gets today's retrieval
answer and the model is not called. The cache is not read and the budgets
are not spent. Below 0.42 the staff form is unchanged.

`scripts/run_study_eval.py --with-check` turns the kill switch on for that
process only. A real call still needs `OFFICEHOURS_ALLOW_EXTERNAL_LLM`,
`OFFICEHOURS_DEMO`, `OFFICEHOURS_LLM_PROVIDER` (`gemini` or `claude`), and
for Gemini `OFFICEHOURS_GEMINI_FREE_TIER_ACK`. Any of those guards, with the
kill switch on, keeps the retrieval answer and does not spend a budget slot.
`scripts/run_product.sh` sets the kill switch only when that provider call
is already armed. A key by itself stays retrieval-only.

## Limits (Orchestrator budget and safety controls)

Every value is an environment variable. A missing, blank, non-numeric, or
non-positive value falls back to the default. The Orchestrator's budget and
safety controls use their own `RateLimiter` instance.
`OFFICEHOURS_RATE_LIMIT=false` disables only the HTTP limiter (login, asks,
the agent route). It does not disable these budgets, including under pytest.

Per-user windows apply only when the caller passes a user id. `POST
/agent/ask` passes the signed-in user. The eval harness does not, so a
75-question run is not charged to one anonymous person. The course window
applies when `course_id` is set.

| Variable | Default | What trips it | Why this number |
| --- | --- | --- | --- |
| `OFFICEHOURS_LLM_MAX_QUESTION_CHARS` | 2000 | Question longer than this, and the kill switch is on | A study question, not a pasted chapter. The HTTP schema still allows 4000 characters so the request is not rejected at the door; past 2000 the model is not asked. |
| `OFFICEHOURS_LLM_MAX_CHUNKS` | 3 | Only the first N retrieved chunks are sent on the first attempt | The quote check cites one chunk. Three is the existing top-k. A recovery widen may raise the later attempt to 6, which is the ceiling. |
| `OFFICEHOURS_AGENT_MAX_ATTEMPTS` | 3 | Quote-check attempts on one student question | Clamped to 2 or 3. Each attempt is one quote check. Entailment runs only after a pass. Recovery runs only after entailment says no, and not on the last attempt. |
| `OFFICEHOURS_LLM_MAX_INPUT_TOKENS` | 3000 | Estimated input (system prompt + JSON of the question and chunks, characters ÷ 4) is larger | Three course chunks are capped at about 900 characters each. With the question and the system prompt that lands near 1,500 tokens. 3,000 leaves headroom and still refuses a pathological paste. |
| `OFFICEHOURS_LLM_MAX_OUTPUT_TOKENS` | 400 | Passed to the provider as `maxOutputTokens` | The reply is one small JSON object: a short answer, one quote, one chunk id. 400 is the existing check budget. |
| `OFFICEHOURS_LLM_MAX_ANSWER_CHARS` | 600 | A passing answer longer than this fails closed (`answer_too_long`) | The student-facing answer is a sentence or two plus a quote that was checked. A longer body was not validated line by line, so it is refused rather than truncated. |
| `OFFICEHOURS_LLM_TIMEOUT_SECONDS` | 10 | Provider call timeout | A study question should return while the student is still looking at the page. 10 seconds matches the existing client. |
| `OFFICEHOURS_LLM_USER_PER_MINUTE` | 4 | Sliding 60-second window per user | Enough to rephrase a couple of times. Not enough to script the route. |
| `OFFICEHOURS_LLM_USER_PER_DAY` | 30 | Sliding 24-hour window per user | One study session of short questions. A forgotten loop stops the same day. |
| `OFFICEHOURS_LLM_COURSE_PER_DAY` | 150 | Sliding 24-hour window per course | The fixed eval is 75 questions. 150 covers that run plus one rerun of the whole set, and still caps a course if a client loops. |
| `OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY` | 200 | UTC calendar day, all courses, one count per quote check, entailment verdict, or recovery | A demo day, not a campus rollout. A verified answer spends two calls. 200 still covers one 75-question eval, and it stops a recovery loop. |
| `OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY` | 200000 | UTC calendar day, input + output tokens reported by the provider | 200 calls at the 3,000-token input cap is 600,000, so this trips first if prompts grow. At the expected ~1,500 input tokens it allows the call cap to be the one that fires. |
| `OFFICEHOURS_LLM_BREAKER_FAILURES` | 3 | Consecutive failed-closed results | Three bad replies in a row means the provider or the parser is down. A model refusal (`not_answerable`), an entailment no (`unsupported`), an abstain, and a passed answer all reset the counter. They are not outages. |
| `OFFICEHOURS_LLM_BREAKER_MINUTES` | 5 | How long the breaker stays open | Long enough that a tight retry loop stops. Short enough that a demo can continue after a brief outage. |
| `OFFICEHOURS_LLM_CACHE_TTL_SECONDS` | 3600 | Age of a cached decision | About a lecture hour. Approval changes drop the row immediately; the TTL only bounds rows whose text did not change. |

When any limit or the open breaker fires, the response is busy and the
staff hint is set (`should_seek_help`). The retrieval paragraph is not
used. A full window is checked before the cache, so a student who is over
their cap does not receive a cached answer either. Another student is not
charged for that and can still take a cache hit: the cache has no user id.

The per-user and per-course windows are recorded only after the cache
misses, and all of them are recorded or none of them are. A request cannot
take a per-user slot and then fail the course cap.

Global calls and tokens roll over at UTC midnight, separate from the
sliding windows.

## Output checks

The quote check still requires one JSON object, a real boolean `answerable`
(the string `"true"` does not count), a `supporting_chunk_id` from the
chunks that were sent, and a `quote` that appears verbatim in that chunk.
The question and the chunk text are sent as a JSON value under an explicit
system rule that they are data, not instructions. The Orchestrator adds the
answer-length cap above. Anything else is a refusal, logged as
`failed_closed_error`, and it counts toward the breaker. A failed quote
check does not call entailment.

The entailment check is a second prompt. It sees only the short answer and
the quote, and it must return `{"supports": true}` or `{"supports": false}`.
`true` counts only when it is a JSON boolean. `true` means every claim in
the answer is stated by the quote. `false` does not show the answer. Invalid
JSON or a transport error fails closed and does not recover.

## Corrective loop

When entailment says no, and an attempt remains under the cap, one recovery
call chooses the next step from why that gate failed. The prompt includes
the question, the answer, the quote, and the reason that the quote does not
fully support the answer. The reply is one of:

| Action | What the pipeline does |
| --- | --- |
| `reformulate` | Search again with the model's `query`, then run the quote check on that query. The query is not logged. |
| `widen` | Raise retrieval `top_k` by 2, capped at 6. The 0.42 cutoff stays. |
| `narrow` | Set retrieval `top_k` to 1. The 0.42 cutoff stays. |
| `abstain` | Stop. The student sees `This isn't covered in the course materials.` |

A weak re-search returns the staff form. It does not show a draft and it
does not take another recovery. An invalid recovery fails closed. The cap
is the whole student question: a later attempt that would pass the global
call or token budget returns busy and does not show the unverified answer.
Per-user and per-course windows are still charged once per question, before
the first call.

## Cache

Key: SHA-256 of the course id, the question normalized (lowercase, internal
whitespace collapsed), `chunk_id:status` for each chunk sent on the first
retrieval, the configured model name, the prompt version
`study-answer-check-v1`, and the gate version
`study-entailment-v1+recovery-v1`.

Stored value: the decision (`passed` or `not_answerable`), the short answer,
the quote, the cited chunk id, and the chunk ids. A `passed` row is stored
only after entailment says yes. Abstain, an entailment no, errors, quota
stops, and busy stops are not cached. No user id, no name, no email, and no
reformulated query.

The row is dropped when:

- its TTL passes
- `update_entry` changes `status` or `answer_draft`
- an upload is approved or rejected (`_stamp_upload`)

Status is both part of the key and a reason to delete. A chunk whose
approval flipped cannot be served from the previous decision.

## Log line

One line per request, logger `officehours.agent_policy`:

```text
agent_policy outcome=%s model=%s latency_ms=%.1f input_tokens=%s output_tokens=%s limit=%s
```

`outcome` is one of `answered`, `refused_by_model`, `failed_closed_error`,
`quota`, `busy`, `cache_hit`. Below the cutoff logs `staff`. The kill
switch logs `disabled`. The older guards log `flag_off` or `demo_off`.

`limit` names what fired (`question_length`, `input_tokens`,
`user_per_minute`, `user_per_day`, `course_per_day`, `global_calls`,
`global_tokens`, `circuit_breaker`, `answer_length`, `kill_switch`) or `-`.

The line has no question text, no chunk text, no user id, and no API key.
Token counts on a cache hit or a budget refusal are zero because nothing
was sent.

## Harness

`evaluate_with_check` records `prompt_version`, the model, and `miss_source`
on each question:

| `miss_source` | Checker outcome | Rerun? |
| --- | --- | --- |
| `model` | `not_answerable`, `unsupported`, or `abstain` | No. The model refused or abstained. |
| `error` | `invalid_json`, `api_error`, `rate_limited`, `daily_quota`, `answer_too_long` | Yes. |
| `rejected` | `unfaithful`, `unknown_chunk` | No. The quote check failed; sending it again will not fix the chunk. |
| `quota` | `quota` or `busy` | No. |
| `cutoff` | Below 0.42, no call | No. |

The printout reports `refused_by_model` and `failed_closed_error` as
separate counts. `--rerun-errors` requires `--with-check`. It reloads the
newest `docs/eval_results/with_check_*.json`, keeps finished questions, and
sends only the error rows again. It does not rewrite a baseline file.

Windows PowerShell, from the repo root:

```powershell
$env:OFFICEHOURS_DEMO = "true"
$env:OFFICEHOURS_ALLOW_EXTERNAL_LLM = "true"
$env:OFFICEHOURS_LLM_ENABLED = "true"
$env:OFFICEHOURS_LLM_PROVIDER = "gemini"
$env:OFFICEHOURS_GEMINI_FREE_TIER_ACK = "true"
$env:GEMINI_API_KEY = "<your key>"
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
$env:OFFICEHOURS_CLUSTERING_BACKEND = "sentence-transformers"
.\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini
.\backend\venv\Scripts\python.exe scripts\run_study_eval.py --with-check --provider gemini --rerun-errors docs\eval_results\with_check_gemini_gemini-3.5-flash-lite_<stamp>.json
```

`--with-check` sets `OFFICEHOURS_LLM_ENABLED` for that process even if the
shell forgot it.
