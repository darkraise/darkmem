# Classification v2 Leaderboard

Date: 2026-04-15
Training data: `data/classification/train_v2.jsonl` (10,000 rows — 7,000 shared base + 3,000 classification top-up, v2 7-label taxonomy)
Eval: `docs/e2e/scripts/classification_eval/corpus/gold_v2.jsonl` (195 rows, balanced 27–28 per class, 46 easy / 71 medium / 78 hard)

## Headline

| Rank | Model | Size | Accuracy | Macro F1 | `reference` recall |
|---|---|---:|---:|---:|---:|
| 1 | ModernBERT-base | 150M | **0.928** | **0.929** | 0.964 |
| 2 | RoBERTa-base | 125M | 0.897 | 0.900 | 0.964 |
| 3 | DistilBERT-base | 67M | 0.800 | 0.803 | 0.964 |
| 4 | MiniLM-L12-H384 | 33M | 0.764 | 0.765 | 0.893 |

For reference, the 2026-04-14 benchmark on the v1 gold set (12 labels, 195 rows) reported qwen3.5:4b (≈4B params) as the winner at accuracy 0.817. All four v2 fine-tuned encoders beat that number despite being 27× to 120× smaller, on a balanced 7-label eval with the same 195-row support.

## Per-class F1 (gold_v2)

| Class | ModernBERT | RoBERTa | DistilBERT | MiniLM |
|---|---:|---:|---:|---:|
| architecture | 0.982 | 0.933 | 0.875 | 0.831 |
| decision | 0.889 | 0.889 | 0.786 | 0.800 |
| fact | 0.852 | 0.800 | 0.638 | 0.650 |
| milestone | 0.963 | 0.902 | 0.792 | 0.585 |
| preference | 0.873 | 0.889 | 0.824 | 0.760 |
| problem | 0.963 | 0.902 | 0.723 | 0.783 |
| reference | 0.982 | 0.982 | 0.982 | 0.943 |

Notes:

- `reference` was the failure mode flagged in the 2026-04-14 eval ("broken across all 9 models"). It is now the strongest or tied-strongest class across all four v2-trained encoders.
- `fact` remains the weakest class for the smaller encoders, consistent with its catch-all role in the taxonomy. ModernBERT closes most of that gap (0.852).
- `milestone` was MiniLM's weakest (0.585, low recall), and scales cleanly with encoder size — 0.963 at ModernBERT.
- DeBERTa-v3-small NaN'd under transformers 5.1 due to stale LayerNorm key names (`beta/gamma` → `weight/bias`); excluded from this leaderboard. Document the transformers 5.1 incompatibility if revisiting DeBERTa.

## Training settings

All four runs used the same hyperparameters unless noted:

- `--epochs 10` (early stopping patience 3 on macro F1)
- `--batch-size 32` (ModernBERT: 16, due to longer sequences from its native 8192 context)
- `--lr 3e-5`
- `--max-length 256`
- 85/15 stratified train/val split, seed 42

Training time on RTX 5060 (8.5 GB):

| Model | Wall time |
|---|---:|
| MiniLM-L12 | 107 s |
| DistilBERT-base | 133 s |
| RoBERTa-base | 359 s |
| ModernBERT-base | 561 s |

## Next steps

1. Publish the ModernBERT-base checkpoint as the production classification head. It beats the prior qwen3.5:4b baseline on a stricter eval set, at ~30× less inference cost and a fraction of the VRAM.
2. Consider a class-weighted loss to lift `fact` precision for the smaller encoders if a cheaper tier is needed.
3. Regenerate the qwen3.5:4b baseline on gold_v2 once GPU is freed up, to complete the fair-comparison leaderboard (current qwen number is stale from v1 gold).
