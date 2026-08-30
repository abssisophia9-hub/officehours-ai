# Repo audit — what to fix, improve, upgrade

Written 30 Aug 2026 after a full-repo pass of `backend/`, `frontend/officehours-app/`,
legacy shells, and `docs/`. Extra weight on **AI for the three parties**
(student / TA / professor). This is a backlog, not a claim that the FYP is
unfinished.

Companion: [`session_log_opening_auth_canvas.md`](session_log_opening_auth_canvas.md),
[`agent_performance.md`](agent_performance.md), [`fyp_evidence.md`](fyp_evidence.md),
[`ai_nlp_design.md`](ai_nlp_design.md).

**Honest one-liner on the AI:** the platform is **classifiers + retrieval + a
professor gate**, not a campus ChatGPT. That is the right FYP story. Upgrades
should make those three pieces *truer per course*, not louder.

---

## Priority key

| Tag | Meaning |
| --- | --- |
| **P0** | Wrong, leaky, or a defense landmine if you host / claim it |
| **P1** | AI or product quality the three parties will feel |
| **P2** | Hygiene, naming, docs, leftover shells |

---

## What is already solid (do not “upgrade” these away)

- One login, **role per course**, Quiet ask vs Identify me, Rooms + Hilbert ŵ.
- Ask Triage runs local models by default (`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`).
- Study Agent **refuses** when the approved KB is weak (`should_seek_help`) — correct.
- Student refuse path already links to Quiet ask (`#ask`) and Stuck Room.
- Help Coach does **not** publish to the student agent.
- FAQ-from-cluster and FAQ-from-insight **are** on the professor workspace.
- LTI 1.3 + Microsoft SSO **code** exists; campus credentials do not.
- Backend pytest is real (~149 cases). Opening story is approved.

`AGENTS.md` is **stale**: it still describes a Three.js Student → TA → Professor
guest path. That courtyard is gone. The cloud-setup copy that called
`backend/app/ai/*` docstring stubs is also wrong — those modules are imported
at runtime (`oracle_service` → `claude_client` → Analyzer / Matcher / Synthesizer).

---

## P0 — campus / security / claims

Auth is **uneven**. Rooms, peer notes, TA queue, Help Coach, Canvas status,
and review-insights are locked. Intake, the Study Agent, KB stamps, and most
analytics are not.

| Endpoint | Auth today | Why it matters |
| --- | --- | --- |
| `POST /agent/ask` | none | Anyone can query any `course_id`’s approved KB and write `kb_ask_events`. Omit `course_id` → search **all** approved rows campus-wide. |
| `POST /requests/` | none | Spam + pending-KB poison off-demo. Quiet ask still creates a real triage row. |
| `GET /requests/`, `GET /requests/{id}` | none | Full queue + names / IDs / question text. |
| `GET /knowledge/`, `GET /knowledge/{id}` | none | Lists **pending drafts**, not just approved FAQs. |
| `PATCH /knowledge/{id}` | **none** | Anyone who can reach the API can **stamp or unstamp** the Study Agent. The UI sends a token; the route ignores it. |
| `POST /knowledge/from-cluster` | none | Creates KB drafts without a professor check. |
| `GET /analytics/*` (heatmap, clusters, oracle-metrics, kb-hit-rate, gold-labels, lifetime-confusion) | none | Course struggle + gold labels leak. Review-insights is the exception (locked). |
| `POST /analytics/gold-labels` | none | Poison the evaluation set. |
| `POST /actions/recommendations/` | none | Anyone can schedule a group meeting. |
| `GET /office-hours/` + write | none | Calendar mutation. |
| `WS /ws` | none | Live queue events to any socket. |

**Also P0:**

1. **CORS is `allow_origins=["*"]` with `allow_credentials=True`.** Tighten to the SPA origin before hosting.
2. **Host wiring:** `VITE_API_BASE` must not stay `127.0.0.1:8000`; SPA fallback; `OFFICEHOURS_DEMO=false`; favicon / OG tags.
3. **IT blockers (not code):** Microsoft app registration; Canvas LTI developer key + `CANVAS_BASE_URL` / `CANVAS_ACCESS_TOKEN`. Without these, do not claim live AUI login or live modules.
4. **Defense wording:** cite CV / silver / gold with caveats. Do not cite seed gold as quality. Do not say “the agent understands the course” — say “it retrieves what you stamped.”
5. **The gate the product sells is not the gate the code runs.** Professor copy says “Nothing reaches students until you approve it.” All three ingest buttons send `auto_approve: true`. `launch_from_canvas` also syncs with `auto_approve=True` on first student launch **and** every professor launch. Materials can enter `/agent/ask` with no human stamp.

