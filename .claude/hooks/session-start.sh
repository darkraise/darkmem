#!/bin/bash
#
# SessionStart hook for Claude Code cloud sessions (claude.ai/code).
#
# Brings a fresh cloud container to the state CLAUDE.md's commands assume:
#   - backend/.venv on Python 3.13 with requirements.lock, the app (editable)
#     and the test tools CI installs (pytest, pytest-asyncio, ruff). 3.13 is
#     the dev hosts' interpreter, and sdks/python's surface test whitelists
#     3.13-only class attributes; the image and CI run 3.12, and the backend
#     suite passes on both;
#   - frontend/node_modules from package-lock.json via `npm ci` (the SDK
#     suites borrow its tsc and vitest; extension/ needs no install);
#   - PostgreSQL 17 + pgvector 0.8 from the PGDG apt repo, listening on
#     127.0.0.1:5433 as darkmem/darkmem with the dev databases CLAUDE.md
#     names. CI uses pgvector/pgvector:0.8.2-pg17; Ubuntu's own pgvector is
#     0.6, which lacks `hnsw.iterative_scan` (set by app/database.py).
#
# Runs only when CLAUDE_CODE_REMOTE=true, so it never touches a developer's
# machine or the production host. Idempotent: the container is snapshotted
# after the first run, and later sessions only restart Postgres and skip
# installs whose lockfile hash is unchanged.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
    exit 0
fi

REPO="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)}"
BACKEND="$REPO/backend"
FRONTEND="$REPO/frontend"
VENV="$BACKEND/.venv"
PY_VERSION=3.13

PG_MAJOR=17
PG_CLUSTER=main
PG_PORT=5433
PG_DATABASES="darkmem darkmem_test darkmem_test_2 darkmem_test_3 darkmem_test_4 darkmem_test_5 darkmem_bench"

# stdout of a SessionStart hook becomes session context; keep progress on stderr.
log() { echo "[session-start] $*" >&2; }

hash_files() { cat "$@" | sha256sum | cut -d' ' -f1; }

# ── backend: Python venv ────────────────────────────────────────────
if [ -x "$VENV/bin/python" ] \
    && [ "$("$VENV/bin/python" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" != "$PY_VERSION" ]; then
    log "backend/.venv is not Python $PY_VERSION; recreating it"
    rm -rf "$VENV"
fi
if [ ! -x "$VENV/bin/python" ]; then
    log "creating backend/.venv (Python $PY_VERSION)"
    uv venv --quiet --python "$PY_VERSION" "$VENV"
fi

BACKEND_STAMP="$VENV/.darkmem-deps.sha256"
BACKEND_HASH="$(hash_files "$BACKEND/requirements.lock" "$BACKEND/pyproject.toml")"
if [ "$(cat "$BACKEND_STAMP" 2>/dev/null || true)" != "$BACKEND_HASH" ]; then
    log "installing backend dependencies (requirements.lock)"
    # Same set as CI's "Install (pinned)" step, but the app is editable so
    # scripts outside backend/ (sdks/generate.py, harnesses) never import a
    # stale copy of app/.
    uv pip install --quiet --python "$VENV/bin/python" -r "$BACKEND/requirements.lock"
    uv pip install --quiet --python "$VENV/bin/python" --no-deps -e "$BACKEND"
    uv pip install --quiet --python "$VENV/bin/python" pytest pytest-asyncio ruff
    echo "$BACKEND_HASH" > "$BACKEND_STAMP"
else
    log "backend dependencies up to date"
fi

# ── frontend: npm ci ─────────────────────────────────────────────────────
# `npm ci`, not `npm install`: the committed lockfile is not in sync with
# package.json, and `npm install` would rewrite it in the working tree.
# HUSKY=0 keeps the `prepare` script from setting core.hooksPath.
FRONTEND_STAMP="$FRONTEND/node_modules/.darkmem-lock.sha256"
FRONTEND_HASH="$(hash_files "$FRONTEND/package-lock.json")"
if [ "$(cat "$FRONTEND_STAMP" 2>/dev/null || true)" != "$FRONTEND_HASH" ]; then
    log "installing frontend dependencies (npm ci)"
    (cd "$FRONTEND" && HUSKY=0 npm ci --no-audit --no-fund --loglevel=error >&2)
    echo "$FRONTEND_HASH" > "$FRONTEND_STAMP"
else
    log "frontend dependencies up to date"
fi

