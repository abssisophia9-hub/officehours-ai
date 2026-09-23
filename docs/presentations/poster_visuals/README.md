# Poster visuals

**Used in the SSE poster dashed boxes.** Matplotlib figures, sized to each
cell’s official `hRule=exact` content area:

| File | Template slot | Figure |
| --- | --- | --- |
| `SLOT_gap.png` | OPTIONAL VISUAL | Capability presence matrix (LMS / Piazza / chatbot vs OfficeHours) |
| `SLOT_architecture.png` | PROPOSED DESIGN FIGURE | C4-style container diagram |
| `SLOT_pipeline.png` | PROPOSED PROCESS / PIPELINE | Input → process → output flowchart |
| `SLOT_roadmap.png` | PLANNED WORK / REQUIREMENTS VISUAL | Milestone stem plot (demo built vs waiting on IT) |
| `SLOT_evaluation.png` | PLANNED EVALUATION FRAMEWORK | Accuracy bars + per-class F1 from `reports/final_report/` |

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
