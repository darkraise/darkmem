#!/usr/bin/env bash
# Back up the darkmem Postgres database to a gzipped SQL dump.
# Usage: ./scripts/backup.sh [DEST_DIR]   (default: ./backups)
# Run on a schedule (cron) and copy the result OFF-HOST. Back up before upgrades.
set -euo pipefail

DEST_DIR="${1:-./backups}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

mkdir -p "$DEST_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="$DEST_DIR/darkmem-$STAMP.sql.gz"

echo "Dumping database '$DB' from compose service '$SERVICE' -> $OUT"
$COMPOSE exec -T "$SERVICE" pg_dump -U "$USER" -d "$DB" --clean --if-exists \
  | gzip -c > "$OUT"

echo "Backup complete: $OUT ($(du -h "$OUT" | cut -f1))"
echo "Copy this file to off-host storage."
