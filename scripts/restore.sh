#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by backup.sh.
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
# WARNING: this replaces the database with the restored copy. Stop the API
# first. It transiently holds both the old and the restored database on disk.
set -euo pipefail

BACKUP_FILE="${1:?usage: restore.sh BACKUP_FILE.sql.gz}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"

[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

# gzip of an empty stream is itself valid gzip, so integrity alone proves
# nothing about the dump underneath it. pg_dump writes this completion
# marker last and only on a run that finished, so its presence is what
# proves the dump is whole.
if ! gunzip -c "$BACKUP_FILE" 2>/dev/null | tail -c 512 \
     | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Not a complete pg_dump dump: $BACKUP_FILE" >&2
    echo "Nothing was changed." >&2
    exit 1
fi

echo "This will REPLACE database '$DB'. Stop the darkmem service first."
read -r -p "Restore from $BACKUP_FILE? [y/N] " ans
[ "$ans" = "y" ] || [ "$ans" = "Y" ] || { echo "Aborted."; exit 1; }

# Replay into a side database and swap it in only on success, so the window in
# which "$DB" does not exist is the drop+rename below, not the whole replay. A
# dump that aborts partway through (a missing extension, any statement psql
# rejects) leaves the side database as debris and "$DB" untouched, rather than
# leaving "$DB" itself half-restored with no way back.
TEMP_DB="${DB}_restore_$$"
STAGE="none"

cleanup() {
    local rc=$?
    trap - EXIT
    if [ "$rc" -eq 0 ]; then
        return 0
    fi
    echo >&2
    echo "Restore FAILED (exit $rc)." >&2
    echo "Dump file is intact and unchanged: $BACKUP_FILE" >&2
    case "$STAGE" in
        original_dropped)
            echo "'$DB' was DROPPED and the restored copy was NOT renamed into place." >&2
            echo "'$DB' does not currently exist. The restored data is in '$TEMP_DB'." >&2
            echo "Finish the restore by hand:" >&2
            echo "  $COMPOSE exec -T \"$SERVICE\" psql -U \"$USER\" -d postgres -c 'ALTER DATABASE \"$TEMP_DB\" RENAME TO \"$DB\";'" >&2
            ;;
        temp_created)
            echo "Original database '$DB' is untouched." >&2
            echo "Drop the leftover restore copy to clean up:" >&2
            echo "  $COMPOSE exec -T \"$SERVICE\" psql -U \"$USER\" -d postgres -c 'DROP DATABASE IF EXISTS \"$TEMP_DB\";'" >&2
            ;;
        *)
            echo "Original database '$DB' is untouched. Nothing else to clean up." >&2
            ;;
    esac
}
trap cleanup EXIT

echo "Creating temporary database '$TEMP_DB'..."
$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "DROP DATABASE IF EXISTS \"$TEMP_DB\";" \
  -c "CREATE DATABASE \"$TEMP_DB\" OWNER \"$USER\";"
STAGE="temp_created"

# `events` is declaratively RANGE-partitioned, so a --clean dump carries one
# `ALTER TABLE ONLY events_YYYYMM DROP CONSTRAINT events_YYYYMM_pkey` per
# monthly child, and PostgreSQL refuses to drop an inherited constraint --
# fatal if replayed over a database that already has the schema. The empty
# temporary database leaves those statements nothing to match.
echo "Restoring into '$TEMP_DB'..."
gunzip -c "$BACKUP_FILE" | $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$TEMP_DB" -v ON_ERROR_STOP=1

echo "Replacing '$DB' with the restored copy..."
DROP_CLAUSE="DROP DATABASE IF EXISTS \"$DB\";"
if [ "${RESTORE_FORCE:-0}" = "1" ]; then
    DROP_CLAUSE="DROP DATABASE IF EXISTS \"$DB\" WITH (FORCE);"
fi
if ! $COMPOSE exec -T "$SERVICE" psql -U "$USER" -d postgres -v ON_ERROR_STOP=1 -c "$DROP_CLAUSE"; then
    echo "Could not drop '$DB' -- it likely still has active connections." >&2
    echo "Stop the darkmem service first:  $COMPOSE stop darkmem" >&2
    echo "Or re-run with RESTORE_FORCE=1 to terminate connections automatically." >&2
    exit 1
fi
STAGE="original_dropped"

$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d postgres -v ON_ERROR_STOP=1 \
  -c "ALTER DATABASE \"$TEMP_DB\" RENAME TO \"$DB\";"

echo "Restore complete. Restart the API:  $COMPOSE up -d darkmem"
