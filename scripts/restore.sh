#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by backup.sh.
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
# WARNING: this drops and recreates the database. Stop the API first.
set -euo pipefail

BACKUP_FILE="${1:?usage: restore.sh BACKUP_FILE.sql.gz}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

# From the recreate below onwards this file is the only surviving copy, so it is
# proved good while the database still exists. gzip of an empty stream is itself
# valid gzip, so integrity alone proves nothing — pg_dump writes the completion
# marker last and only on success, the same evidence backup.sh checks before it
# publishes a dump.
if ! gunzip -c "$BACKUP_FILE" 2>/dev/null | tail -c 512 \
     | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Not a complete pg_dump dump: $BACKUP_FILE" >&2
    echo "Nothing was changed." >&2
    exit 1
fi

echo "This will DROP AND RECREATE database '$DB'. Stop the darkmem service first."
read -r -p "Restore from $BACKUP_FILE? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }

# Never replay a --clean dump over a live schema. `events` is declaratively
# RANGE-partitioned, so the dump's DROP phase carries one `ALTER TABLE ONLY
# events_YYYYMM DROP CONSTRAINT events_YYYYMM_pkey` per monthly child, and
# PostgreSQL refuses to drop an inherited constraint. ON_ERROR_STOP aborts
# there — after every trigger and foreign key above it is already gone and
# before the first CREATE — leaving a database with all its rows and none of
# its structure. An empty target leaves those statements nothing to match.
echo "Recreating database '$DB'..."
$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE);" \
  -c "CREATE DATABASE \"$DB\" OWNER \"$USER\";"

echo "Restoring..."
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Restore complete. Restart the API:  $COMPOSE up -d darkmem"
