# AI / NLP Design (Custom-Trained Oracle)

## FYP constraint

The assessed runtime path uses **custom-trained local models only**.
Prompted Claude calls and `USE_MOCK_CLAUDE` mocks are disabled by default
(`OFFICEHOURS_ALLOW_EXTERNAL_LLM=false`).

## Oracle pipeline

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

Details: [`training_data.md`](training_data.md) · diagrams: `diagrams/oracle_agents.png`

## Models / libraries

- `sentence-transformers` (`all-MiniLM-L6-v2`) for embeddings
- `scikit-learn` `LogisticRegression` for Analyzer / Matcher / style ranker
- Local CSV teaching bank for Synthesizer RAG (no generative LLM required)

## Clustering

New requests get a `cluster_id` by embedding similarity against existing requests.
Threshold: `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` (default `0.72`).
Tests use `OFFICEHOURS_CLUSTERING_BACKEND=lexical` to avoid model downloads.

## Recommendation heuristics (professor cards)

| Condition | Suggested action |
| --- | --- |
| Large conceptual cluster | Group review session |
| Single factual/logistics | Quick FAQ |
| Procedural cluster | TA-led review |
| Grading / retake / integrity | Admin route |
| Urgent / emotional | Priority 1:1 |

Oracle Matcher assignment is separate from these professor recommendation cards:
Matcher picks a TA for the live queue; recommendation cards help the professor
plan office-hours agenda blocks.

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
