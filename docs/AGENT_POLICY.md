# Study agent policy

The study agent has one entry point, `run_study_agent` in
`backend/app/ai/agent_policy.py`. The pipeline is fixed:

1. Validate the question.
2. Retrieve with the existing search (same arguments, same 0.42 cutoff, same filters).
3. Check budgets and the circuit breaker.
4. Make at most one checker call.
5. Validate that reply.
6. Choose a response and write one log line.

The model does not choose an action and does not call tools. There is no
loop. Invalid JSON, a bad quote, an unknown chunk, and any error that is
not a dropped connection are not sent again.

A dropped connection (`TimeoutError` or `URLError`) is retried once inside
that single checker call. That retry already existed so a blip does not
fail a good question. The pipeline still invokes the checker once and does
not write a second prompt.

## Outcomes

The student sees one of four replies:

| Outcome | When | Reply |
| --- | --- | --- |
| Answer with citation | The checker returns a quote that appears verbatim in the cited chunk, and the answer is within the length cap | Short answer, then `based on <file>, p.<page> approved by the professor`. The quote stays in the check and is not shown. |
| Refuse | The checker says the material does not answer, or the reply fails validation | `I couldn't confirm an answer in the approved course material.` |
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

## Limits

Every value is an environment variable. A missing, blank, non-numeric, or
non-positive value falls back to the default. The study agent uses its own
`RateLimiter` instance. `OFFICEHOURS_RATE_LIMIT=false` disables only the
HTTP limiter (login, asks, the agent route). It does not disable these
budgets, including under pytest.

Per-user windows apply only when the caller passes a user id. `POST
/agent/ask` passes the signed-in user. The eval harness does not, so a
75-question run is not charged to one anonymous person. The course window
applies when `course_id` is set.

| Variable | Default | What trips it | Why this number |
| --- | --- | --- | --- |
| `OFFICEHOURS_LLM_MAX_QUESTION_CHARS` | 2000 | Question longer than this, and the kill switch is on | A study question, not a pasted chapter. The HTTP schema still allows 4000 characters so the request is not rejected at the door; past 2000 the model is not asked. |
| `OFFICEHOURS_LLM_MAX_CHUNKS` | 3 | Only the first N retrieved chunks are sent | The checker cites one chunk. Three is the existing top-k the quote check was built for. The checker also refuses a fourth chunk if a caller bypasses this. |
| `OFFICEHOURS_LLM_MAX_INPUT_TOKENS` | 3000 | Estimated input (system prompt + JSON of the question and chunks, characters ÷ 4) is larger | Three course chunks are capped at about 900 characters each. With the question and the system prompt that lands near 1,500 tokens. 3,000 leaves headroom and still refuses a pathological paste. |
| `OFFICEHOURS_LLM_MAX_OUTPUT_TOKENS` | 400 | Passed to the provider as `maxOutputTokens` | The reply is one small JSON object: a short answer, one quote, one chunk id. 400 is the existing check budget. |
| `OFFICEHOURS_LLM_MAX_ANSWER_CHARS` | 600 | A passing answer longer than this fails closed (`answer_too_long`) | The student-facing answer is a sentence or two plus a quote that was checked. A longer body was not validated line by line, so it is refused rather than truncated. |
| `OFFICEHOURS_LLM_TIMEOUT_SECONDS` | 10 | Provider call timeout | A study question should return while the student is still looking at the page. 10 seconds matches the existing client. |
| `OFFICEHOURS_LLM_USER_PER_MINUTE` | 4 | Sliding 60-second window per user | Enough to rephrase a couple of times. Not enough to script the route. |
| `OFFICEHOURS_LLM_USER_PER_DAY` | 30 | Sliding 24-hour window per user | One study session of short questions. A forgotten loop stops the same day. |
| `OFFICEHOURS_LLM_COURSE_PER_DAY` | 150 | Sliding 24-hour window per course | The fixed eval is 75 questions. 150 covers that run plus one rerun of the whole set, and still caps a course if a client loops. |
| `OFFICEHOURS_LLM_GLOBAL_CALLS_PER_DAY` | 200 | UTC calendar day, all courses | A demo day, not a campus rollout. Above one full eval (75) and the per-course cap, below an unbounded retry loop. |
| `OFFICEHOURS_LLM_GLOBAL_TOKENS_PER_DAY` | 200000 | UTC calendar day, input + output tokens reported by the provider | 200 calls at the 3,000-token input cap is 600,000, so this trips first if prompts grow. At the expected ~1,500 input tokens it allows the call cap to be the one that fires. |
| `OFFICEHOURS_LLM_BREAKER_FAILURES` | 3 | Consecutive failed-closed results | Three bad replies in a row means the provider or the parser is down. A model refusal (`not_answerable`) and a passed answer both reset the counter. They are not outages. |
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

The checker still requires one JSON object, a real boolean `answerable`
(the string `"true"` does not count), a `supporting_chunk_id` from the
chunks that were sent, and a `quote` that appears verbatim in that chunk.
The question and the chunk text are sent as a JSON value under an explicit
system rule that they are data, not instructions. The policy adds the
answer-length cap above. Anything else is a refusal, logged as
`failed_closed_error`, and it counts toward the breaker.

## Cache

Key: SHA-256 of the course id, the question normalized (lowercase, internal
whitespace collapsed), `chunk_id:status` for each chunk sent, the configured
model name, and the prompt version `study-answer-check-v1`.

Stored value: the decision (`passed` or `not_answerable`), the short answer,
the quote, the cited chunk id, and the chunk ids. No user id, no name, no
email. Errors, quota stops, and busy stops are not cached.

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
| `model` | `not_answerable` | No. The model refused. |
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
