#!/bin/sh
set -e
echo "Running database migrations..."
python -m alembic upgrade head

# The migration above can be a NO-OP that reports success. Until 2026-09-28 a
# schema change regenerated 0001_baseline.py in place rather than appending a
# revision, so a database built from an older copy is still stamped 0001 and
# `upgrade head` compares 0001 to 0001 and does nothing -- while the code goes
# on to query columns the database does not have. Production drifted five
# columns that way and article_synthesis died on every run for days.
#
# The baseline is permanent now and later changes are chained revisions, but
# the databases built from the regenerated copies still exist. This compares
# the baseline's CONTENT and refuses to serve on a mismatch.
echo "Checking schema baseline..."
python -m app.schema_guard

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
