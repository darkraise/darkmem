#!/usr/bin/env bash
# One-shot orchestrator: train 3 ModernBERT-base seeds with hardened recipe,
# then ensemble-infer on gold_v2 and score.
#
# Requires RTX 5060 (8.5 GB) free. ~30 min end-to-end.

set -euo pipefail
cd "$(dirname "$0")/.."

RUN_DIR="runs/classification-v2-modernbert-base-ensemble"
mkdir -p "${RUN_DIR}"

BASE="answerdotai/ModernBERT-base"
SEEDS=(42 7 1337)

COMMON_ARGS=(
  --base "${BASE}"
  --epochs 10
  --batch-size 8
  --lr 3e-5
  --max-length 512
  --bf16
  --lr-scheduler-type cosine
  --label-smoothing 0.05
  --trust-remote-code
)

MODEL_DIRS=()
for s in "${SEEDS[@]}"; do
  out="models/classifier-v2-modernbert-base-seed${s}"
  MODEL_DIRS+=("${out}/best")
  if [ -d "${out}/best" ]; then
    echo "SKIP seed ${s} — already present at ${out}/best"
    continue
  fi
  echo "=== training seed ${s} ==="
  python -m scripts.train_classifier \
    "${COMMON_ARGS[@]}" \
    --seed "${s}" \
    --output-dir "${out}" \
    > "${RUN_DIR}/seed${s}.train.log" 2>&1
  echo "=== done seed ${s} ==="
done

echo "=== ensemble inference on gold_v2 ==="
python -m scripts.infer_ensemble \
  --models "${MODEL_DIRS[@]}" \
  --gold ../docs/e2e/scripts/classification_eval/corpus/gold_v2.jsonl \
  --out "${RUN_DIR}/gold_v2_preds.jsonl" \
  --norm-out "${RUN_DIR}/gold_v2_norm.jsonl" \
  --max-length 512

echo "=== scoring ==="
python -m scripts.eval_classifier \
  --gold "${RUN_DIR}/gold_v2_norm.jsonl" \
  --pred "${RUN_DIR}/gold_v2_preds.jsonl" \
  --out "${RUN_DIR}/gold_v2_metrics.json"

echo
echo "=== ensemble results (gold_v2) ==="
python - <<'PY'
import json
from pathlib import Path
m = json.loads(Path("runs/classification-v2-modernbert-base-ensemble/gold_v2_metrics.json").read_text())
print(f"accuracy     {m['accuracy']:.4f}")
print(f"macro_f1     {m['macro_f1']:.4f}")
print(f"ref_recall   {m['reference_recall']:.4f}")
print()
print("per-class F1:")
for t, v in sorted(m['per_type'].items()):
    print(f"  {t:<14} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f} n={v['support']}")
PY
