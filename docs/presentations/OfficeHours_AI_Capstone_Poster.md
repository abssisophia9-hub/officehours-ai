# OfficeHours AI — Capstone Poster (text mirror)

**Open in Cursor:** [`OfficeHours_AI_Capstone_Poster.html`](OfficeHours_AI_Capstone_Poster.html) (readable preview — `.docx` shows “Binary file is not supported” in the IDE).

**Print / Word:** [`OfficeHours_AI_Capstone_Poster.docx`](OfficeHours_AI_Capstone_Poster.docx) · **PDF:** [`OfficeHours_AI_Capstone_Poster.pdf`](OfficeHours_AI_Capstone_Poster.pdf) · **Plain extract:** [`OfficeHours_AI_Capstone_Poster_content.txt`](OfficeHours_AI_Capstone_Poster_content.txt)

**Title:** OfficeHours AI: Multi-Role Campus Office-Hours Triage with Local NLP and Canvas Integration

**Student:** Sophia Abssi | **Degree:** B.Sc. Computer Science (SSE) | **Type:** Software Development

**Supervisor:** TBD (Capstone Supervisor) | **Client path:** AUI Canvas LMS | **Stage:** Working Prototype → Live aim | **Date:** Sep 2026

**Before print:** replace supervisor name; add QR (repo/demo); enlarge architecture figure if needed.

---

## Project Overview
Finals-week support overload and student hesitation create repeated, urgent asks across email and Canvas. OfficeHours AI is a unified multi-role campus app that triages asks, staffs TAs, and lets professors stamp Study Agent answers. Contribution: gated local-NLP triage designed for Canvas-first deployment—not an unconstrained chatbot.

- **Context:** AUI courses; students, TAs, professors during peak academic support demand.
- **Proposed idea:** React SPA + FastAPI with Ask Triage, Help Coach, stamped Study Agent, Rooms, and Canvas LTI/materials sync.
- **Expected contribution:** Course-scoped triage, dual-TA staffing, KB approval gate, and a demo→live Canvas path.

## Problem Definition & Relevance
- **Problem:** How can campus office hours cut repeat load and lower ask barriers while keeping professors in control of AI answers?
- **Stakeholders:** Students (Quiet asks, Study Agent, Strategist, Rooms); TAs (Live Queue, Help Coach); Professors (Repeated Topics, KB stamp, Canvas sync).
- **Constraints:** Synthetic/silver FYP labels; local ML by default; live Canvas needs IT credentials + HTTPS. No portal scraping; no unconstrained LLM backend.

## Related Work, Gap & Innovation
- **Alternatives:** LMS inboxes; Piazza/Ed; tutoring chatbots; FAQ bots without professor gates or dual-TA matching.
- **Gap:** Missing Quiet escalation + local triage ML + dual-TA staffing + professor stamp before student-facing AI.
- **Innovation:** Ask Triage + Help Coach + stamped Study Agent in one app; Canvas LTI; trackable Quiet asks.

## Objectives & Success Criteria
1. Triage & route asks → usable demo triage; cite holdout metrics carefully  
2. Keep Study Agent professor-gated → 0 unauthorized quotes from pending KB  
3. Canvas-first deploy path → live checklist on one AUI test course  

## Proposed System / Design
- Unified React SPA; FastAPI (requests/ta/knowledge/lti); SQLite→Postgres; WebSocket hub; Quiet-ask privacy.
- Ask Triage = MiniLM embeddings + LogisticRegression + RAG (joblibs). Help Coach = TA assist. Study Agent = approved KB only.
- Revision Strategist = client-side planner until live Canvas grades.

**Pipeline:** Ask → Analyzer/Matcher/Synthesizer → TA queue/Help Coach → Professor stamp → Study Agent

**Figure:** `diagrams/architecture.png`

## Requirements & Work Plan
1. Core triage+roles  
2. TA/Help Coach+KB gate  
3. Rooms+Canvas demo  
4. LTI+live sync  
5. Strategist grades + Postgres host  

**Dependencies:** Canvas LTI key + API token; optional Entra; public HTTPS.

## Methodology / Tech
- Iterative prototyping + CI  
- FastAPI, React/Vite/Tailwind, SQLAlchemy, sentence-transformers, scikit-learn, WebSockets, Canvas LTI 1.3 + REST  
- GitHub, docs/, train scripts, reports/

## Evaluation
pytest + holdouts + gold-label TA lab + role walkthroughs + live Canvas checklist

## Feasibility & Risks
- Risk: IT delay on LTI/API/Entra; Strategist grades blocked until token  
- Mitigation: demo mirror for showcase; staged live; Postgres at go-live  

## Ethics / Responsible AI
Quiet asks; auth + CORS; professor stamp; external LLM off by default; refuse weak KB

## Expected Impact
Safer faculty-controlled AI help for campus office hours; transferable to other LMS schools.  
**Limits:** Not SIS replacement; not live grade Strategist yet; not multilingual ChatGPT tutoring.

## Key References
[1] AUI finals-week office-hours need. [2] Piazza/Ed-style Q&A. [3] Canvas LTI 1.3; MiniLM; scikit-learn.
