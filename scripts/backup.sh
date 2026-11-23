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
# would not: this database's nightly dumps are about 250 MB, and were once
# as small as 14 KB.
if ! gunzip -c "$PART" | tail -c 512 | grep -F 'PostgreSQL database dump complete' >/dev/null; then
    echo "Incomplete dump: no pg_dump completion marker. Nothing written to $OUT." >&2
    exit 1
fi

# A complete dump of the wrong database (another stack's, an empty one) passes
# the marker above, and BACKUP_KEEP such nights would prune every real dump.
# pipefail is off for these reads: grep -m1 stops at the first match, and gzip
# then fails writing to the closed pipe.
MISSING=()
for marker in 'CREATE TABLE public.memories (' 'COPY public.alembic_version '; do
    if ! (set +o pipefail; gzip -dc "$PART" 2>/dev/null | grep -m1 -F -- "$marker" >/dev/null); then
        MISSING+=("$marker")
    fi
done
if [ "${#MISSING[@]}" -gt 0 ]; then
    mv -- "$PART" "$OUT.suspect"
    printf "Suspect dump: no '%s' line in it.\n" "${MISSING[@]}" >&2
    echo "Not a darkmem database dump. Kept as $OUT.suspect; no dump pruned." >&2
    # Suspects take their own glob, so this can never reach a real dump; a
    # run of bad nights would otherwise fill the disk with ~250 MB files.
    SUSPECT_KEEP=3
    mapfile -d '' -t SUSPECTS < <(
        find "$DEST_DIR" -maxdepth 1 -name 'darkmem-*.sql.gz.suspect' -type f -printf '%T@ %p\0' \
        | sort -zrn | cut -z -d' ' -f2-
    )
    if [ "${#SUSPECTS[@]}" -gt "$SUSPECT_KEEP" ]; then
        for old_suspect in "${SUSPECTS[@]:$SUSPECT_KEEP}"; do
            rm -f -- "$old_suspect"
            echo "Pruned $old_suspect (suspects: newest $SUSPECT_KEEP)" >&2
        done
    fi
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

# ── Attachments ───────────────────────────────────────────────────────
#
# pg_dump alone leaves out every attachment, so the volume is backed up as a
# second artefact family -- a whole-set tarball, written only when the set
# changed, so an unchanged multi-gigabyte volume is not copied nightly.
#
# The dump above is already on disk and already pruned, and nothing here may
# unwind it. The stage runs in a subshell with its own errexit and reports
# through its exit status, which is read at the very end -- with this shell's
# errexit switched off for the one call, for the reason given there.
ATTACHMENT_VOLUME="${ATTACHMENT_VOLUME:-darkmem-prod_attachment_data}"
DARKMEM_IMAGE="${DARKMEM_IMAGE:-darkraise/darkmem:latest}"
DOCKER_CMD="${DOCKER_CMD:-docker}"
KEEP_TARS="${BACKUP_ATTACHMENTS_KEEP:-3}"

# Identical to app/services/attachment_manifest.py's constants, and a test
# asserts that. Postgres does the aggregation and the hash so the shell and
# the app producer cannot disagree about ordering or encoding.
MANIFEST_SQL="SELECT encode(sha256(convert_to(coalesce(string_agg(id::text || ':' || sha256, E'\n' ORDER BY id), ''), 'UTF8')), 'hex') FROM page_attachments"
COUNT_SQL="SELECT count(*) FROM page_attachments"

TAR_OUT="$DEST_DIR/darkmem-attachments-$STAMP.tar.gz"
TAR_PART="$TAR_OUT.part"
TAR_LIST="$TAR_OUT.list"

