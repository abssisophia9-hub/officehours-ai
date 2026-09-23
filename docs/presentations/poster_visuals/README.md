# Poster visuals

**Used in the SSE poster dashed boxes.** Each PNG is sized to that cell’s
official `hRule=exact` content area so labels cannot clip:

| File | Template slot | Cell height | Figure |
| --- | --- | --- | --- |
| `SLOT_gap.png` | OPTIONAL VISUAL | 1.15in | Today vs OfficeHours comparison table |
| `SLOT_architecture.png` | PROPOSED DESIGN FIGURE | 2.55in | App → FastAPI → Canvas + Analyzer/Matcher/Synthesizer/stamp |
| `SLOT_pipeline.png` | PROPOSED PROCESS / PIPELINE | 2.29in | Ask → triage → TA/stamp → Study Agent |
| `SLOT_roadmap.png` | PLANNED WORK / REQUIREMENTS VISUAL | 0.70in | Phases 1–5 banner (this cell is short by design) |
| `SLOT_evaluation.png` | PLANNED EVALUATION FRAMEWORK | 2.33in | Method / evidence / pass-rule matrix |

Rebuild poster (figures + official template fill):

```bash
backend/venv/bin/python docs/presentations/build_capstone_poster.py
```

Larger print-size extras (V01–V16) stay in this folder for a backboard. Text on the SSE poster supports the slot figures — it does not replace them.

| File | Slot on the SSE template |
| --- | --- |
| `V01_architecture.png` | **PROPOSED DESIGN FIGURE** |
| `V02_ask_triage_agents.png` | Optional extra / backboard |
| `V03_pipeline.png` | **PROPOSED PROCESS / PIPELINE** |
| `V04_gap_map.png` | **OPTIONAL VISUAL** (gap map) |
| `V05_roles.png` | Optional extra next to Problem / Stakeholders |
| `V06_stamp_gate.png` | Optional extra next to Ethics / Study Agent |
| `V07_roadmap.png` | **PLANNED WORK / REQUIREMENTS VISUAL** |
| `V08_evaluation.png` | **PLANNED EVALUATION FRAMEWORK** |
| `V09_demo_vs_live.png` | Optional extra next to Feasibility |
| `V10_qr.png` / `V10_qr_square.png` | **Replace with QR** |
| `V11`–`V16` | Full repo diagrams if a judge wants more detail |

Open [`index.html`](index.html) to review every figure.

Rebuild:

```bash
backend/venv/bin/python docs/presentations/poster_visuals/build_visuals.py
```
