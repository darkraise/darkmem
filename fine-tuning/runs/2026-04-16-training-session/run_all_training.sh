#!/usr/bin/env bash
# Phase 2 master runner — trains GLiNER-small, GLiNER-large, REBEL-large
# sequentially. Emits "PHASE_DONE:<label>" on success for the Monitor filter.
# Any trainer crash writes "PHASE_FAIL:<label>:<exit>" but continues so later
# phases still execute (per the plan's failure-handling policy: GLiNER-small
# failure blocks, the other two don't).

set -u
cd "$(dirname "$0")/../.."  # back to fine-tuning/

SESSION_DIR="runs/2026-04-16-training-session"
FAIL_LOG="${SESSION_DIR}/failures.log"
: > "${FAIL_LOG}"

run_phase () {
  local label="$1"; shift
  local logfile="$1"; shift
  local outdir="$1"; shift
  mkdir -p "${outdir}"
  mkdir -p "$(dirname "${logfile}")"
  echo ">>> PHASE_START:${label} $(date -Iseconds)" | tee -a "${FAIL_LOG}"
  "$@" > "${logfile}" 2>&1
  local rc=$?
  if [ ${rc} -eq 0 ]; then
    echo "PHASE_DONE:${label}"
  else
    echo "PHASE_FAIL:${label}:${rc}" | tee -a "${FAIL_LOG}"
  fi
  return ${rc}
}

# 2a: already started manually; this script can be started fresh from 2b if needed.
if [ "${SKIP_2A:-0}" != "1" ]; then
  run_phase "gliner-small" \
    "runs/gliner-small-v2corpus/train.log" \
    "runs/gliner-small-v2corpus" \
    python -m scripts.train_gliner \
      --base-model urchade/gliner_small-v2.1 \
      --output-dir models/gliner-small-v2corpus \
      --epochs 5 --batch-size 16 --lr 1e-5
  small_rc=$?
  if [ ${small_rc} -ne 0 ]; then
    echo "PHASE_HALT:gliner-small failure is a blocker"
    exit ${small_rc}
  fi
fi

run_phase "gliner-large" \
  "runs/gliner-large-v2corpus/train.log" \
  "runs/gliner-large-v2corpus" \
  python -m scripts.train_gliner \
    --base-model urchade/gliner_large-v2.1 \
    --output-dir models/gliner-large-v2corpus \
    --epochs 5 --batch-size 8 --lr 1e-5

run_phase "rebel-large" \
  "runs/rebel-large-v2corpus/train.log" \
  "runs/rebel-large-v2corpus" \
  python -m scripts.train_rebel \
    --base-model Babelscape/rebel-large \
    --output-dir models/rebel-large-v2corpus \
    --epochs 3 --batch-size 2 --lr 3e-5 \
    --max-source-length 256 --max-target-length 128

echo "PHASE_DONE:all-training"