attachment_stage() (
    set -euo pipefail
    trap 'rm -f -- "$TAR_PART" "$TAR_LIST"' EXIT

    # `docker run -v NAME:/src` CREATES a missing volume. A typo, a renamed
    # compose project or the dev stack would tar an empty one, exit 0, and
    # leave a well-formed empty archive under the canonical name whose sidecar
    # records the real manifest -- after which every later night compares equal
    # and skips, green, forever.
    $DOCKER_CMD volume inspect "$ATTACHMENT_VOLUME" >/dev/null

    MANIFEST="$($COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -At -c "$MANIFEST_SQL" | tr -d '\r')"
    ROWS="$($COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -At -c "$COUNT_SQL" | tr -d '\r')"

    # Newest by NAME: the stamp is zero-padded and big-endian, so lexical
    # order is chronological, and a copy that reset an mtime cannot reorder it.
    NEWEST_TAR="$(find "$DEST_DIR" -maxdepth 1 -name 'darkmem-attachments-*.tar.gz' -type f -printf '%f\n' | sort -r | head -1 || true)"
    if [ -n "$NEWEST_TAR" ] && [ -f "$DEST_DIR/$NEWEST_TAR.manifest" ] \
       && [ "$(cat "$DEST_DIR/$NEWEST_TAR.manifest")" = "$MANIFEST" ]; then
        echo "Attachment set unchanged since $NEWEST_TAR; no tarball written."
        exit 0
    fi

    echo "Archiving attachment volume '$ATTACHMENT_VOLUME' -> $TAR_OUT"
    # -v so tar itself reports its members: counting them here costs nothing,
    # where reading a multi-gigabyte archive back would cost the whole
    # decompression. The listing goes to stderr because the archive is stdout.
    #
    # `|| status=$?` and NOT `if ! ...; then status=$?`: inside the body of a
    # negated condition, `$?` is the status of the *negation*, which is 0
    # exactly when the command failed (ShellCheck SC2319). That spelling would
    # read every tar failure as 0, refuse the accepted exit 1 along with the
    # rest, and fail this stage on every run against a live volume. The `||`
    # also keeps the subshell's errexit from killing the stage before the
    # status is inspected.
    status=0
    $DOCKER_CMD run --rm --entrypoint tar \
        -v "$ATTACHMENT_VOLUME:/src:ro" "$DARKMEM_IMAGE" \
        -czvf - -C /src --exclude='*.part' --exclude='./.staging' \
        --ignore-failed-read --warning=no-file-changed . \
        > "$TAR_PART" 2> "$TAR_LIST" || status=$?

    # 1 is "file changed as we read it", expected against a live volume the
    # cleanup job may be unlinking from. Anything else is a failure.
    if [ "$status" -ne 0 ] && [ "$status" -ne 1 ]; then
        echo "tar exited $status" >&2
        tail -5 "$TAR_LIST" >&2
        exit 1
    fi

    # Members are the lines tar itself lists, which under `-C /src .` all
    # begin with `./`; directories end in '/'. The same stream carries tar's
    # DIAGNOSTICS (`tar: ./x: Cannot open ...`, one per file that
    # --ignore-failed-read skipped), and counting those would score one
    # archived member per file that failed to be archived -- exactly inverse
    # to the signal this check exists for.
    MEMBERS="$(grep -c '^\./.*[^/]$' "$TAR_LIST" || true)"
    if [ "$ROWS" -gt 0 ] && [ "$MEMBERS" -eq 0 ]; then
        echo "Archive holds no files while page_attachments holds $ROWS rows." >&2
        echo "Volume '$ATTACHMENT_VOLUME' is empty or not the right one. Nothing written." >&2
        exit 1
    fi
    if [ "$MEMBERS" -lt "$ROWS" ]; then
        echo "Note: archived $MEMBERS files against $ROWS rows (one may have been collected mid-run)."
    fi

    trap - EXIT
    rm -f -- "$TAR_LIST"
    mv -- "$TAR_PART" "$TAR_OUT"
    printf '%s\n' "$MANIFEST" > "$TAR_OUT.manifest"
    echo "Attachments backed up: $TAR_OUT ($(du -h "$TAR_OUT" | cut -f1))"

    # Its own glob and its own keep. The dump glob 'darkmem-*.sql.gz' cannot
    # match a .tar.gz, and this one cannot match a dump.
    if [ "$KEEP_TARS" -gt 0 ]; then
        mapfile -d '' -t TARS < <(
            find "$DEST_DIR" -maxdepth 1 -name 'darkmem-attachments-*.tar.gz' -type f -printf '%f\0' \
            | sort -zr
        )
        if [ "${#TARS[@]}" -gt "$KEEP_TARS" ]; then
            for old_tar in "${TARS[@]:$KEEP_TARS}"; do
                rm -f -- "$DEST_DIR/$old_tar" "$DEST_DIR/$old_tar.manifest"
                echo "Pruned $old_tar (retention: newest $KEEP_TARS)"
            done
        fi
    fi
)

# NOT `if ! attachment_stage`: a function called from an `if`, `!`, `&&` or
# `||` runs in a context where errexit is ignored, and bash documents that a
# `set -e` issued INSIDE such a context has no effect until it completes --
# the subshell body does not escape that rule. Errexit is switched off in this
# shell for the one call instead, so the stage's own `set -e` is the live one,
# and its status is read back here.
set +e
attachment_stage
attachment_status=$?
set -e
if [ "$attachment_status" -ne 0 ]; then
    echo "Attachment backup FAILED. The database dump above is intact." >&2
    exit 1
fi
