#!/bin/sh
set -e
echo "Running database migrations..."
python -m alembic upgrade head

# The migration above can be a NO-OP that reports success. Before the schema
# freeze a change regenerates 0001_baseline.py in place rather than appending a
# revision, so the revision id never moves and `upgrade head` compares 0001 to
# 0001 and does nothing -- while the code goes on to query columns the database
# does not have. Production drifted five columns that way and article_synthesis
# died on every run for days, visible only in its own config row.
#
# This compares the baseline's CONTENT, which is the part that moves, and
# refuses to serve on a mismatch. Retire it at the freeze, when revisions become
# additive and alembic's own comparison does the job.
echo "Checking schema baseline..."
python -m app.schema_guard

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --no-proxy-headers
