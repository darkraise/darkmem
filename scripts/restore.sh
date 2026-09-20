#!/usr/bin/env bash
# Restore the darkmem Postgres database from a gzipped SQL dump made by
# backup.sh or by the backup_ship job.
#
# Usage: ./scripts/restore.sh BACKUP_FILE.sql.gz
#        ./scripts/restore.sh --from DESTINATION [--identity FILE] [SNAPSHOT]
#
# WARNING: this replaces the database with the restored copy. Stop the API
# first. It transiently holds both the old and the restored database on disk.
#
# `--from` fetches the snapshot off a configured destination first, verifies
# its checksum against what the destination reports, decrypts it if it is
# age-encrypted, and then falls through to exactly the same marker check,
# confirmation and side-database replay as the plain form. **Decryption
# happens here, on the host, never in the container**: the container must
# never hold the age identity, because a snapshot that could be decrypted
# where it is stored is not encrypted at rest.
set -euo pipefail

SERVICE="${POSTGRES_SERVICE:-postgres}"
DB="${POSTGRES_DB:-darkmem}"
USER="${POSTGRES_USER:-darkmem}"
COMPOSE="${COMPOSE_CMD:-docker compose}"
APP_SERVICE="${APP_SERVICE:-darkmem}"
DUMP_DIR="${DARKMEM_DUMP_DIR:-/srv/darkmem-dumps}"

FROM=""
IDENTITY="${AGE_IDENTITY:-}"
BACKUP_FILE=""
DECRYPTED=""

while [ "$#" -gt 0 ]; do
    case "$1" in
        --from)     FROM="${2:?--from needs a destination name}"; shift 2 ;;
        --identity) IDENTITY="${2:?--identity needs a file}"; shift 2 ;;
        --help|-h)
            sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *)          BACKUP_FILE="$1"; shift ;;
    esac
done

# Covers the window before the staged cleanup() below installs its own trap;
# that one takes over and removes $DECRYPTED itself.
cleanup_decrypted() { [ -n "$DECRYPTED" ] && rm -f -- "$DECRYPTED"; }
trap cleanup_decrypted EXIT

if [ -n "$FROM" ]; then
    # The pull runs in the container because that is where the destination
    # credentials and the client libraries live. Its last stdout line is the
    # container-side path, by contract.
    echo "Pulling from destination '$FROM'..."
    if [ -n "$BACKUP_FILE" ]; then
        PULL_ARGS=(--name "$BACKUP_FILE")
    else
        PULL_ARGS=(--latest)
    fi
    CONTAINER_PATH="$(
        $COMPOSE exec -T "$APP_SERVICE" python -m app.services.backup_pull \
            --destination "$FROM" "${PULL_ARGS[@]}" --out /dumps | tail -1
    )"
    [ -n "$CONTAINER_PATH" ] || { echo "Pull produced no path." >&2; exit 1; }

    # /dumps is a bind mount, so the container path maps onto the host.
    BACKUP_FILE="$DUMP_DIR/$(basename "$CONTAINER_PATH")"
    echo "Pulled $BACKUP_FILE"
    # The dump is half a backup. Naming the exact command here rather than in
    # the runbook alone, because this is where the operator already is.
    echo
    echo "This restores the database only. For its attachments, run:"
    echo "  $COMPOSE exec -T $APP_SERVICE python -m app.services.backup_pull \\"
    echo "      --destination $FROM --paired-with $(basename "$CONTAINER_PATH") --out /dumps"
    echo "  then unpack it (docs/runbook-deployment.md, Attachments), and run"
    echo "  $COMPOSE exec -T $APP_SERVICE python -m app.services.attachment_verify"
    echo
fi

[ -n "$BACKUP_FILE" ] || { echo "usage: restore.sh BACKUP_FILE.sql.gz | --from DESTINATION" >&2; exit 1; }
[ -f "$BACKUP_FILE" ] || { echo "No such file: $BACKUP_FILE" >&2; exit 1; }

case "$BACKUP_FILE" in
    *.age)
        command -v age >/dev/null 2>&1 || {
            echo "$BACKUP_FILE is age-encrypted and 'age' is not on this host." >&2
            exit 1; }
        [ -n "$IDENTITY" ] || {
            echo "$BACKUP_FILE is age-encrypted; pass --identity FILE (or set AGE_IDENTITY)." >&2
            echo "The identity never enters the container or the database, by design." >&2
            exit 1; }
        DECRYPTED="$(mktemp "${TMPDIR:-/tmp}/darkmem-restore-XXXXXX.sql.gz")"
        echo "Decrypting on this host with $IDENTITY..."
        age -d -i "$IDENTITY" -o "$DECRYPTED" "$BACKUP_FILE"
        BACKUP_FILE="$DECRYPTED"
        ;;
esac

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
    # This trap REPLACES cleanup_decrypted above, so the plaintext copy of an
    # encrypted snapshot has to be removed here or it outlives the restore on
    # the success path -- an unencrypted database dump left in /tmp.
    [ -n "$DECRYPTED" ] && rm -f -- "$DECRYPTED"
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
# A SIGKILL between the DROP below and the RENAME after it leaves the EXIT
# trap unable to run, so this is printed before that window opens rather
# than relying on the trap to explain it afterward.
echo "If this is killed from here on, the restored data is safe in '$TEMP_DB'."
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