**Fix order for auth:** `get_current_user` + `require_course_role` on writes first (`PATCH /knowledge`, `/agent/ask`, `/requests`, `/from-cluster`, `/actions`), then reads. Demo mode can stay looser if you keep an unsigned kiosk; off-demo must not.

---

## P0 / P1 — AI by party

### Student — Course Study Agent (`POST /agent/ask`, `kb_agent_service.py`)

**What it is:** embed the question, retrieve approved entries, paste the best
`answer_draft` if similarity ≥ 0.42, else refuse and push Quiet ask / Rooms.
Frontend already sends `course_id: activeCourse.id` and shows a seek-help
banner. The API does not require either.

| Upgrade | Why |
| --- | --- |
| Auth + membership + **required** `course_id` | Isolation. Today omit = search every approved row. |
| Cite **module / FAQ title**, not `#id (72% match)` | Trust. Students cannot map `#184` to “Week 4 hashing slides.” |
| Prefill Quiet ask / Room from the failed question | Links exist; the question is not copied. That is the product moment. |
| Show hit-rate on the student card | `GET /analytics/kb-hit-rate` exists and is unused here. Honesty: “3 of 10 asks this week had a stamped answer.” |
| Live Canvas walker only downloads `.txt` / `.md` / `.html` | Real slides are PDF / PPTX. Manual upload already uses `material_extract.py`. Live sync should download the Canvas file URL and run the same extractor. Pages (HTML) already work. |

**Do not:** add an unconstrained LLM that answers from classmate notes or Rooms
posts. That breaks the gate you already sold. Peer notes stay a human path.

**Also:** Ask Triage’s Synthesizer neighbor search (`oracle_service._similar_kb_hits`)
does **not** pass `course_id`, so a CSC 2302 hint can be built from a CSC 3374
FAQ. Help Coach **does** scope by `request.course_id`. Align them.

---

### TA — Ask Triage Matcher + Help Coach

**What it is:** Analyzer (embedding LogReg + CSC keyword overlays + heuristic
difficulty / ETA) → Matcher (LogReg over **demo TA names** + queue penalty) →
Synthesizer (teaching-bank RAG + style ranker) → pending KB draft. Help Coach
later (`POST /ta/assist/`, auth OK): similar opens, KB neighbors, Socratic
**templates**, draft / rewrite from the same bank. Coach never publishes.

| Upgrade | Why |
| --- | --- |
| Prefer **course-scoped load balance** when memberships exist | `build_course_matcher_roster` already returns course TAs. The trained classifier still scores **Alice / Bob / Priya / Sam**. Unseen AUI `display_name`s get a 0.05 × tag-overlap prior — almost random. Heuristic overlap + queue depth should win for unknown names. |
| Stop reseeding `DEFAULT_TA_ROSTER` off-demo | `ensure_default_roster` runs on every intake. A community DB that once had demo on can keep leaking demo names. |
| Course-condition or drop `TOPIC_OVERLAYS` | They are CSC-hardcoded (red-black, hashing, round-robin). An MTH / COM ask that hits a keyword gets a CSC-looking Analyzer title. |
| One taxonomy for the queue | `classify_and_recommend` **and** Analyzer both run. `oracle_service` then overwrites category from Analyzer’s `ml_category`. The student card still shows Analyzer’s display label. Pick one source of truth. |
| Help Coach “this draft was useless” | Drafts are retrieval + glue. That is fine. Missing signal is `gold_hint_useful` from the TA who actually helped. |
| Show **why** group-help fired | Cluster id vs shared category is already in `match_reason`. Surface it on the badge. |
| Hide learning-style unless confidence is high | A 12-word ask is not a style. The TA card treats it as fact. |

**Do not:** replace Help Coach with a live LLM tutor. The FYP claim is
“co-pilot over stamped KB,” not “the TA is optional.”

---

### Professor — gate, insights, “their” models

**What it is:** stamp / unstamp KB; review insights from Quiet asks + Rooms;
Canvas sync; command-center clusters; FAQ-from-cluster / from-insight;
optional gold-label POST (API only — no unified-app form).

