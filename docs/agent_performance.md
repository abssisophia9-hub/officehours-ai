# Agent performance — analysis & upgrade plan

Status after AUI demo conformance work. Use this as the backlog for making
Analyzer / Matcher / Synthesizer / KB agent **actually better**, not just louder.

## What runs today (FYP path)

```
POST /requests
  → classify_and_recommend (ML category + learning-style ML by default)
  → Analyzer (embedding LogReg + topic overlays)
  → Matcher (embedding LogReg + expertise/queue blend on DEFAULT_TA_ROSTER)
  → Synthesizer (approved KB RAG → CSC/base teaching bank → seek-help)
  → pending KB draft (professor gate)
POST /agent/ask
  → approved KB only; weak/no match → should_seek_help (Quiet ask)
```

No prompted Claude on the default path. Models live in `backend/models/*.joblib`.

## Bottlenecks (ranked)

1. **Training text does not match demos** — older fixtures lean finals-week triage;
   demos need CSC 2302 hashing/RB-trees, CSC 3351 scheduling, CSC 3374 RPC.
2. **Matcher labels are silver** — expertise heuristics, not TA gold judgments;
   Bob is under-represented; holdout ~96% is self-consistency.
3. **Teaching bank was templated** — same hints reused across categories;
   CSC supplement rows now exist (`data/synthesizer_teaching_bank_csc.csv`).
4. **KB quality = professor content** — agent cannot invent; empty course KB
   correctly steers to Quiet ask.
5. **Almost no quality CI** beyond Analyzer CV + smoke tests.

## Done in this pass

- Align `DEFAULT_TA_ROSTER` with `data/ta_roster_seed.csv` (incl. category tags);
  roster refresh on startup.
- Default `OFFICEHOURS_LEARNING_STYLE_BACKEND=ml`.
- CSC topic labeled sets for Analyzer + Matcher; CSC teaching-bank supplement.
- `train_classifier.py` loads CSC + optional `analyzer_training_export.csv`.
- `train_matcher.py` loads CSC supplement and writes `reports/final_report/matcher_evaluation.json`.
- Frontend CI audits fixed (postcss; product app → `react-router@8.3.0`).

## Next (needs retrain / data)

| Priority | Action | How we know it worked |
| --- | --- | --- |
| P0 | Retrain Analyzer + Matcher + Synthesizer with new CSC rows | CV/holdout reports + golden tests green |
| P1 | Collect gold Matcher labels from TAs (even 40) | Holdout on gold set, not silver |
| P1 | Grow approved KB per course from Canvas sync | `/agent/ask` hit-rate on real module questions |
| P2 | Joint urgency head or second classifier | Confusion matrix on urgent/sensitive |
| P2 | Human ratings of synthesizer hints | Preference win-rate vs template baseline |
| P3 | Course-conditioned retrieval index | Latency + isolation metrics |

## Retrain (from `backend/`)

```bash
venv/bin/python scripts/train_classifier.py
venv/bin/python scripts/train_matcher.py
venv/bin/python scripts/train_synthesizer.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_learning_style.py
```

## Honest ceiling

More prompt-like copy will not move accuracy. Gains come from **topic-covered labels**,
**non-templated teaching/KB content**, and **gold Matcher feedback**. The seek-help
path is intentional: when materials are empty, human office hours beat hallucinated help.