# ── PostgreSQL 17 + pgvector on :5433 ────────────────────────────────────
if ! dpkg -s "postgresql-$PG_MAJOR-pgvector" >/dev/null 2>&1; then
    log "installing PostgreSQL $PG_MAJOR + pgvector from apt.postgresql.org"
    PGDG_KEY=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc
    install -d "$(dirname "$PGDG_KEY")"
    curl -fsSL -o "$PGDG_KEY" https://www.postgresql.org/media/keys/ACCC4CF8.asc
    . /etc/os-release
    echo "deb [signed-by=$PGDG_KEY] https://apt.postgresql.org/pub/repos/apt ${VERSION_CODENAME}-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list
    apt-get update -qq >&2
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        "postgresql-$PG_MAJOR" "postgresql-$PG_MAJOR-pgvector" >&2
fi

if ! pg_lsclusters -h | awk '{print $1"/"$2}' | grep -qx "$PG_MAJOR/$PG_CLUSTER"; then
    log "creating cluster $PG_MAJOR/$PG_CLUSTER on port $PG_PORT"
    pg_createcluster --port "$PG_PORT" "$PG_MAJOR" "$PG_CLUSTER" >&2
fi
if [ "$(pg_conftool -s "$PG_MAJOR" "$PG_CLUSTER" show port)" != "$PG_PORT" ]; then
    pg_ctlcluster "$PG_MAJOR" "$PG_CLUSTER" stop 2>/dev/null || true
    pg_conftool "$PG_MAJOR" "$PG_CLUSTER" set port "$PG_PORT"
fi
if ! pg_isready -q -h 127.0.0.1 -p "$PG_PORT"; then
    log "starting PostgreSQL $PG_MAJOR on port $PG_PORT"
    pg_ctlcluster "$PG_MAJOR" "$PG_CLUSTER" start
    for _ in $(seq 1 30); do
        pg_isready -q -h 127.0.0.1 -p "$PG_PORT" && break
        sleep 1
    done
    pg_isready -q -h 127.0.0.1 -p "$PG_PORT"
fi

as_postgres() { runuser -u postgres -- "$@"; }
pg_admin() { as_postgres psql -X -q -p "$PG_PORT" -v ON_ERROR_STOP=1 -tAc "$1"; }

# Superuser, like the pgvector image's POSTGRES_USER: conftest drops and
# recreates the public schema and alembic creates the vector extension.
if [ "$(pg_admin "SELECT 1 FROM pg_roles WHERE rolname = 'darkmem'")" != "1" ]; then
    pg_admin "CREATE ROLE darkmem LOGIN SUPERUSER PASSWORD 'darkmem'"
fi
for db in $PG_DATABASES; do
    if [ "$(pg_admin "SELECT 1 FROM pg_database WHERE datname = '$db'")" != "1" ]; then
        as_postgres createdb -p "$PG_PORT" -O darkmem "$db"
    fi
done

# ── session environment ──────────────────────────────────────────────────
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    {
        echo "export PATH=\"$VENV/bin:\$PATH\""
        # Host-side alembic and the dev server read DATABASE_URL (default
        # port 5432); pytest ignores it and pins TEST_DATABASE_URL instead.
        echo "export DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:$PG_PORT/darkmem"
        echo "export PGHOST=127.0.0.1 PGPORT=$PG_PORT PGUSER=darkmem PGPASSWORD=darkmem"
    } >> "$CLAUDE_ENV_FILE"
fi

log "done"

cat <<EOF
Cloud session environment (set up by .claude/hooks/session-start.sh). It differs from CLAUDE.md's "Host environment":
- No Docker daemon and no production instance here. Postgres $PG_MAJOR + pgvector runs natively on 127.0.0.1:$PG_PORT (darkmem/darkmem) with databases: $PG_DATABASES. Use \`psql -d <db>\` (PG* vars are set) instead of \`docker exec darkmem-postgres-1 psql\`.
- backend/.venv (Python $PY_VERSION) is first on PATH; DATABASE_URL points at the darkmem database on :$PG_PORT.
- Backend tests: \`cd backend && .venv/bin/python -m pytest -q <path>\`. Frontend: \`cd frontend && npm run typecheck\` / \`npm test\`.
- \`./scripts/gate.sh\` stops with GATE BLOCKED here: the gitignored F1 bench cache (backend/scripts/extraction_bench/.cache) is machine-local. Run its legs individually.
EOF
