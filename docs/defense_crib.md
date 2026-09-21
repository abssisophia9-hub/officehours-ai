# Defense crib — one page

Print this. Do not improvise past it.

## The product (10 seconds)

OfficeHours is **classifiers + retrieval + a professor gate**, not a campus ChatGPT.
Students ask. TAs are **staff on a course they already took** — one role per course,
not classmates in that section. Professors stamp what the Study Agent may quote.
If the stamp is weak, the agent refuses.

## Demo path (8 minutes)

Password `aui-demo`. Role is per course.

1. **Opening** — “Three seats. One login. One role per course.” Stop.
2. **Sara** `s.elidrissi@aui.ma` · CSC 2302 — Quiet ask or Identify me. Show
   **Ask Triage** (Analyzer → Matcher → Synthesizer). Open **My asks**. Ask the
   Study Agent something the KB does not have; it must refuse.
3. **Alice** `a.chen@aui.ma` · CSC 2302 — desk filter, claim, Help Coach on
   select, gold-label control. Help Coach never publishes to students. Second
   TA cannot steal a claim.
4. **Benali** `a.benali@aui.ma` — pending KB, stamp, hit-rate. “It retrieves
   what you stamped.”
5. If asked about Canvas / Microsoft: **code exists; campus credentials do not.**

## What is true in the code

- Quiet asks are invisible on a classmate’s `GET /requests/`. Status-by-code is a receipt.
- `/agent/ask`, stamps, analytics, TA queue, and `/ws` require a session + membership.
- Ingest lands in `pending_review`. Stamp before the agent can quote.
- Ask Triage is the product name. API fields and DB columns use `triage_*` (the historical `oracle_*` prefix was renamed).
- One product app: `frontend/officehours-app` (:5180). CI builds that + the backend.

## Numbers you may cite

| Number | Say this | Do not say this |
| --- | --- | --- |
| Analyzer CV ~85%, n=156 | Synthetic / curated holdout | Campus quality |
| Matcher silver ~87% | Self-consistency on demo names | Gold on real AUI TAs |
| Alice gold n=20 | Demo TA pass, does not retrain `.joblib` | A section lab |
| Weak-match 0.42 | Refuse threshold | “The agent understands the course” |
| Student hit-rate | Asks that hit a **stamp** | Model accuracy |

Live Matcher on a real roster is **heuristic** (tag overlap + per-course depth),
not `matcher_classifier.joblib`.

## Scale that is in the code: `DATABASE_URL` for Postgres, inbox + optional SMTP
on claim/reply, `limit`/`offset` on big lists, professor **Evaluate gold now**
(does not rewrite `.joblib` unless `OFFICEHOURS_ALLOW_RETRAIN`).

If they ask “what’s next?”

A **TA gold lab** (≥40 `human_gold` rows from one AUI section) — not a Likert
survey. IT: Entra + LTI key + Canvas token. Do not add an unconstrained LLM.
That breaks the gate.

## Forbidden sentences

- “TAs are also students in that same section.”
- “The agent understands the course.”
- “We have live AUI Microsoft / live Canvas modules.”
- “Oracle is a fourth AI product.”
- “The three frontends are the package.”
