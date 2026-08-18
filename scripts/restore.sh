#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by backup.sh.
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
# WARNING: this overwrites the current database. Stop the API first.
set -euo pipefail

BACKUP_FILE="${1:?usage: restore.sh BACKUP_FILE.sql.gz}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

echo "This will OVERWRITE database '$DB'. Stop the darkmem service first."
read -r -p "Restore from $BACKUP_FILE? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }

echo "Restoring..."
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -v ON_ERROR_STOP=1

echo "Restore complete. Restart the API:  $COMPOSE up -d darkmem"
