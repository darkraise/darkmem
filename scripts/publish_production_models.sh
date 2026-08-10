#!/usr/bin/env bash
# Publish every production ML dependency in one pass.
#
#   1. Upload the five fine-tuned darkmem heads to HuggingFace Hub.
#   2. Ensure the configured Ollama LLMs are pulled on the target Ollama host.
#
# darkmem fine-tuned heads (GLiNER, ModernBERT, REBEL, bge) are NOT served by
# Ollama. Ollama models are decoder-only LLMs pulled from the public registry.
# Treat the two halves of this script accordingly.
#
# Required env:
#   HF_USER         — HuggingFace username or org to publish under.
#   HF_TOKEN        — write token for that user/org.
#   OLLAMA_HOST     — Ollama base URL (defaults to http://localhost:11434).
#
# Optional env:
#   HF_PRIVATE=1    — create private repos (default: public).
#   DARKMEM_API     — base URL of a running backend (used with --from-backend).
#   DRY_RUN=1       — print the plan without pushing/pulling.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

: "${HF_USER:?HF_USER must be set (e.g. HF_USER=darkraise)}"
: "${HF_TOKEN:?HF_TOKEN must be set (write scope)}"

hf_args=(--hf-user "$HF_USER" --token "$HF_TOKEN")
if [[ "${HF_PRIVATE:-0}" == "1" ]]; then
    hf_args+=(--visibility private)
else
    hf_args+=(--visibility public)
fi
if [[ "${DRY_RUN:-0}" == "1" ]]; then
    hf_args+=(--dry-run)
fi

echo "=== 1/2 Uploading darkmem heads to HuggingFace (${HF_USER}) ==="
(cd "$REPO_ROOT/fine-tuning" && python -m scripts.upload_to_hub "${hf_args[@]}")

echo
echo "=== 2/2 Ensuring Ollama LLMs on ${OLLAMA_HOST:-http://localhost:11434} ==="
ollama_args=()
if [[ "${DRY_RUN:-0}" == "1" ]]; then
    ollama_args+=(--dry-run)
fi
if [[ -n "${DARKMEM_API:-}" ]]; then
    ollama_args+=(--from-backend --api "$DARKMEM_API")
fi
if [[ -n "${OLLAMA_HOST:-}" ]]; then
    ollama_args+=(--ollama-host "$OLLAMA_HOST")
fi

python "$REPO_ROOT/scripts/ensure_ollama_models.py" "${ollama_args[@]}"

echo
echo "Done. HuggingFace repos under ${HF_USER}/; Ollama daemon synced."
