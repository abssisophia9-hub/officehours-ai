# AI / NLP Design

## Pipeline Overview
1. **Preprocessing** — clean and normalize incoming request text
2. **Classification** — categorize request into types (e.g., conceptual question, logistics/admin, retake request, emotional/stress-related, grading dispute)
3. **Embedding generation** — use sentence-transformers to embed request text
4. **Clustering** — group semantically similar requests using cosine similarity (and/or k-means / HDBSCAN for batch clustering)
5. **Recommendation** — map cluster size + category + urgency to a recommended action

## Models / Libraries
- `sentence-transformers` (e.g., `all-MiniLM-L6-v2`) for embeddings
- `scikit-learn` for clustering and baseline classifiers
- Optional: LLM API call for harder classification cases or generating FAQ-style responses

## Clustering MVP
New requests are assigned a `cluster_id` at creation time. The clustering layer
embeds the incoming request with `sentence-transformers`, compares it to
existing requests using cosine similarity, and reuses the closest cluster when
similarity is above the configured threshold. Otherwise, it starts the next
cluster ID.

Configuration:

- `OFFICEHOURS_EMBEDDING_MODEL` — defaults to `all-MiniLM-L6-v2`
- `OFFICEHOURS_CLUSTER_SIMILARITY_THRESHOLD` — defaults to `0.72`
- `OFFICEHOURS_CLUSTERING_BACKEND=lexical` — deterministic lightweight backend
  for tests/dev environments where downloading the embedding model is not wanted

## Data Fixtures
- `data/synthetic_requests.csv` contains raw synthetic finals-week student requests for local demos.
- `data/labeled_requests.csv` mirrors those request IDs with `category` and `urgency` labels for baseline classification experiments.
- `data/demo_scenarios.csv` describes expected cluster/action outcomes for demo validation and future recommendation tests.

The current fixture set is synthetic only; do not treat it as real student data.

## Recommendation Logic (initial heuristic)
| Condition | Recommended Action |
|---|---|
| Cluster size ≥ N, conceptual question | Group review session |
| Single occurrence, simple/factual | Quick FAQ response |
| Cluster size ≥ N, procedural | TA-led review session |
| Grading dispute / retake | Admin/retake route |
| Flagged as urgent/emotional | One-to-one meeting (priority) |

This heuristic will be refined using labeled data in `data/labeled_requests.csv` and tested in `notebooks/ai_classification_tests.ipynb`.
