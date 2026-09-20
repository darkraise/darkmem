#!/usr/bin/env bash
# One nightly restore cycle on a darkmem backup worker (spec §9.5, review B1).
#
# Runs OUTSIDE the app, on the worker host, from a systemd timer. That is not a
# style choice: this script drops and renames the database the app is serving,
# so the app process must never own the operation that destroys its own
# connection target.
#
# THE ORDER IS THE DESIGN. Verify, then swap:
#   1. pick the newest snapshot that is not already the one being served
#   2. decrypt it and check the pg_dump completion marker
#   3. replay it into a SIDE database, app still serving the old one
#   4. migrate + stamp schema_guard against the side database, privileged
#   5. grant the SELECT-only viewer role on the side database
#   6. only now: stop the app, drop, rename, start
#
# A snapshot from an older baseline fails schema_guard at step 4, the side
# database is dropped, and this exits 0 having changed nothing -- the viewer
# keeps serving what it had. That is B1's schema-mismatch answer: the surface
# must not go down for exactly the snapshots one most wants to inspect.
#
# Usage: restore-cycle.sh   (configuration is env, see the runbook)
set -euo pipefail

COMPOSE="${COMPOSE_CMD:-docker compose} -f ${WORKER_COMPOSE:-docker-compose.worker.yml}"
DUMP_DIR="${DUMP_DIR:-/srv/darkmem-dumps}"
STATE_FILE="${STATE_FILE:-/var/lib/darkmem-worker/serving}"
AGE_IDENTITY="${AGE_IDENTITY:?set AGE_IDENTITY to the private key file that decrypts the snapshots}"
OWNER_USER="${OWNER_USER:-darkmem}"
OWNER_PASSWORD="${OWNER_PASSWORD:?set OWNER_PASSWORD}"
VIEWER_PASSWORD="${VIEWER_PASSWORD:?set VIEWER_PASSWORD}"
DB="${DB_NAME:-darkmem}"
SERVICE="${POSTGRES_SERVICE:-postgres}"
APP_SERVICE="${APP_SERVICE:-darkmem}"
GRANTS="${GRANTS:-$(dirname "$0")/viewer-grants.sql}"
ATTACHMENT_STORE="${ATTACHMENT_STORE:-/srv/darkmem-attachments}"

SIDE_DB="${DB}_restore_$$"
STAGE="none"
PLAIN=""

cleanup() {
    local rc=$?
    trap - EXIT
    [ -n "$PLAIN" ] && rm -f -- "$PLAIN"
    if [ "$rc" -eq 0 ]; then
        return 0
    fi
    echo >&2
    echo "Restore cycle FAILED (exit $rc) at stage '$STAGE'." >&2
    case "$STAGE" in
        app_stopped)
            # The one window where the viewer is down with no database. Named
            # here rather than left to the operator to work out, because the
            # EXIT trap cannot run if this is SIGKILLed.
            echo "The app is STOPPED and '$DB' may not exist." >&2
            echo "The restored data is in '$SIDE_DB'. Finish by hand:" >&2
            echo "  $COMPOSE exec -T $SERVICE psql -U $OWNER_USER -d postgres -c 'ALTER DATABASE \"$SIDE_DB\" RENAME TO \"$DB\";'" >&2
            if [ -n "${WANT_GEN:-}" ]; then
                echo "  ln -s $WANT_GEN $ATTACHMENT_STORE/current.tmp && mv -T $ATTACHMENT_STORE/current.tmp $ATTACHMENT_STORE/current" >&2
            fi
            echo "  $COMPOSE start $APP_SERVICE" >&2
            ;;
        side_created|side_replayed|side_migrated|side_granted)
            echo "The viewer is untouched and still serving its previous snapshot." >&2
            echo "Drop the leftover side database to clean up:" >&2
            echo "  $COMPOSE exec -T $SERVICE psql -U $OWNER_USER -d postgres -c 'DROP DATABASE IF EXISTS \"$SIDE_DB\";'" >&2
            ;;
        *)
            echo "Nothing was changed. The viewer is still serving its previous snapshot." >&2
            ;;
    esac
}
trap cleanup EXIT

psql_owner() {
    PGPASSWORD="$OWNER_PASSWORD" $COMPOSE exec -T "$SERVICE" \
        psql -U "$OWNER_USER" -v ON_ERROR_STOP=1 "$@"
}

# ── attachment generations ────────────────────────────────────────────
#
# The viewer reads ATTACHMENTS_DIR through a relative `current` symlink. A new
# set is unpacked BESIDE the serving one and the symlink is swapped at the same
# point as the database rename, so a cycle that fails before the swap leaves
# both halves on the previous generation.

