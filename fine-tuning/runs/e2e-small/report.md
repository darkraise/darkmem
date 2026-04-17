# Fine-tuned Pipeline Evaluation

Date: 2026-04-17 07:52:58
Corpus: fine-tuning test split (2000 examples)
Pipeline: fine-tuned GLiNER (entities) + fine-tuned REBEL (relationships)

## Results

| Metric | Value |
|---|---|
| Entity F1 | **0.727** |
| Entity Precision | 0.791 |
| Entity Recall | 0.673 |
| Type Accuracy | 0.756 |
| **Relationship F1** | **0.349** |
| Relationship Precision | 0.327 |
| Relationship Recall | 0.374 |
| Direction Rate | 0.995 |
| GLiNER latency | 13 ms |
| REBEL latency | 200 ms |
| Total latency | 213 ms |

## Comparison vs zero-shot best

| Metric | Zero-shot best | Fine-tuned | Delta |
|---|---|---|---|
| Entity F1 | 0.904 | 0.727 | -0.177 |
| Type Accuracy | 0.901 | 0.756 | -0.145 |
| Rel F1 | 0.654 | 0.349 | -0.305 |
| Latency | 1800 ms | 213 ms | -1587 ms |