| Upgrade | Why |
| --- | --- |
| Default ingest to `pending_review` | Conflicts with the sold gate. Launch sync, professor Sync, paste, and file upload all auto-approve today. Keep a demo checkbox if you want one-click demos; off-demo must stamp. |
| Surface hit-rate + refuse count on the professor home | Makes the gate visible: “students asked the agent 40 times; 11 hit a stamp.” Endpoint exists. |
| In-app “download this course’s training slice” | `export_analyzer_training_data.py` exists; professors will not run it. A CSV button is enough for FYP. No need for in-app retrain. |
| Gold-label button on a resolved ask | `POST /analytics/gold-labels` is unused in the unified UI. One TA click (“Analyzer was wrong / Matcher was wrong”) is the only number a supervisor should trust. |
| Expertise tags per **course membership**, not `ta_roster` name join | Matcher joins TAs by `display_name` string. A renamed account or two “Sara”s breaks assignment and load counts. |

The professor is the only party who can make the student agent smarter. Every
AI upgrade that is not “more stamps + real gold labels” is theater.

---

## P1 — models & data (quality, not theater)

From [`agent_performance.md`](agent_performance.md), still true:

1. **Gold set is small / seeded** (n=80 public-OH inspired). Real TA
   `human_gold` when a lab exists — the only number a supervisor should trust.
2. **Matcher silver holdout (~87%)** is self-consistency, not gold.
3. **Analyzer CV (~85%, n=156)** is synthetic / curated. Topic overlays paper
   over CSC demos.
4. **Teaching bank** is a global CSV (base + CSC + multi-dept). Synthesizer
   falls through to the bank when that course’s KB is empty — a COM student can
   get a hashing script if embeddings drift. **Filter bank by department** or
   disable the bank when any approved KB hit exists (Help Coach refresh already
   prefers KB).
5. **No online learning.** Retrain is a script. That is fine; say so.
6. **Clustering** defaults to MiniLM; tests use lexical. Production without the
   model download behaves worse than you demoed if someone forgets the venv
   weight files.

Highest-leverage AI work, in order:

1. Pending-not-auto-approve on Canvas ingest + professor buttons.  
2. Auth on `/agent/ask`, `PATCH /knowledge`, `/requests`, analytics.  
3. Force `course_id` on Study Agent **and** Synthesizer neighbor search.  
4. Matcher: real course TAs only; heuristic for unseen names.  
5. Live Canvas PDF / DOCX through `material_extract`.  
6. Ten real TA gold labels from one AUI section beat another CSV.

---

## P1 — product (non-AI) still worth doing

- Microsoft + LTI credentials (IT). Local wiring was tested; Sophia’s real
  login was not (placeholder client → AADSTS700038).
- Favicon + Open Graph.
- `oracle_*` in API / UI vs “Ask Triage” in copy — rename for literacy or live
  with it and say so in defense.
- Unified app has **no frontend tests**. Backend carries the product.
- Legacy kiosk / professor-dashboard / ta-dashboard still run CI. They are not
  the product. Either mark them archival in CI or stop implying three apps.
- Student “Look up request code” is a kiosk leftover. Fine for Quiet ask;
  identified students should see **their** queue without typing an id.
- `AGENTS.md` still describes a Three.js guest landing.

---

## P2 — hygiene

- Historical `oracle_service.py` / `oracle_agents.png` filenames.
- Legacy Claude modules only behind a flag — keep them out of the default path
  (already).
- No Python linter in `requirements.txt`.
- React Router engine warning (wants Node ≥ 22.22; CI is 22).
- Study-buddy exists and is wired; confirm it stays in the demo script.
- `product_overview.md` still mentions the Three.js guest path in the
  supervisor checklist.

---

## Suggested order if you only do five things

**Shipped 30 Aug 2026** (this branch):

1. Auth + course membership on stamps, asks, analytics, `/from-cluster`, `/actions`.  
2. Canvas / paste / upload / LTI launch ingest → `pending_review` until stamp.  
3. Matcher uses real course TAs only (heuristic load-balance; no demo-name
   classifier on a scoped roster).  
4. Live Canvas file sync extracts PDF / DOCX; Synthesizer RAG stays in-course
   and filters the teaching bank by department.  
5. Alice Chen demo-TA pass: 20 `human_gold` rows in
   `data/gold_labels/ta_alice_pass.csv`, seeded on demo login, plus a Gold
   label control on the TA workspace.

That is the AI upgrade path for all three parties. Remaining items are hosting,
IT, or polish.
