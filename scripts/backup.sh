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

# Retention. A nightly cadence with no pruning is a disk-filling timer, not a
# backup policy — and this host runs the database it is dumping, so filling the
# disk takes production down with it. Keep the newest KEEP dumps and delete the
# rest; KEEP=0 disables pruning for a one-off manual dump.
KEEP="${BACKUP_KEEP:-14}"
if [ "$KEEP" -gt 0 ]; then
    # NUL-delimited and newest-first, so a filename with a space or a newline
    # cannot shift the boundary between "keep" and "delete".
    mapfile -d '' -t DUMPS < <(
        find "$DEST_DIR" -maxdepth 1 -name 'darkmem-*.sql.gz' -type f -printf '%T@ %p\0' \
        | sort -zrn | cut -z -d' ' -f2-
    )
    if [ "${#DUMPS[@]}" -gt "$KEEP" ]; then
        for old_dump in "${DUMPS[@]:$KEEP}"; do
            rm -f -- "$old_dump"
            echo "Pruned $old_dump (retention: newest $KEEP)"
        done
    fi
fi

echo "Copy this file to off-host storage."
