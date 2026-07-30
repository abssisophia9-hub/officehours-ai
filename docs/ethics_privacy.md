# Ethics & Privacy Considerations

## Core Principles
- **Student anonymity by default** — students may submit requests without identifying themselves
- **Opt-in identification** — only when a student wants a direct follow-up (e.g., 1:1 meeting) do they provide identifying info
- **Professor stays in control** — AI recommends, never auto-executes actions like scheduling or grade changes
- **Data minimization** — store only what's needed for triage; avoid retaining raw NFC/QR identifiers beyond session scope

## Risks
- Misclassification leading to a student's urgent request being deprioritized
- Sensitive content (e.g., mental health disclosures) being mishandled
- Bias in AI classification across different phrasing/language styles

## Mitigations
- Human-in-the-loop: professors approve what enters the **Study Agent** knowledge
  base; AI does not auto-schedule grades or publish unapproved FAQ answers
- TA **Reply** can reach the student on request status before KB approval
  (message help mode) — that is intentional async help, separate from Study Agent
- Clear escalation path for flagged urgent/sensitive content
- Regular review of classification accuracy across diverse phrasing (see `docs/evaluation_plan.md`)

## Data Retention
- Synthetic/demo data only during development (see `data/`)
- Real deployment would require institutional IRB/ethics review before collecting actual student data
