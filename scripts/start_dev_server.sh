#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../backend"

# Install dependencies if needed
if [ ! -d ".venv" ] && ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -e ".[dev]"
fi

# Run migrations (requires Postgres)
echo "Running migrations..."
python -m alembic upgrade head

# Start server with hot-reload
echo "Starting darkmem API server..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-include "*.py" --reload-dir app
