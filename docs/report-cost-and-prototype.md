# Cost estimation, prototype description, and software tests

**Date:** 2026-11-12  
**Branch:** `cursor/canvas-settings-token-db64` (PR #133; not merged)  
**Sources:** code under `backend/app/`, `docs/AGENT_POLICY.md`, `docs/ops_scale.md`, `docs/system_architecture.md`, Task a/b evidence.  
**Rule:** No invented token meters or cloud invoices. Provider prices only with cited URLs; otherwise **[VERIFY]**.

---

## Database and LLM configuration (from code)

### Database

| Item | Code / env |
| --- | --- |
| Default engine | **SQLite** — `DATABASE_URL` defaults to `sqlite:///./officehours.db` in `backend/app/database/session.py` |
| Tests | `DATABASE_URL=sqlite:///:memory:` |
| Campus option | Postgres via `DATABASE_URL=postgresql://…` (`docs/ops_scale.md`, `docker-compose.postgres.yml`); pool via `OFFICEHOURS_DB_POOL_SIZE`, `OFFICEHOURS_DB_MAX_OVERFLOW` |
| Schema | `Base.metadata.create_all` + `ensure_schema` (no Alembic) |

### LLM / model providers

| Path | Default in assessed FYP product | Env gates |
| --- | --- | --- |
| Ask Triage Analyzer / Matcher / Synthesizer | **Local** joblib + embeddings (`OFFICEHOURS_ANALYZER_BACKEND` default `ml`) | External Analyzer only if `OFFICEHOURS_ANALYZER_BACKEND=claude` **and** `OFFICEHOURS_ALLOW_EXTERNAL_LLM=true` |
| Help Coach | **Local** templates / KB draft helpers (`help_coach_service.py`) — no provider HTTP in that service | — |
| Study Agent answers | **Retrieval-only** when `OFFICEHOURS_LLM_ENABLED` is false (default) | Kill switch: `OFFICEHOURS_LLM_ENABLED` |
| Study Agent quote / entailment / recovery | Optional Gemini or Claude | Needs **all** of: `OFFICEHOURS_LLM_ENABLED=true`, `OFFICEHOURS_ALLOW_EXTERNAL_LLM=true`, `OFFICEHOURS_DEMO=true`, `OFFICEHOURS_LLM_PROVIDER=gemini\|claude`; Gemini also `OFFICEHOURS_GEMINI_FREE_TIER_ACK=true` + `GEMINI_API_KEY`; Claude `ANTHROPIC_API_KEY` |
| Default Gemini model | `gemini-3.5-flash-lite` (`GEMINI_MODEL` override) — `gemini_client.py` |
| Default Claude model | `claude-haiku-5-5` (`ANTHROPIC_MODEL` override) — `claude_client_legacy.py` / `agent_policy.py` |
| Embeddings (local) | `OFFICEHOURS_EMBEDDING_MODEL` default `all-MiniLM-L6-v2`; clustering may use `OFFICEHOURS_CLUSTERING_BACKEND=lexical` |

`.env.example` sets `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false` for the gated product path.

### LLM off vs on — triage and Study Agent

With the assessed defaults (`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`, `OFFICEHOURS_LLM_ENABLED=false`, Analyzer backend `ml`), **Ask Triage does not change when the Study Agent kill switch flips**: intake still runs local Analyzer → Matcher → Synthesizer (`analyze_question` / `match_ta` / `synthesize_solution` → joblibs), and the only way triage itself calls an external LLM is the non-default `OFFICEHOURS_ANALYZER_BACKEND=claude` plus the allow flag. For the **Study Agent**, LLM **off** means `run_study_agent` still embeds/searches approved course material and, if top similarity ≥ **0.42**, returns the retrieval draft (`_retrieval_answer`) with no provider HTTP; below 0.42 it returns the staff/Quiet-ask miss. LLM **on** (kill switch plus allow + demo + provider ready) keeps the same retrieval and cutoff first, then may spend quote-check / entailment / optional recovery calls (or fall back to the same retrieval draft if a gate is incomplete, or busy/refuse if budgets or checks fail) — it does **not** invent answers outside approved chunks.

---

## 1. LLM inventory (every external LLM call site)

Local classifiers / synthesizer / Help Coach are **not** billed LLM APIs; listed separately.

### A. External HTTP LLM calls (only when gates above are armed)

| # | Call | File / function | Model (default) | Trigger | Rough I/O size |
| --- | --- | --- | --- | --- | --- |
| 1 | Quote / answer check | `claude_client.verify_course_answer` → Gemini or Anthropic `complete` | Gemini: `gemini-3.5-flash-lite`; Claude: `claude-haiku-5-5` | Study Agent when kill switch + external flags on; after retrieval ≥ 0.42 | Cap: `OFFICEHOURS_LLM_MAX_INPUT_TOKENS` default **3000**; `OFFICEHOURS_LLM_MAX_OUTPUT_TOKENS` / `ANSWER_CHECK_MAX_TOKENS` **400**. Chunks: up to `OFFICEHOURS_LLM_MAX_CHUNKS` (3), ~900 chars each per policy docs. Exact measured tokens per ask: **[VERIFY]** (not metered in Task a; Task a ran retrieval-only) |
| 2 | Entailment verdict | `judge_entailment` (same clients) | Same as provider | After a passing quote check | Small JSON (answer + quote) in / boolean out — **[VERIFY]** exact tokens |
| 3 | Recovery choice | `choose_recovery` | Same | Only if entailment says no; inside attempt cap (≤3 attempts total) | Small JSON — **[VERIFY]** exact tokens |
| 4 | Legacy Analyzer LLM | `claude_client_legacy.analyze_question_llm` via `_complete_claude` | `ANTHROPIC_MODEL` / `claude-haiku-5-5` | Only if `OFFICEHOURS_ANALYZER_BACKEND=claude` + allow flag | **[VERIFY]** — not on FYP default path |
| 5 | Legacy Matcher/Synthesizer LLM | `claude_client_legacy` / `draft_with_claude` live path | Same | Legacy gated path; product synthesizer uses local `synthesize_with_model` | **[VERIFY]** — not default |

Transport: Gemini `generativelanguage.googleapis.com/.../generateContent`; Claude `https://api.anthropic.com/v1/messages`.

**Task a Study Agent asks:** ran with defaults → **0 external LLM calls** (retrieval + citation only). Confirmed by product defaults and evidence answers citing PDF chunks without check-gate phrasing.

### B. Local “models” (CPU, not provider $)

| Component | Artifact / lib | Trigger |
| --- | --- | --- |
| Analyzer | `request_classifier.joblib` + embeddings | `POST /requests/` Ask Triage |
| Matcher | `matcher_classifier.joblib` or course-scoped heuristic | Ask Triage |
| Synthesizer | `synthesizer_ranker.joblib` + teaching bank | Ask Triage |
| Learning style | `learning_style_classifier.joblib` | Intake |
| Clustering / Study retrieval embed | `sentence-transformers` `all-MiniLM-L6-v2` (or lexical) | Clusters + KB search |

---

## 2. Cost section (monthly bands)

### Cited provider prices (optional LLM path only)

| Provider / model | Free tier | Paid (per 1M tokens) | Source |
| --- | --- | --- | --- |
| Google `gemini-3.5-flash-lite` (Standard) | Input/output **Free of charge** on Free Tier | Input **$0.30**, Output **$2.50** (incl. thinking) | [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing) (page content retrieved 2026-11-12) |
| Anthropic Claude Haiku 5.5 (API id used in code: `claude-haiku-5-5`) | N/A (paid API) | Prompts ≤100K: input **$0.10** / output **$0.50** per 1M tokens | [Anthropic Claude Haiku](https://www.anthropic.com/claude/haiku) (retrieved 2026-11-12) |

### Assumptions (labeled — not measured invoices)

1. **Assessed FYP / default deploy:** `OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`, `OFFICEHOURS_LLM_ENABLED=false` → **$0/mo LLM**.
2. **Optional “checks on” scenario:** Gemini free tier for demo; paid tier only if campus leaves free tier — **[VERIFY]** which Google tier AUI would use.
3. **Usage sketch if checks on (assumption, not production telemetry):** ~5 Study Agent questions / active user / month that pass the 0.42 gate and spend **2** provider calls (quote + entailment), ~1.5k input + 0.2k output tokens each call → ~3k in + 0.4k out tokens per such question. Recovery adds more — ignored in the low band.
4. **Hosting:** single small VM/container for API+SPA at 50 users; modest vertical scale at 500; multi-instance + managed Postgres at 5,000. Dollar figures below are **illustrative assumption bands**, not quotes from a cloud bill — treat as **[VERIFY]** against actual AUI/IT pricing.
5. **DB:** SQLite file on app disk at 50–500 demo scale; Postgres at 5,000 (`docs/ops_scale.md`). Managed Postgres cost **[VERIFY]**.
6. **Third-party:** Canvas REST/LTI (institutional) — typically no per-call fee to the app **[VERIFY]** with AUI IT; optional Microsoft Entra / SMTP — usually covered by campus **[VERIFY]**; no mobile push vendor in code.
7. **Embeddings:** run on the same host CPU — folded into hosting, not a separate API bill.

### Monthly cost bands (USD, assumption)

| Users | LLM (default off) | LLM if Gemini free + checks on | LLM if Gemini **paid** Standard (assumption sketch) | Hosting+DB+misc (assumption band) | Notes |
| --- | --- | --- | --- | --- | --- |
| **50** | **$0** | **$0** (free tier) | ≈ negligible (~0.75 M in / 0.1 M out tok/mo → cents; formula from cited rates) **[VERIFY]** | **~$10–40** single VPS + SQLite | FYP/demo shape |
| **500** | **$0** | **$0** until free quota — then **[VERIFY]** | Rough order **~$1–5** if all active users hit the sketch (500×5×2 calls) **[VERIFY]** | **~$40–150** VPS + optional small Postgres | Still one product app |
| **5,000** | **$0** | Free tier **unlikely** to suffice **[VERIFY]** | Rough order **~$10–50**/mo under the same sketch; spikes if recovery loops — code caps via `OFFICEHOURS_LLM_GLOBAL_*` | **~$200–800+** app instances + managed Postgres + backups **[VERIFY]** | Needs real capacity plan |

**Claude instead of Gemini:** using Haiku 5.5 cited rates on the same sketch is still low single-digit to low tens of USD at 5,000 under the assumption — **[VERIFY]** with real call logs before budgeting.

**Canvas / Microsoft / SMTP:** no metered amounts found in-repo → **[VERIFY]** with IT.

---

## 3. Final prototype description (from actual code)

OfficeHours AI is a **modular monolith**: FastAPI (`backend/`, :8000) + one React SPA (`frontend/officehours-app`, :5180). Role is **per course membership** (student / TA / professor).

**Student path:** Quiet ask or Identify me → `POST /requests/` runs **Ask Triage** (local Analyzer → Matcher → Synthesizer) → live WS queue; Study Agent `POST /agent/ask` answers only from **professor-approved** KB (retrieval; optional gated LLM check). Rooms (`/help-room/`) and peer notes are separate classmate surfaces.

**TA path:** authenticated queue, claim → help → reply / group meeting; **Help Coach** assists mid-session without publishing to the student agent.

**Professor path:** stamp KB (`pending_review` → approved/rejected), Canvas materials sync, analytics / review insights. Live Canvas uses `CANVAS_BASE_URL` + `CANVAS_API_TOKEN` (settings); demo can use a local module mirror when credentials are absent and `OFFICEHOURS_DEMO=true`.

**Data:** default SQLite; Postgres-ready. **External LLM off by default.** Legacy three frontends under `frontend/*-dashboard` / `student-kiosk` are archives, not the product CI target.

---

## 4. Software tests description (real results)

| Item | Result |
| --- | --- |
| Backend pytest (Task b, 2026-11-12) | **277 passed, 0 failed**, 0 skipped; ~127s; 51 modules |
| Coverage % | **Not measured** — no `pytest-cov` in requirements **[VERIFY]** if later instrumented |
| Frontend automated tests | **None** (known limitation) |
| Task a Study Agent (live sync evidence) | **2 / 3 correct**; Q3 incorrect = ranking miss (asked lecture 1, cited lecture 2); **no retrieval code change** |
| Task a sync mechanism | Live Canvas API + smoke **bulk** `update_entry(status=approved)` (not professor UI) — see `docs/test_results.md` |

Primary write-up: `docs/test_results.md`. Store mirrors under `/cursor/stores/self/docs/`.

---

## Study Agent retrieval flow (from `agent_policy.run_study_agent`)

1. Validate length only when LLM enabled; always `search_approved_entries` (approved, course-scoped, course-material chunks).
2. If no hit or top similarity **&lt; 0.42** → staff miss (`should_seek_help`); **no LLM**.
3. If LLM kill switch **off** → return `_retrieval_answer` (cite best chunk); **0 LLM calls**.
4. If LLM **on** but provider/demo/allow incomplete → still `_retrieval_answer` (guards spend nothing useful).
5. If LLM **on** and ready: quote check (`verify_course_answer`) → on pass, **entailment** (`judge_entailment`); if entailment fails, optional **recovery** then re-search (attempt loop capped, default ≤3) — not free-form tools.
6. Low confidence / below cutoff never “guesses”; busy/refuse paths do not fall back to an unchecked draft when the check path was entered and failed closed.

---

## Known limitations (cost / report)

- No production token telemetry → LLM $ at scale are **sketches**.
- Hosting/DB dollar bands are **assumptions**, not invoices.
- Uvicorn `canvas_mode=local` during Task a = stale process **[VERIFY after restart]**.
- Q3 Study Agent ranking miss remains open; feature freeze forbids “fix by changing retrieval.”
- Task d PREP: `.cursor/rules/design.mdc` drafted; **no UI edits** until Sophia approves.
