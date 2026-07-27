#!/usr/bin/env bash
#
# The merge gate, scripted (T0.16).
#
# There is no hosted CI. Doc 17 §9 makes the gate a *discipline, scripted*:
# one command runs the whole floor, so the posture is command-shaped and a
# future CI pipeline is a transcription of this file rather than a design
# task. Run it before merging anything.
#
#   ./scripts/gate.sh           # the floor: backend, frontend, F1 bench (cached)
#   ./scripts/gate.sh --full    # the floor plus the retrieval eval and e2e
#
# Exits non-zero on the first failing gate and names it. Every process it
# starts is reaped, including on failure.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
BACKEND="$REPO_ROOT/backend"
FRONTEND="$REPO_ROOT/frontend"
PY="$BACKEND/.venv/bin/python"

FULL=0
for arg in "$@"; do
    case "$arg" in
        --full) FULL=1 ;;
        -h|--help) sed -n '3,14p' "${BASH_SOURCE[0]}"; exit 0 ;;
        *) echo "gate: unknown argument '$arg' (expected --full)" >&2; exit 2 ;;
    esac
done

# ── process hygiene ──────────────────────────────────────────────────────
# Every gate runs in its own process group so a hung or failing step takes
# its whole tree down with it — a stray vitest or playwright worker holding
# a port is exactly what makes the next run fail for the wrong reason.
declare -a STARTED_PGIDS=()

cleanup() {
    local status=$?
    for pgid in "${STARTED_PGIDS[@]}"; do
        [ -n "$pgid" ] || continue
        # Only ever signal a group this script started.
        kill -TERM "-$pgid" 2>/dev/null || true
    done
    # Give a graceful TERM a moment, then insist.
    if [ ${#STARTED_PGIDS[@]} -gt 0 ]; then
        sleep 1
        for pgid in "${STARTED_PGIDS[@]}"; do
            [ -n "$pgid" ] || continue
            kill -KILL "-$pgid" 2>/dev/null || true
        done
    fi
    return $status
}
trap cleanup EXIT INT TERM

FAILED_GATE=""

# run_gate <name> <timeout-seconds> <working-dir> <command...>
run_gate() {
    local name="$1"; shift
    local secs="$1"; shift
    local dir="$1"; shift

    printf '\n\033[1m── %s ──\033[0m\n' "$name"
    if [ -n "$FAILED_GATE" ]; then
        echo "skipped (a previous gate failed)"
        return 0
    fi

    # setsid puts the child in its own process group so cleanup can signal
    # the whole tree; timeout bounds it so a hang cannot linger.
    setsid timeout "$secs" "$@" &
    local pid=$!
    STARTED_PGIDS+=("$pid")   # setsid makes PID == PGID
    wait "$pid"
    local rc=$?

    if [ $rc -ne 0 ]; then
        FAILED_GATE="$name"
        if [ $rc -eq 124 ]; then
            echo "gate '$name' TIMED OUT after ${secs}s" >&2
        else
            echo "gate '$name' FAILED (exit $rc)" >&2
        fi
    fi
    return 0
}

cd "$REPO_ROOT" || exit 1

# ── preflight ────────────────────────────────────────────────────────────
# A missing toolchain is an environment problem, not a failing gate. Say so
# in those words: a bare `tsc: not found` (exit 127) sends the reader after
# a type error that does not exist.
preflight_fail() {
    printf '\033[1;33mGATE BLOCKED\033[0m — %s\n' "$1" >&2
    exit 2
}

[ -x "$PY" ] || preflight_fail "backend venv missing at $PY (create it, then re-run)"
[ -d "$FRONTEND/node_modules" ] || preflight_fail \
    "frontend dependencies not installed — run 'cd frontend && npm ci' first"


# ── the floor ────────────────────────────────────────────────────────────

# The single-revision assertion (doc 19 §2, T0.15).
#
# The greenfield baseline is ONE revision, regenerated in place until the
# first deploy whose data must survive — the homelab cutover — at which event
# it is tagged and frozen. Until that tag exists, a second revision means
# somebody quietly started the chain early, which is exactly what this holds
# shut. After the freeze, a linear chain is correct and the check stands down.
FREEZE_TAG="schema-frozen"
assert_single_revision() {
    printf '\n\033[1m── %s ──\033[0m\n' "alembic single-revision"
    if [ -n "$FAILED_GATE" ]; then echo "skipped (a previous gate failed)"; return 0; fi

    if git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$FREEZE_TAG" >/dev/null 2>&1; then
        echo "freeze tag '$FREEZE_TAG' exists — the chain is open; assertion stands down"
        return 0
    fi

    local count
    count=$(cd "$BACKEND" && "$PY" -m alembic history 2>/dev/null | grep -c '.')
    if [ "$count" -ne 1 ]; then
        FAILED_GATE="alembic single-revision"
        echo "expected exactly 1 revision before the freeze, found $count." >&2
        echo "A schema change REGENERATES the baseline in place; it never appends 0002." >&2
        (cd "$BACKEND" && "$PY" -m alembic history 2>/dev/null) >&2
        return 0
    fi
    echo "1 revision, unfrozen — correct"
}
assert_single_revision


# Backend suite. conftest overwrites DATABASE_URL from TEST_DATABASE_URL, so
# the gate must set the latter or it silently tests a different database.
run_gate "backend pytest" 1500 "$BACKEND" \
    env -C "$BACKEND" \
        TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test}" \
        "$PY" -m pytest -q

# Frontend. `tsc -b` (not plain tsc) — plain tsc misses the project refs.
run_gate "frontend typecheck" 600 "$FRONTEND" \
    env -C "$FRONTEND" npm run typecheck

run_gate "frontend test" 900 "$FRONTEND" \
    env -C "$FRONTEND" npm test

run_gate "frontend build" 900 "$FRONTEND" \
    env -C "$FRONTEND" npm run build

# The F1 bench in --algo-only mode: it errors rather than calling the LLM if
# any output is uncached, which is what keeps the gate free of live calls and
# therefore fast, offline and deterministic.
run_gate "extraction F1 bench (--algo-only)" 900 "$BACKEND" \
    env -C "$BACKEND" "$PY" scripts/extraction_bench/run_bench.py --algo-only

# ── --full: the measured gates ───────────────────────────────────────────
if [ "$FULL" -eq 1 ]; then
    run_gate "retrieval eval" 3600 "$BACKEND" \
        env -C "$BACKEND" "$PY" scripts/benchlib/run_retrieval_eval.py

    run_gate "playwright e2e" 1800 "$FRONTEND" \
        env -C "$FRONTEND" npm run test:e2e
fi

# ── verdict ──────────────────────────────────────────────────────────────
printf '\n'
if [ -n "$FAILED_GATE" ]; then
    printf '\033[1;31mGATE RED\033[0m — failed at: %s\n' "$FAILED_GATE" >&2
    exit 1
fi

if [ "$FULL" -eq 1 ]; then
    printf '\033[1;32mGATE GREEN\033[0m — floor + retrieval eval + e2e\n'
else
    printf '\033[1;32mGATE GREEN\033[0m — floor (run with --full before a phase boundary)\n'
fi
