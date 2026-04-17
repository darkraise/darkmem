# Fine-tuned Pipeline Evaluation

Date: 2026-04-17 08:01:57
Corpus: fine-tuning test split (2000 examples)
Pipeline: fine-tuned GLiNER (entities) + fine-tuned REBEL (relationships)

## Results

| Metric | Value |
|---|---|
| Entity F1 | **0.739** |
| Entity Precision | 0.662 |
| Entity Recall | 0.837 |
| Type Accuracy | 0.789 |
| **Relationship F1** | **0.363** |
| Relationship Precision | 0.329 |
| Relationship Recall | 0.405 |
| Direction Rate | 0.996 |
| GLiNER latency | 32 ms |
| REBEL latency | 232 ms |
| Total latency | 264 ms |

## Comparison vs zero-shot best

| Metric | Zero-shot best | Fine-tuned | Delta |
|---|---|---|---|
| Entity F1 | 0.904 | 0.739 | -0.165 |
| Type Accuracy | 0.901 | 0.789 | -0.112 |
| Rel F1 | 0.654 | 0.363 | -0.291 |
| Latency | 1800 ms | 264 ms | -1536 ms |
