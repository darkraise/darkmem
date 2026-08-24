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

# Dump to a name the retention glob cannot match, and rename only once the
# dump is known good. The redirection below creates its target before pg_dump
# writes a byte and gzip -c exits 0 on empty input, so writing straight to
# $OUT leaves a well-formed empty .sql.gz behind on every failure — and
# retention sorts by mtime alone, so those artefacts are always the newest
# files on disk and survive every prune while real dumps age past KEEP.
PART="$OUT.part"
trap 'rm -f -- "$PART"' EXIT

echo "Dumping database '$DB' from compose service '$SERVICE' -> $OUT"
$COMPOSE exec -T "$SERVICE" pg_dump -U "$USER" -d "$DB" --clean --if-exists \
  | gzip -c > "$PART"

# pg_dump writes this marker last and only on success, so it also catches the
# truncated stream that still exits 0, which pipefail cannot see. A size floor
# would not: this database's nightly dumps have ranged from 14 KB to 2.4 MB.
if ! gunzip -c "$PART" | tail -c 512 | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Incomplete dump: no pg_dump completion marker. Nothing written to $OUT." >&2
    exit 1
fi

mv -- "$PART" "$OUT"

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
