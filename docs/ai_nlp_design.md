# AI / NLP Design (Custom-Trained Ask Triage)

Product vocabulary: [`glossary.md`](glossary.md). Training inventory:
[`training_data.md`](training_data.md). Performance backlog:
[`agent_performance.md`](agent_performance.md).

> **Naming:** docs and UI say **Ask Triage**. The intake module is still
> `backend/app/services/oracle_service.py` and many columns/API fields use the
> historical `oracle_*` prefix — same pipeline.

## FYP constraint

The assessed runtime path uses **custom-trained local models only**.
Prompted Claude calls and `USE_MOCK_CLAUDE` mocks are disabled by default
(`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`).

## Ask Triage pipeline

On every `POST /requests/`:

1. **Analyzer** — fine-tuned embedding + logistic regression classifier  
   Artifact: `backend/models/request_classifier.joblib`
2. **Matcher** — fine-tuned TA assignment classifier + queue penalty  
   Artifact: `backend/models/matcher_classifier.joblib`
3. **Synthesizer** — RAG over teaching bank / approved KB + style ranker  
   Artifact: `backend/models/synthesizer_ranker.joblib`

Plus supporting pieces:

- **Learning-style classifier** — `learning_style_classifier.joblib`
- **Clustering** — sentence-transformer embeddings + cosine similarity (`cluster_id`)
- **Summarizer** — TF-IDF keywords for action-plan titles
- **Help Coach** — separate mid-session TA surface (`help_coach_service.py`);
  same local RAG / teaching-bank stack, not a fourth intake joblib

Details: [`training_data.md`](training_data.md) · diagrams: `diagrams/oracle_agents.png`
(Ask Triage agent cards; filename is historical).

## Help Coach (not Ask Triage)

`POST /ta/assist/` runs **after** escalation, while a TA is helping:

| Mode | Purpose |
| --- | --- |
| `draft_reply` | Suggest a written reply for `message` help mode |
| `socratic` | Step-by-step prompts for face-to-face teaching |
| `refresh_teaching` | Refresh the teaching script from KB / similar opens |
| `rewrite_reply` | Tone/clarity rewrite of a draft |

Help Coach does not replace Ask Triage and does not publish to the Study Agent.
Professor KB approval remains the gate for `/agent/ask`.

## Models / libraries

- `sentence-transformers` (`all-MiniLM-L6-v2`) for embeddings
- `scikit-learn` `LogisticRegression` for Analyzer / Matcher / style ranker
- Local CSV teaching bank for Synthesizer / Help Coach RAG (no generative LLM required)

## Clustering

New requests get a `cluster_id` by embedding similarity against existing requests.
Threshold: `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` (default `0.72`).
Tests use `OFFICEHOURS_CLUSTERING_BACKEND=lexical` to avoid model downloads.
Repeated clusters can become **shared group meetings** (title / when / place on
every linked request status).

## Recommendation heuristics (professor cards)

| Condition | Suggested action |
| --- | --- |
| Large conceptual cluster | Group review session |
| Single factual/logistics | Quick FAQ |
| Procedural cluster | TA-led review |
| Grading / retake / integrity | Admin route |
| Urgent / emotional | Priority 1:1 |

Ask Triage Matcher assignment is separate from these professor recommendation cards:
Matcher picks a TA for the live queue; recommendation cards help the professor
plan office-hours agenda blocks (and optional group meetings).

## Train / refresh

```bash
cd backend
python3 scripts/train_classifier.py
python3 scripts/train_matcher.py
python3 scripts/train_synthesizer.py
python3 scripts/train_learning_style.py
```

Professor-approved KB exports can later expand Analyzer training via
`scripts/export_analyzer_training_data.py`.
