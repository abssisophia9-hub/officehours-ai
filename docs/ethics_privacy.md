# Ethics & Privacy Considerations

## Core Principles
- **Student anonymity by default** — students may submit requests without identifying themselves
- **Opt-in identification** — only when a student wants a direct follow-up (e.g., 1:1 meeting) do they provide identifying info
- **Professor stays in control of published answers** — Study Agent only reads **approved** KB; AI does not auto-change grades or publish FAQ without review
- **Data minimization** — store only what's needed for triage; student ID is
  optional and only kept when the student chooses identified submission
- **Stuck Room is classmates, not staff surveillance** — professors see
  aggregated chapter/topic insights, not a live student chat; grades/integrity/
  crises are blocked from the room and sent to Quiet ask

## Risks
- Misclassification leading to a student's urgent request being deprioritized
- Sensitive content (e.g., mental health disclosures) being mishandled
- Bias in AI classification across different phrasing/language styles
- Unsigned Canvas launch simulator allowing identity impersonation in demos

## Mitigations
- Human-in-the-loop: professors approve what enters the **Study Agent** knowledge
  base; AI does not auto-schedule grades or publish unapproved FAQ answers
- TA **Reply** can reach the student on request status before KB approval
  (message help mode) — intentional async help, separate from Study Agent publication
- Clear escalation path for flagged urgent/sensitive content
- Regular review of classification accuracy (`docs/evaluation_plan.md`, gold labels)
- Label Canvas launch as **demo-only / unsigned**; optional
  `OFFICEHOURS_CANVAS_LAUNCH_SECRET`; production path is Canvas LTI 1.3
- Document open local-demo list endpoints as not campus-hardened
  (`docs/fyp_evidence.md`)

## Data Retention
- Synthetic/demo data only during development (see `data/`)
- Real deployment would require institutional IRB/ethics review before collecting actual student data
- Training CSVs must not contain scraped private student emails or real transcripts
