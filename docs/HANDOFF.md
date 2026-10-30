# Handoff

Checked at `26c1095` on `main` (merge of PR #121). `docs/ORCHESTRATION.md` and `docs/midreport/EVIDENCE.md`, `GAPS.md`, and `CONSISTENCY.md` are **not in repo**. This page uses `docs/prompt_log.md`, `git log --oneline -40`, and the docs and code those leave you in.

## What this is

OfficeHours AI is a multi-role campus app for office-hours triage at Al Akhawayn University: one login, role per course, Ask Triage at intake, Help Coach for TAs, and a Study Agent that quotes only professor-approved material. The docs call that classifiers + retrieval + a professor gate. `main` matches `origin/main` at `26c1095` (“Merge pull request #121”, `cursor/study-conversations-a8bd`).

## Architecture the repo shows

UI is `frontend/officehours-app` (port 5180); API is FastAPI (port 8000). CI builds those two. Legacy kiosk and dashboard folders are archives. Role is a `course_memberships` row, not the email. A TA is staff on a course they already took. Ask Triage is `ask_triage_service.py` (`triage_*`). Help Coach is `POST /ta/assist/`. Study Agent is `POST /agent/ask`. `agent_policy.py` allows one checker call, no tool loop, cutoff 0.42; below that, a staff form and no model call. Later docs name Canvas LTI 1.3 for community enrollment, and `lti13.py` says the launch JWT is verified. `OFFICEHOURS_DEMO=true` seeds local accounts and the unsigned Canvas mirror. Default DB is SQLite (`DATABASE_URL` for Postgres). Rooms stay on `/help-room/`.

## Done, in progress, open

**Done.** `docs/prompt_log.md` logs PRs #99–#107 only. The last 40 commits merge #108–#118 and #120–#121: professor pages, the ask flow, Rooms, the Gemini checker, the one-call policy, Diary 2 (`reports/diary2/EGR4402_Diary2_Sophia_Abssi.pdf`), the citation line, and conversations beside the chat. Pull request #119 is not in `git log`.

**In progress:** not in repo.

**Open, as the docs name it:** prompt-log narrative fields stay `TODO` through #107; do not invent prompts. Microsoft and Canvas campus credentials are not in the repo. A real-section gold lab is the next evidence (`docs/fyp_evidence.md`). A community host still needs `OFFICEHOURS_DEMO=false` and a real `VITE_API_BASE`.

## Conventions

Say Ask Triage, `triage_*`, Help Coach, Study Agent, Rooms, Quiet ask. `diagrams/oracle_agents.png` is a historical filename. Tests: from `backend/`, `venv/bin/python -m pytest`, `DATABASE_URL=sqlite:///:memory:`, `OFFICEHOURS_CLUSTERING_BACKEND=lexical`. `docs/fyp_evidence.md` says 162 pytest cases; `def test_` under `backend/tests` here is 265. `docs/repo_audit.md` says the product app has no frontend tests. `scripts/run_product.sh` defaults demo on and clustering to lexical; the app otherwise defaults to sentence-transformers. `OFFICEHOURS_ALLOW_EXTERNAL_LLM` stays false unless demo mode and a chosen provider are both armed. `OFFICEHOURS_LLM_ENABLED` defaults to false; the helper turns it on only when that call is already armed. A key alone stays retrieval-only. Gemini also needs `OFFICEHOURS_GEMINI_FREE_TIER_ACK`. `OFFICEHOURS_RATE_LIMIT=false` does not disable the study-agent budgets.

## Traps

`docs/system_architecture.md` still says “LTI signatures still TODO.” `lti13.py` and `docs/defense_crib.md` say the code verifies launches and the campus keys are absent. `docs/repo_audit.md` (30 Aug 2026) keeps an older “auto-approve today” paragraph above a later “Shipped” list; use the shipped list. “A TA is still a student” in `docs/project_journey.md` means a different course. The crib forbids calling a TA a classmate in the section they staff, and it says the live Matcher is a heuristic, not `matcher_classifier.joblib`. Do not cite Analyzer CV, Matcher silver, or seed gold as campus quality. `scripts/run_study_eval.py --with-check` turns the kill switch on for that process. This handoff did not re-run that evaluation.
