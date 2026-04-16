#!/usr/bin/env bash
# Phase 4: run the 2-head extraction pipeline (GLiNER + REBEL) against the
# canonical 2k test split, capturing nvidia-smi VRAM every 10 seconds into
# vram.csv for peak analysis. Runs twice: once with gliner-small, once with
# gliner-large. metrics + report land in fine-tuning/eval_results/ per run.
#
# Usage: bash scripts/_run_phase4_pipeline.sh

set -u
cd "$(dirname "$0")/.."  # back to fine-tuning/

run_pipeline () {
  local size="$1"       # small | large
  local out_dir="runs/e2e-${size}"
  mkdir -p "${out_dir}"
  local vram_csv="${out_dir}/vram.csv"

  # VRAM logger loop in background
  (
    echo "iso_ts,memory_used_mb,memory_free_mb,memory_total_mb"
    while true; do
      now=$(date -Iseconds)
      vals=$(nvidia-smi --query-gpu=memory.used,memory.free,memory.total \
                       --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -d ' ')
      if [ -n "${vals}" ]; then
        echo "${now},${vals}"
      fi
      sleep 10
    done
  ) > "${vram_csv}" &
  local logger_pid=$!

  echo "=== Phase 4 ${size} pipeline (logger pid ${logger_pid}) ==="
  python -m scripts.evaluate \
    --gliner-model "models/gliner-${size}-v2corpus/best" \
    --rebel-model "models/rebel-large-v2corpus/best" \
    --test-split \
    > "${out_dir}/run.log" 2>&1
  local rc=$?

  kill "${logger_pid}" 2>/dev/null || true
  wait "${logger_pid}" 2>/dev/null || true

  # Copy eval_results into the per-run dir so we don't lose them to the next run
  if [ -f "eval_results/results.json" ]; then
    cp eval_results/results.json "${out_dir}/metrics.json"
  fi
  if [ -f "eval_results/report.md" ]; then
    cp eval_results/report.md "${out_dir}/report.md"
  fi

  if [ ${rc} -eq 0 ]; then
    echo "PHASE4_DONE:${size}"
  else
    echo "PHASE4_FAIL:${size}:${rc}"
  fi
  return ${rc}
}

run_pipeline small
run_pipeline large
echo "PHASE4_DONE:all"
