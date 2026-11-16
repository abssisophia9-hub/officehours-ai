Historical document, written for an earlier version of the product (the Revision Strategist is now the Pedagogy Agent)

# Revision Agent — design (approved — LLM-in-loop)

**Status:** shipped on `revision-agent` — Gemini-in-the-loop with rule fallback.  
**Date:** 2026-11-12  
**Constraints:** no new deps; never store real grades in repo/DB; never send names/real grades to LLM or search; never print secrets.

## Product contract

| # | Behavior |
| --- | --- |
| 1 | **Grades:** synthetic only (seed / localStorage). Optional later: live Canvas = logged-in student’s **own** grades only, fetched ephemerally, **never** written to DB/repo. |
| 2 | Combine weak topics with **preferences** + a **deadline timeline**. |
| 3 | **Web search** for resources (bounded). |
| 4 | Emit a **study plan**: time slots + ordered resources for weak **text** assignments. |
| Loop | `observe → think → act(search) → check`, **max 3** iterations. |
| Privacy | LLM/search payloads: **topic labels**, **weakness level**, **preference**, public search **titles/snippets** only — no names, scores, Canvas IDs. |
| Links | Show only **load-checked** URLs from search (or course KB without fabricated URLs); always show **source**. |
| Mode | Response + UI plain text: **Planning mode: agent** vs **Planning mode: rule-based fallback**. |

Naming: UI says **Revision Strategist** (`/student/revision`). API: `POST /revision/plan`.

## Shape

| File | Role |
| --- | --- |
| `backend/app/models/revision.py` | Request/response Pydantic only (no SQLAlchemy grade table). |
| `backend/app/routes/revision.py` | `POST /revision/plan` (student-only). |
| `backend/app/services/revision_service.py` | observe→think→act→check; Gemini think + rule fallback; Orchestrator budget and safety controls. |
| `backend/app/services/revision_search.py` | Wikipedia (+ DDG), `link_ok`, caps. |
| `backend/tests/test_revision_agent.py` | Mocked LLM + gate/budget cases. |
| `frontend/officehours-app/src/pages/StudentRevisionPage.jsx` | Prefs, Build plan, mode label, Ask TA. |

Request grades carry `weakness` only (client maps scores first). Plans are not persisted in SQLite.

## LLM-in-loop

Provider: `OFFICEHOURS_LLM_PROVIDER=gemini`. Model: `GEMINI_MODEL` or `gemini-3.5-flash-lite`.

| Cap | Value |
| --- | --- |
| Loop iterations | **3** |
| LLM calls / plan | **≤3** |
| Searches / plan | **≤6** |
| Checked links / plan | **≤5** |
| HTTP rate limit | **10 / 60s** on `/revision/plan` |

Think JSON: `{ "action": "search"|"drop"|"stop", "query": string|null }`. Invalid → rule fallback for that step.

## Orchestrator budget and safety controls (shared `agent_policy`)

Revision does **not** enter the Orchestration Layer / `run_study_agent` (no quote check / entailment / recovery). It reuses the Orchestrator's budget and safety controls:

| Control | Where |
| --- | --- |
| Kill switch, allow+demo, Gemini ack, breaker, global budget | `revision_service._llm_gate` |
| Per-user / per-course windows | `_WINDOWS.allow_all(_window_checks(...))` **before each** `complete_gemini` (Study spend path); exceed → rule fallback |
| Global token/call spend + breaker | `_note_spend` / `_note_success` / `_note_failure` after Gemini |
| Mode log (one line / plan) | `agent_policy._log` with `limit="{mode}:{fallback_reason|'-'}"` — no grades, names, scores, or search results |

Fallback triggers: LLM off / no key / allow-demo-ack-provider gates / breaker / budget windows / Gemini errors / invalid JSON → **Planning mode: rule-based fallback**.

## Tests

| Case | Expect |
| --- | --- |
| No grades / LLM off / no key / invalid output | Rule-based mode |
| Synthetic grades | High weakness first; no numeric scores in body/queries |
| Failed / empty / invented URLs | Absent from resources |
| Mocked LLM search / stop / caps | Agent path; caps hold |
| Per-user window full | Fallback; `complete_gemini` not called |
| Per-course window full | Fallback; `complete_gemini` not called |
| Orchestrator log | One line each for agent and rule-based fallback; no grade/name/score |

## Out of scope

Install/run Canvas sync; print `.env`/tokens; live Canvas grades in UI; new pip/npm deps; Study Agent quote/entailment rebase.