unpack_generation() {
    [ -n "$PAIRED" ] || return 0
    [ "$SERVING_GEN" = "$WANT_GEN" ] && return 0
    mkdir -p -- "$ATTACHMENT_STORE"
    local target="$ATTACHMENT_STORE/$WANT_GEN"
    local staging="$target.tmp"
    rm -rf -- "$staging"
    mkdir -p -- "$staging"
    # A pipe, never a temp file: the plaintext is the whole attachment volume
    # and $TMPDIR is tmpfs on many hosts.
    if ! age -d -i "$AGE_IDENTITY" "$DUMP_DIR/$PAIRED" | tar -xzf - -C "$staging"; then
        echo "Could not unpack $PAIRED; keeping the current attachment generation." >&2
        rm -rf -- "$staging"
        PAIRED=""; WANT_GEN=""
        return 0
    fi
    # -T because a plain mv onto an existing directory NESTS the new tree
    # inside it, which is exactly what a cycle killed after this leaves behind.
    rm -rf -- "$target"
    mv -T -- "$staging" "$target"
}

swap_generation() {
    [ -n "$WANT_GEN" ] || return 0
    # A cycle killed between the ln and the mv leaves current.tmp, and the next
    # ln would then fail under errexit -- in the window where the database has
    # already been renamed.
    rm -f -- "$ATTACHMENT_STORE/current.tmp"
    ln -s "$WANT_GEN" "$ATTACHMENT_STORE/current.tmp"
    # mv -T over a symlink is atomic; ln -sfn is not.
    mv -T -- "$ATTACHMENT_STORE/current.tmp" "$ATTACHMENT_STORE/current"
}

prune_generations() {
    [ -n "$WANT_GEN" ] || return 0
    for gen_dir in "$ATTACHMENT_STORE"/gen-*; do
        [ -e "$gen_dir" ] || continue
        [ "$(basename "$gen_dir")" = "$WANT_GEN" ] && continue
        rm -rf -- "$gen_dir"
    done
}

# ── 1. pick a snapshot ────────────────────────────────────────────────

SERVING=""
[ -f "$STATE_FILE" ] && SERVING="$(cat "$STATE_FILE")"

# Newest by name: the stamp is zero-padded and big-endian, so lexical order is
# chronological, and no mtime is trusted (a copy resets it).
NEWEST="$(ls -1 "$DUMP_DIR" 2>/dev/null | grep -E '^darkmem-app-.*\.sql\.gz\.age$' | sort -r | head -1 || true)"

if [ -z "$NEWEST" ]; then
    echo "No encrypted snapshot in $DUMP_DIR; nothing to restore."
    exit 0
fi
DUMP_STAMP="${NEWEST#darkmem-app-}"
DUMP_STAMP="${DUMP_STAMP%%.*}"

# The paired attachment set: the newest captured at or before this dump. That
# is the right one precisely because an unchanged set writes no tarball, so the
# newest at or before the dump is what was live when it was taken.
PAIRED=""
PAIRED_STAMP=""
for candidate in $(ls -1 "$DUMP_DIR" 2>/dev/null \
        | grep -E '^darkmem-app-attachments-[0-9]{8}-[0-9]{6}\.tar\.gz\.age$' \
        | sort -r); do
    stamp="${candidate#darkmem-app-attachments-}"
    stamp="${stamp%%.*}"
    if [[ "$stamp" > "$DUMP_STAMP" ]]; then
        continue
    fi
    PAIRED="$candidate"
    PAIRED_STAMP="$stamp"
    break
done
if [ -z "$PAIRED" ]; then
    echo "No attachment tarball at or before $DUMP_STAMP; attachments unchanged." >&2
fi

SERVING_GEN=""
[ -L "$ATTACHMENT_STORE/current" ] && SERVING_GEN="$(readlink "$ATTACHMENT_STORE/current")"
# A link whose generation was removed serves nothing; reading it as "already
# serving" would freeze the attachment half on a directory that is not there.
[ -n "$SERVING_GEN" ] && [ ! -d "$ATTACHMENT_STORE/$SERVING_GEN" ] && SERVING_GEN=""
WANT_GEN=""
[ -n "$PAIRED" ] && WANT_GEN="gen-$PAIRED_STAMP"

# Both halves, not just the dump. The ship order is dump then tarball, so there
# is a nightly window where this host holds the new dump and not yet the new
# set; a predicate on the dump alone would restore against the previous set,
# record the dump as served, and strand the tarball until another dump arrives.
if [ "$NEWEST" = "$SERVING" ] && { [ -z "$WANT_GEN" ] || [ "$SERVING_GEN" = "$WANT_GEN" ]; }; then
    echo "Already serving $NEWEST${WANT_GEN:+ and $WANT_GEN}; nothing to do."
    exit 0
