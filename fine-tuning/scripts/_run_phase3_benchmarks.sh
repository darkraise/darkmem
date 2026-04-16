#!/usr/bin/env bash
# Phase 3: head-level benchmarking.
#   - Entity: infer with gliner-small and gliner-large on test.jsonl (2k),
#     score with eval_entity.py.
#   - Relation: infer with rebel-large on rebel_test_gold.jsonl (1007),
#     score with eval_relation.py.
# Writes pred.jsonl, pred.runtime.json (latency + VRAM), and metrics.json
# into each model's runs/ dir.

set -u
cd "$(dirname "$0")/.."

GOLD_ENTITY="data/splits/test.jsonl"
GOLD_REL="data/splits/rebel_test_gold.jsonl"

for size in small large; do
  model="models/gliner-${size}-v2corpus/best"
  rundir="runs/gliner-${size}-v2corpus"
  if [ ! -d "${model}" ]; then
    echo "PHASE3_SKIP:gliner-${size}:missing ${model}"
    continue
  fi
  mkdir -p "${rundir}"
  echo "=== Phase 3a gliner-${size} infer ==="
  python -m scripts._infer_entity \
    --model "${model}" \
    --gold "${GOLD_ENTITY}" \
    --pred "${rundir}/pred.jsonl"
  echo "=== Phase 3a gliner-${size} score ==="
  python -m scripts.eval_entity \
    --gold "${GOLD_ENTITY}" \
    --pred "${rundir}/pred.jsonl" \
    --out "${rundir}/metrics.json"
done

model="models/rebel-large-v2corpus/best"
rundir="runs/rebel-large-v2corpus"
if [ -d "${model}" ]; then
  mkdir -p "${rundir}"
  echo "=== Phase 3b rebel infer ==="
  python -m scripts._infer_relation \
    --model "${model}" \
    --gold "${GOLD_REL}" \
    --pred "${rundir}/pred.jsonl"
  echo "=== Phase 3b rebel score ==="
  python -m scripts.eval_relation \
    --gold "${GOLD_REL}" \
    --pred "${rundir}/pred.jsonl" \
    --out "${rundir}/metrics.json"
else
  echo "PHASE3_SKIP:rebel:missing ${model}"
fi

echo "PHASE3_DONE:all"
