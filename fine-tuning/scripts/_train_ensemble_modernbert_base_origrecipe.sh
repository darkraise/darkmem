#!/usr/bin/env bash
# Variant of _train_ensemble_modernbert_base.sh using the ORIGINAL base recipe
# (linear LR, max_len 256, no label smoothing, no bf16) to isolate the effect
# of ensembling alone vs. the stacked recipe.

set -euo pipefail
cd "$(dirname "$0")/.."

RUN_DIR="runs/classification-v2-modernbert-base-ensemble-origrecipe"
mkdir -p "${RUN_DIR}"

BASE="answerdotai/ModernBERT-base"
SEEDS=(42 7 1337)

COMMON_ARGS=(
  --base "${BASE}"
  --epochs 10
  --batch-size 16
  --lr 3e-5
  --max-length 256
  --trust-remote-code
)

MODEL_DIRS=()
for s in "${SEEDS[@]}"; do
  out="models/classifier-v2-modernbert-base-orig-seed${s}"
  MODEL_DIRS+=("${out}/best")
  if [ -d "${out}/best" ]; then
    echo "SKIP seed ${s} — already present at ${out}/best"
    continue
  fi
  echo "=== training orig-recipe seed ${s} ==="
  python -m scripts.train_classifier \
    "${COMMON_ARGS[@]}" \
    --seed "${s}" \
    --output-dir "${out}" \
    > "${RUN_DIR}/seed${s}.train.log" 2>&1
  echo "=== done orig-recipe seed ${s} ==="
done

echo "=== ensemble inference on gold_v2 ==="
python -m scripts.infer_ensemble \
  --models "${MODEL_DIRS[@]}" \
  --gold ../docs/e2e/scripts/classification_eval/corpus/gold_v2.jsonl \
  --out "${RUN_DIR}/gold_v2_preds.jsonl" \
  --norm-out "${RUN_DIR}/gold_v2_norm.jsonl" \
  --max-length 256

echo "=== scoring ==="
python -m scripts.eval_classifier \
  --gold "${RUN_DIR}/gold_v2_norm.jsonl" \
  --pred "${RUN_DIR}/gold_v2_preds.jsonl" \
  --out "${RUN_DIR}/gold_v2_metrics.json"

echo
echo "=== orig-recipe ensemble results (gold_v2) ==="
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path("runs/classification-v2-modernbert-base-ensemble-origrecipe/gold_v2_metrics.json").read_text())
print(f"accuracy     {m['accuracy']:.4f}")
print(f"macro_f1     {m['macro_f1']:.4f}")
print(f"ref_recall   {m['reference_recall']:.4f}")
print()
print("per-class F1:")
for t, v in sorted(m['per_type'].items()):
    print(f"  {t:<14} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f} n={v['support']}")
PY
