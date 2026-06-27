# Evaluation Plan

## Research Question
Can an AI-assisted office-hours triage system reduce faculty communication overload and improve student comfort in seeking academic help during final exam periods?

## Evaluation Methods

### 1. Technical Evaluation
- Classification accuracy on labeled dataset (`data/labeled_requests.csv`)
- Clustering quality (silhouette score, manual inspection of clusters)
- Latency of end-to-end request → recommendation pipeline

### 2. User Evaluation
- Simulated finals-week demo scenario (`demo/demo_script.md`)
- Survey for student comfort/anonymity perception
- Survey for faculty perceived workload reduction

### 3. Metrics
| Metric | Target |
|---|---|
| Classification accuracy | ≥ 80% on labeled test set |
| Avg. requests per cluster (during simulated peak) | Reduction vs. unclustered baseline |
| Student comfort survey score | Qualitative + Likert scale |
| Faculty time-to-triage | Reduction vs. manual baseline |

## Reporting
Results will be documented in `reports/mid_report` and `reports/final_report`, with supporting analysis in `notebooks/`.
