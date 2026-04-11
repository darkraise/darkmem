#!/bin/bash
# Shared environment variables for darkmem E2E scripts.
# Source this file before running scripts manually:
#   source env.sh && python 00_health_check.py

export DARKMEM_BASE_URL="${DARKMEM_BASE_URL:-http://localhost:8000}"
export DARKMEM_PASSWORD="${DARKMEM_PASSWORD:-e2e-admin-pw}"
export DARKMEM_BACKEND_DIR="${DARKMEM_BACKEND_DIR:-/workspace/darkmem/backend}"

# Optional: path to a small local repo for code indexing tests
export E2E_REPO_PATH="${E2E_REPO_PATH:-/workspace/darkmem/backend}"

echo "darkmem E2E environment loaded:"
echo "  DARKMEM_BASE_URL=$DARKMEM_BASE_URL"
echo "  DARKMEM_PASSWORD=<hidden>"
echo "  DARKMEM_BACKEND_DIR=$DARKMEM_BACKEND_DIR"
echo "  E2E_REPO_PATH=$E2E_REPO_PATH"