fi

if [ "$NEWEST" = "$SERVING" ]; then
    # Only the attachment half is behind: no side database, no downtime.
    echo "Database already current; swapping attachments to $WANT_GEN."
    unpack_generation
    swap_generation
    prune_generations
    echo "Now serving $NEWEST and ${WANT_GEN:-${SERVING_GEN:-no attachment generation}}."
    exit 0
fi

echo "Restoring $NEWEST${PAIRED:+ with $PAIRED}"

# ── 2. decrypt and verify the marker ──────────────────────────────────

PLAIN="$(mktemp "${TMPDIR:-/tmp}/darkmem-restore-XXXXXX.sql.gz")"
if ! age -d -i "$AGE_IDENTITY" -o "$PLAIN" "$DUMP_DIR/$NEWEST"; then
    echo "Could not decrypt $NEWEST with $AGE_IDENTITY. Nothing changed." >&2
    exit 1
fi

# gzip of an empty stream is itself valid gzip, so integrity proves nothing
# about the dump underneath. pg_dump writes this marker last and only on a run
# that finished -- the same check scripts/restore.sh makes, for the same reason.
if ! gunzip -c "$PLAIN" 2>/dev/null | tail -c 512 \
     | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Not a complete pg_dump dump: $NEWEST. Nothing changed." >&2
    exit 1
fi

# ── 3. replay into a side database, app still serving ─────────────────

echo "Creating side database '$SIDE_DB'..."
psql_owner -d postgres \
    -c "DROP DATABASE IF EXISTS \"$SIDE_DB\";" \
    -c "CREATE DATABASE \"$SIDE_DB\" OWNER \"$OWNER_USER\";"
STAGE="side_created"

echo "Replaying into '$SIDE_DB'..."
gunzip -c "$PLAIN" | psql_owner -d "$SIDE_DB"
STAGE="side_replayed"

# ── 4. migrate + stamp, privileged, against the side database ─────────
#
# A non-zero exit here is the expected outcome for a snapshot taken against an
# older baseline: schema_guard hashes the baseline file and refuses a database
# it does not match. The side database is dropped and this exits 0, because a
# viewer that went down for exactly those snapshots would be worse than useless.

echo "Migrating and stamping '$SIDE_DB'..."
if ! $COMPOSE run --rm --no-deps \
        -e DB_USER="$OWNER_USER" -e DB_PASSWORD="$OWNER_PASSWORD" \
        -e DB_NAME="$SIDE_DB" \
        "$APP_SERVICE" sh -c "python -m alembic upgrade head && python -m app.schema_guard"; then
    echo >&2
    echo "SNAPSHOT REJECTED: $NEWEST does not match this image's baseline." >&2
    echo "The viewer keeps serving its previous snapshot; nothing was swapped." >&2
    psql_owner -d postgres -c "DROP DATABASE IF EXISTS \"$SIDE_DB\";" || true
    STAGE="none"
    exit 0
fi
STAGE="side_migrated"

# ── 5. grant the viewer role on the side database ─────────────────────

echo "Applying viewer grants to '$SIDE_DB'..."
PGPASSWORD="$OWNER_PASSWORD" $COMPOSE exec -T "$SERVICE" \
    psql -U "$OWNER_USER" -d "$SIDE_DB" -v ON_ERROR_STOP=1 \
    -v viewer_password="$VIEWER_PASSWORD" -v dbname="$SIDE_DB" \
    < "$GRANTS"
STAGE="side_granted"

# Unpacked while the viewer still serves the previous generation: a failure
# here costs nothing, and the swap below is then a symlink move.
unpack_generation

# ── 6. swap ───────────────────────────────────────────────────────────
#
# ALTER DATABASE ... RENAME needs no live connections, which is why the app
# stops here and not earlier. The receiver holds none by construction (it has
# no database at all), so it keeps accepting uploads across the swap.

echo "Swapping. Downtime starts now and lasts seconds."
echo "If this is killed from here on, the restored data is safe in '$SIDE_DB'."
$COMPOSE stop "$APP_SERVICE"
STAGE="app_stopped"

psql_owner -d postgres -c "DROP DATABASE IF EXISTS \"$DB\";"
psql_owner -d postgres -c "ALTER DATABASE \"$SIDE_DB\" RENAME TO \"$DB\";"
swap_generation
$COMPOSE start "$APP_SERVICE"
STAGE="swapped"

prune_generations

# ── 7. record what is being served ────────────────────────────────────

mkdir -p "$(dirname "$STATE_FILE")"
printf '%s\n' "$NEWEST" > "$STATE_FILE"

echo "Now serving $NEWEST."
