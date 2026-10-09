# Agent performance — analysis & upgrade plan

Status after multi-department metrics work. Use this as the backlog for making
**Ask Triage** (Analyzer / Matcher / Synthesizer), **Help Coach**, and the
**Study Agent** **actually better**, not just louder.

Vocabulary: [`glossary.md`](glossary.md). Design: [`ai_nlp_design.md`](ai_nlp_design.md).

**Scope:** the platform serves **any AUI course** (MTH, COM, ECO, ENG, CSC, …).
CSC supplements are demo enrichment for SSE walkthroughs — not the product boundary.

## What runs today (FYP path)

```
POST /requests                    # Ask Triage (ask_triage_service.py)
  → classify_and_recommend (ML category + learning-style ML by default)
  → Analyzer (embedding LogReg + topic overlays)
  → Matcher (embedding LogReg + expertise/queue blend on DEFAULT_TA_ROSTER)
  → Synthesizer (approved KB RAG → teaching bank → seek-help)
  → pending KB draft (professor gate)
POST /ta/assist/                  # Help Coach (while TA helping; same RAG stack)
POST /agent/ask                   # Study Agent
  → approved KB only; weak/no match → should_seek_help (Quiet ask)
  → logged to kb_ask_events for per-course hit-rate
```

No prompted Claude on the default path. Models live in `backend/models/*.joblib`.

## How to measure performance

| Signal | Command / endpoint | Notes |
| --- | --- | --- |
| Analyzer CV | `scripts/train_classifier.py` → `reports/final_report/classifier_evaluation.*` | Includes multi-dept + CSC CSVs |
| Matcher holdout | `scripts/train_matcher.py` → `matcher_evaluation.json` | Silver labels — not gold |
| **Human gold** | `scripts/evaluate_gold_labels.py` → `gold_label_evaluation.json` | Real quality bar |
| Submit gold | `POST /analytics/gold-labels` | Stored in DB; `--include-db` on eval |
| **KB hit-rate** | `GET /analytics/kb-hit-rate` | Per-course hits vs seek-help |
| Golden smoke | `tests/test_agent_quality.py` | CSC + multi-dept behavior locks |
| Human surveys | `docs/surveys/` | Optional / legacy pilot only — not a capstone gate |

```bash
# Gold-label evaluation (from backend/)
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
  venv/bin/python scripts/evaluate_gold_labels.py

# Optional: include API-submitted labels
OFFICEHOURS_CLUSTERING_BACKEND=lexical \
  venv/bin/python scripts/evaluate_gold_labels.py --include-db
```

Grow gold labels: `data/gold_labels/README.md`.

## Bottlenecks (ranked)

1. **Gold set is still small / seeded** — replace `human_gold_seed` with real TA judgments.
2. **Matcher silver labels** — holdout self-consistency ≠ gold agreement.
3. **KB coverage varies by course** — hit-rate is the honest ceiling for `/agent/ask`.
4. **Teaching bank** — base + CSC + multi-dept; still needs professor-approved KB per course.
5. **Quality CI** — CV + gold script + smoke tests; not live online learning.

## Training data (campus-wide)

| File | Role |
| --- | --- |
| `labeled_requests*.csv` | Analyzer base finals-week labels |
| `labeled_requests_csc.csv` | SSE topic supplement |
| `labeled_requests_multidept.csv` | **MTH / COM / ECO / ENG / GEN** |
| `matcher_training*.csv` (+ csc + multidept) | Matcher silver labels |
| `synthesizer_teaching_bank*.csv` (+ csc + multidept) | Teaching-bank RAG |
| `gold_labels/gold_labels.csv` | Human evaluation set |

## Retrain (from `backend/`)

```bash
venv/bin/python scripts/train_classifier.py
venv/bin/python scripts/train_matcher.py
venv/bin/python scripts/train_synthesizer.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/train_learning_style.py
OFFICEHOURS_CLUSTERING_BACKEND=lexical venv/bin/python scripts/evaluate_gold_labels.py
```

## Next

| Priority | Action | How we know it worked |
| --- | --- | --- |
| P0 | Collect ≥40 real TA gold labels across departments | Gold accuracy/F1 in report; errors sampled |
| P0 | Watch `GET /analytics/kb-hit-rate` per course after Canvas sync | Hit-rate rises when materials are approved |
| P1 | Retrain after adding department-specific labeled asks | CV + gold both move (not just silver holdout) |
| P2 | Preference ratings on synthesizer hints (`gold_hint_useful`) | Win-rate vs template baseline |
| P3 | Course-conditioned retrieval index | Latency + isolation metrics |

## Honest ceiling

More prompt-like copy will not move accuracy. Gains come from **multi-department
labeled text**, **gold TA judgments**, and **approved course KB**. Empty KB
correctly steers to Quiet ask — that is a feature, not a bug.
