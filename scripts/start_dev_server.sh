#!/usr/bin/env bash
set -euo pipefail

# Without DATABASE_URL the app derives localhost:5432, which on the
# production host is the production database: migrating it from a dev
# checkout is never wanted, so the database must be named.
if [ -z "${DATABASE_URL:-}" ]; then
    echo "DATABASE_URL is not set; export the dev database URL (for example the dev Postgres on 127.0.0.1:5433) and run again." >&2
    exit 1
fi

cd "$(dirname "$0")/../backend"

PYTHON="$PWD/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
    echo "Creating backend/.venv and installing dependencies..."
    python3 -m venv .venv
    "$PYTHON" -m pip install -e ".[dev]"
fi

# Run migrations (requires Postgres)
echo "Running migrations..."
"$PYTHON" -m alembic upgrade head

# Start server with hot-reload.
# --timeout-keep-alive 75 keeps backend keep-alive sockets open longer than
# the dev proxy's idle reuse window so the proxy never reuses a half-closed
# socket (otherwise users see sporadic 502 Bad Gateway on the first request
# after a quiet pause, e.g. the Fetch Models click in the setup wizard).
echo "Starting darkmem API server..."
exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
    --reload-include "*.py" --reload-dir app \
    --timeout-keep-alive 75 --no-proxy-headers
