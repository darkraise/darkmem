# Attachment backups — design

Date: 2026-09-20. Status: revision 2, after an independent adversarial review
(13 findings, all addressed — disposition in §15). Awaiting owner approval.

Sub-project 2 of 4 of the Notion import programme
(`docs/superpowers/specs/2026-09-19-notion-import-design.md`). It implements that
spec's §3.7 and closes two items sub-project 1 carried forward
(`docs/superpowers/notes/page-attachment-storage-followups.md`).

## 1. Goal

`pg_dump` alone silently leaves out every attachment: sub-project 1 put the bytes
on a disk volume and the metadata in Postgres, and only the metadata is backed
up today. A restore therefore produces a corpus whose every image is a broken
link, and nothing reports it.

This sub-project makes the attachment set a **second artefact family** carried by
both existing producers, restorable in step with a dump, and served by the backup
worker from versioned generations.

Scope:

1. A manifest — one definition, two producers (§3).
2. `scripts/backup.sh`: a tarball stage after the dump (§4).
3. `backup_ship`: the second family, its ship decision and its retention (§5).
4. The receiver's name pattern (§6).
5. The worker's attachment store and generation swap (§7).
6. The inventory surface and the Backups tab (§8).
7. The parked row-less-file hazard in `page_attachment_cleanup` (§9).
8. Post-restore verification (§10).
9. Documentation (§11).

Out of scope: per-file incremental backup (the tarball is whole-set), restoring
attachments without restoring a database, backing up the `.staging` directory,
and any change to `page_attachments` or to the baseline — **this sub-project
contains no schema change**.

## 2. Rulings

| Question | Ruling |
|---|---|
| Change detection | A manifest hash over `(id, sha256)`, computed by Postgres |
| Producers | Both: `scripts/backup.sh` (host floor) and `backup_ship` (app, off-host) |
| Artefact | One whole-set `tar.gz` per producer, written only when the manifest changed |
| Completion proof | The archive's own entry count against the row count — an empty tarball is never renamed |
| Family separation | A second family beside dumps; `_is_snapshot` is never widened |
| Ordering within a family | By the stamp in the name, never by mtime |
| Restore pairing | The newest tarball whose stamp is ≤ the dump's stamp |
| "Destination holds it" | Listed **and** journalled shipped — a listing alone would trust a copy that failed verification |
| Worker store | A **host bind mount**, mounted `:ro` into the app |
| Worker swap | Unpack a new generation beside the serving one; swap a relative symlink |
| Inventory | Lists both families, with a per-family last outcome |
| Row-less sweep | Refuses on a bulk mismatch, and refuses outright when the table is empty |

## 3. The manifest

A single SQL scalar, so shell and Python cannot disagree about formatting,
ordering or encoding:

```sql
SELECT encode(
         sha256(convert_to(
           coalesce(string_agg(id::text || ':' || sha256, E'\n' ORDER BY id), ''),
           'UTF8')),
         'hex')
  FROM page_attachments
```

Postgres does the aggregation and the hash (`sha256(bytea)` is core since
PG11; the stack runs pg17). An empty table hashes the empty string, which is a
real value and not a null — a corpus with no attachments has a stable manifest.
The literal survives SQLAlchemy `text()` unchanged: neither `':'` inside a
quoted literal nor `::` matches its bind-parameter pattern.

New module `backend/app/services/attachment_manifest.py`:

- `MANIFEST_SQL: str` — the statement above, as one line.
- `COUNT_SQL = "SELECT count(*) FROM page_attachments"` — §4 and §5.3's
  completion check.
- `async manifest_hash(session) -> str`, `async attachment_count(session) -> int`.

`scripts/backup.sh` carries both literals. `tests/test_backup_script.py` asserts
the spellings are byte-identical to the Python constants after whitespace
collapse, so a change to one fails the build rather than drifting.

Why `(id, sha256)` and not an mtime or a count: an attachment's bytes never
change after `os.replace` (the id is the filename and there is no update path),
so the pair set changes if and only if a row was added or deleted. A count alone
would miss a delete-plus-add inside one interval.

## 4. `scripts/backup.sh` — the tarball stage

Appended after the existing dump, marker check, rename and dump prune. The
existing flow is not restructured. The whole stage runs **in a subshell with its
own `set -euo pipefail`**, because an `if ! stage; then` guard around a function
disables errexit inside it and an intermediate failure would not abort.

```
ATTACHMENT_VOLUME="${ATTACHMENT_VOLUME:-darkmem-prod_attachment_data}"
DARKMEM_IMAGE="${DARKMEM_IMAGE:-darkraise/darkmem:latest}"
DOCKER_CMD="${DOCKER_CMD:-docker}"
BACKUP_ATTACHMENTS_KEEP="${BACKUP_ATTACHMENTS_KEEP:-3}"
```

1. **Volume exists.** `$DOCKER_CMD volume inspect "$ATTACHMENT_VOLUME" >/dev/null`.
   Without this, `docker run -v NAME:/src` **creates** a missing volume and tars
   an empty one: a typo, a renamed compose project or the dev stack would produce
   a well-formed empty tarball under the canonical name, whose sidecar then
   records the real manifest so every later night skips. A missing volume is a
   hard failure of the stage.
2. **Manifest and count.** `$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB"
   -At -c "$MANIFEST_SQL"` and the same for `$COUNT_SQL`.
3. **Compare.** The newest existing `darkmem-attachments-*.tar.gz`
   **by name** (the stamp is zero-padded and big-endian, so lexical order is
   chronological; no mtime is trusted, a copy resets one) has a sidecar
   `<name>.manifest` holding exactly one line, the 64-hex hash. Equal → log the
   skip and finish. Absent sidecar or different hash → build.
4. **Build.** `$DOCKER_CMD run --rm --entrypoint tar -v "$ATTACHMENT_VOLUME:/src:ro"
   "$DARKMEM_IMAGE" -czvf - -C /src --exclude='*.part' --exclude='./.staging'
   --ignore-failed-read --warning=no-file-changed .` with stdout redirected to
   `darkmem-attachments-$STAMP.tar.gz.part` and stderr — which is where `-v`
   writes the member listing when the archive goes to stdout — captured to a
   temporary file beside it. `docker run` rather than `docker compose exec` into
   the app: the floor exists for the case where the app is down. `$STAMP` is the
   dump's own, so §7.2's pairing is satisfied by construction.
5. **Accept tar's exit 1.** "file changed as we read it" is expected against a
   live volume and must not fail the backup. Any other non-zero status fails the
   stage.
6. **Completion check.** Count the non-directory members in the captured listing.
   When the row count from step 2 is non-zero and the member count is zero, the
   stage fails without renaming and without writing a sidecar. This is the
   tarball's equivalent of the dump's completion marker, and it is what makes a
   mis-mounted or empty volume loud instead of silently permanent. A count
   *lower* than the row count is not a failure — the cleanup job may legitimately
   have unlinked a file mid-run — and is logged.
7. **Rename** the `.part`, then write the sidecar, then remove the listing file.
8. **Prune** `darkmem-attachments-*.tar.gz` **by name**, newest first,
   NUL-delimited, to `BACKUP_ATTACHMENTS_KEEP`, removing each sidecar with its
   tarball. `BACKUP_ATTACHMENTS_KEEP=0` disables pruning, matching the dump
   prune's convention. The dump glob `darkmem-*.sql.gz` cannot match a
   `.tar.gz`, and this glob cannot match a dump.

**Failure policy.** The dump is the more valuable artefact and is already on disk
by the time this stage runs, so a failure here must not unwind it. The stage
writes its reason to stderr, removes its `.part` and listing file, and leaves the
dump and its prune intact; the script then exits non-zero at the very end so the
systemd unit goes red.

## 5. `backup_ship` — the second family

### 5.1 Module split

`backup_ship.py` is already 1027 lines. New work lands in two modules:

- `app/services/attachment_manifest.py` (§3).
- `app/services/attachment_archive.py`:
  - `ATTACHMENTS_PREFIX = "darkmem-app-attachments-"`
  - `@dataclass(frozen=True) class Family: prefix: str; suffixes: tuple[str, ...]`
    with `matches(name) -> bool`, `stamp_of(name) -> str | None` (the stamp
    **token**, e.g. `"20260920-043000"`) and `stamp_datetime(name) -> datetime`
    (the display value, epoch on an unparseable name — a listing that 500s over
    one foreign file is the worse surface)
  - `DUMPS = Family("darkmem-app-", (".sql.gz", ".sql.gz.age"))`
  - `ATTACHMENTS = Family(ATTACHMENTS_PREFIX, (".tar.gz", ".tar.gz.age"))`
  - `async build_archive(dest_dir: Path, stamp: str, *, expect_rows: int) -> Path`
  - `ATTACHMENTS_STATE_KEY = "backup_ship_attachments_state"`,
    `@dataclass class ArchiveState: stamp: str; manifest_hash: str`,
    `async load_state(session)`, `async save_state(session, state)`

`backup_ship.py` keeps `ship_all`, `run_dump`, `_artifacts_for`, `encrypt` and the
four destination classes. **`_stamp_of` stays in `backup_ship` as a one-line
alias for `DUMPS.stamp_datetime`**: `tests/test_backups_inventory.py:19` imports
it, and there is no reason to churn that import.

The two families never collide: a tarball carries the `darkmem-app-` prefix but
not a `.sql.gz` suffix, so today's `_is_snapshot` already excludes it.
**`_is_snapshot` is not widened** — widening it would let tarballs, which sort
after dumps by name, take every "newest" slot and prune the dumps. It is instead
expressed as `DUMPS.matches`, and `.part` stays excluded by suffix in both
families.

### 5.2 Destination protocol

`list_snapshots` and `prune` gain a family argument on the `Destination` protocol
and on all four implementations (`LocalDestination`, `SshDestination`,
`S3Destination`, `WorkerDestination`):

```python
async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]: ...
async def prune(self, keep: int, family: Family = DUMPS) -> list[str]: ...
```

The default keeps every existing call site correct at the point of the change;
each is then updated to pass `DUMPS` explicitly.

**`S3Destination` must stop materialising objects** (programme §3.7's explicit
requirement, unmet today): `stream` reads `get_object(...)["Body"]` in fixed
chunks through `asyncio.to_thread` instead of one `.read()`, and
`read_back_sha256` hashes those chunks rather than calling `_hash_object` on the
whole body. A multi-gigabyte tarball otherwise OOM-kills a container capped at
1 GB (`docker-compose.yml`), on both the verify and the pull path. The other
three kinds already stream.

`backup_pull.pull` gains the same `family` argument, plus CLI flags
`--family {dump,attachments}` and `--paired-with NAME`, which applies §7.2's
pairing rule so an operator restoring in anger can fetch both halves from one
destination.

### 5.3 The build-and-ship decision

`build_archive` tars `settings.attachments_dir` into
`DUMP_DIR/darkmem-app-attachments-<stamp>.tar.gz`, `.part` then `os.replace`,
excluding `*.part` and `.staging`, as a `tar` subprocess (never in-process): the
work must not run on the event loop, and invariant 13's single worker makes that
a real stall otherwise. tar's exit 1 is accepted, and §4 step 6's completion
check is applied identically from the `-v` listing against `expect_rows` — a
`.part` that fails it is unlinked and `ArchiveIncomplete` is raised, so a
mis-pointed `attachments_dir` cannot produce a canonical empty artefact.

Inside `ship_all`, one run stamp is minted up front and passed to both producers:
**`run_dump` gains `stamp: str | None = None`** (it mints its own today and
returns only a `Path`), so the dump and a same-run tarball carry the identical
stamp, which is what §7.2's `A <= D` comparison needs at equality.

After the dump and before the per-destination loop:

1. `current = await manifest_hash(session)`; `state = await load_state(session)`.
2. `changed = state is None or state.manifest_hash != current`.
3. Per enabled destination, `holds` is true when **both**: that destination's
   `list_snapshots(ATTACHMENTS)` contains a name whose `ATTACHMENTS.stamp_of`
   equals `state.stamp` (stamps, not names — one destination may hold the
   plaintext where another holds the `.age`), **and** the newest
   `(destination, attachments)` journal row is a `backup_shipped` naming that
   stamp. A listing that raises counts as not holding, and the failure is caught
   per destination as everywhere else.
4. `needs[cfg.name] = changed or not holds`. If no destination needs it, no
   tarball is built at all.
5. `stamp = run_stamp if changed else state.stamp`, and the archive is built once
   under that stamp and encrypted per distinct recipient through the existing
   `_artifacts_for`.

**Why `holds` reads the journal and not only the listing.** A copy that failed
read-back verification is still listed. Without the journal half, a destination
whose tarball is corrupt is never re-shipped: the dump family self-heals only
because a fresh dump arrives nightly, and the manifest gate removes exactly that
property. The operator would see "not restorable" on the inventory with nothing
scheduled to repair it.

**Why the stamp is reused on a catch-up.** A destination that was down one night
must catch up the next. If a catch-up minted a fresh stamp, every *other*
destination would then lack that stamp and ship again the night after, forever.
Reusing the recorded stamp makes the catch-up converge, and it is also the
honest label: a tarball's stamp is when its content was captured, which is what
the pairing rule in §7.2 reads. The rebuilt bytes may differ from the original's
(tar records mtimes), so each destination verifies against the artefact this run
actually shipped it, never against a recorded hash.

State `{stamp, manifest_hash}` is written to the config row
`backup_ship_attachments_state` after the loop, only when at least one tarball
shipped and verified. It is **not** `job:backup_ship`, which is the
`config_schema`-validated row and cannot carry a string.

### 5.4 Per destination

For each enabled destination the dump is shipped, verified, journalled and pruned
exactly as today. Then, when that destination needs the tarball: ship, verify by
full read-back, journal, and prune the `ATTACHMENTS` family to
`cfg.attachments_retention_keep`. Each artefact's failure is caught and folded
into the summary independently — a tarball that fails must not mark the dump that
already landed as failed, nor skip the destinations behind it.

`DestinationConfig` gains `attachments_retention_keep: int = 3`, validated in the
same 1..3650 range as `retention_keep`.

Cleanup mirrors the dump's: the plaintext tarball is removed at the end of the
run unless some destination wanted plaintext, and the `.enc` scratch is removed
in the `finally`.

`ship_all`'s summary gains `"attachments": {"stamp": ..., "built": bool,
"shipped": int, "skipped": [names], "verify_failed": [names], "pruned": {...}}`.

**Time budget.** The attachments family gets its own
`ATTACHMENTS_SHIP_TIMEOUT_SECONDS = 7200` and
`ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS = 3600` beside the dump's 3600/900, and
the job's `max_run_seconds` (`app/main.py`, 7200 today) rises to 21600. The
arithmetic, stated so the next reader can re-derive it rather than guess: three
destinations × (dump + tarball) × (upload + full read-back) at a multi-gigabyte
set exceeds two hours, and a kill mid-verify leaves the state row unwritten and
the whole decision to re-run tomorrow. A 5 GB read-back inside 3600 s needs
about 1.5 MB/s sustained.

### 5.5 Journal

No new event type. `BACKUP_SHIPPED` and `BACKUP_VERIFY_FAILED` payloads gain
`"family": "dump" | "attachments"` and, for the attachments family, `"stamp"`
(§5.3 step 3 reads it). Without the family key the inventory's
`DISTINCT ON (destination)` would let a tarball row mask the dump's outcome for
the same destination. Existing rows are read as
`coalesce(payload->>'family', 'dump')`; the greenfield ruling does not oblige
that accommodation, and it is kept only because it is one expression in a query
an operator reads during an incident. Both writers keep ignoring `record_event`'s
boolean return: a snapshot that landed and verified must not be reported failed
because a journal row did not land.

## 6. The receiver

`SNAPSHOT_NAME` becomes two anchored alternatives rather than one loosened
pattern, so the receiver stays a two-family drop and not a general file sink:

```python
SNAPSHOT_NAME = re.compile(
    r"^darkmem-app-[A-Za-z0-9._-]+\.sql\.gz(\.age)?$"
    r"|^darkmem-app-attachments-[A-Za-z0-9._-]+\.tar\.gz(\.age)?$"
)
```

`/snapshots` then lists both families with no further change. `RECEIVER_MAX_BYTES`
(default 10 GB) now bounds the attachment set as well as the dump; the runbook
says so and says to raise it before the set approaches it.

## 7. The backup worker

### 7.1 Mount

`docker-compose.worker.yml`, service `darkmem`:

```yaml
    environment:
      - ATTACHMENTS_DIR=/app/data/attachment-store/current
    volumes:
      - repo_data:/app/data/repositories
      - ${DARKMEM_ATTACHMENT_DIR:-/srv/darkmem-attachments}:/app/data/attachment-store:ro
```

A **host bind mount**, symmetric with `/srv/darkmem-dumps`, because
`restore-cycle.sh` runs on the host and must unpack a generation and swap a
symlink without shelling into a container. `:ro` makes "the app only reads it"
structural rather than conventional — the upload route is already refused by
`refuse_when_read_only`, and this removes the filesystem capability too.

`ATTACHMENTS_DIR` points at `current`, a **relative** symlink
(`current -> gen-<stamp>`): host and container paths differ, so an absolute
target would resolve in only one of them.
`assert_attachments_dir_usable(read_only=True)` already warns instead of
refusing when the directory is missing, which is the pre-first-restore state; no
change is needed there.

The bring-up creates the directory owned by the image's uid, like
`/srv/darkmem-dumps`.

### 7.2 Pairing rule

For a chosen dump `darkmem-app-<D>.sql.gz.age`, the paired tarball is the newest
`darkmem-app-attachments-<A>.tar.gz.age` with `A <= D`. The stamp is zero-padded
and big-endian, so this is a lexical comparison and no mtime is trusted.

The rule holds because an unchanged set writes no tarball: the newest tarball at
or before the dump's stamp is normally the set that was live when the dump was
taken. Its one hole is stated as a limit in §11 rather than claimed away — when
a night's tarball fails on every destination the state does not advance, so the
next night rebuilds under a *newer* stamp and the failed night's dump pairs with
an older set than it should. `attachment_verify` (§10) is what reports the
consequence.

### 7.3 `restore-cycle.sh`

Additions to the existing script:

- **Config**: `ATTACHMENT_STORE="${ATTACHMENT_STORE:-/srv/darkmem-attachments}"`.
- **The no-op predicate covers both halves.** Today the script exits 0 at
  `NEWEST = SERVING` before anything else runs. §5.4 ships the dump before the
  tarball, so there is a nightly window in which the worker holds `D_new` and not
  yet `S_new`; a cycle that fires inside it restores `D_new` against `S_prev`,
  records `D_new`, and the next cycle's early exit strands `S_new` until another
  dump arrives. The predicate becomes "the newest dump is already serving **and**
  `readlink current` equals the generation paired with it". When only the
  attachment half is behind, the script runs an **attachments-only swap**: unpack,
  swap the symlink, drop old generations, exit — no side database, no app stop,
  no downtime.
- **Pairing** by §7.2, after the dump is chosen. No tarball found, or a decrypt or
  unpack failure → warn, keep the current generation, and **continue with the
  database restore**. A missing or corrupt attachment half must never block the
  database half; the reverse ordering would make one bad tarball stop every
  restore for as long as the manifest is unchanged.
- **Unpack before the swap window**, while the viewer still serves the previous
  generation: `age -d -i "$AGE_IDENTITY" "$DUMP_DIR/$PAIRED" | tar -xzf - -C
  "$ATTACHMENT_STORE/gen-<A>.tmp"` — a pipe, never a temporary plaintext file, so
  a multi-gigabyte set never lands in `$TMPDIR` (tmpfs on many hosts). Then
  `mv -T gen-<A>.tmp gen-<A>`, guarded by `test -d gen-<A>` — a plain `mv` onto an
  existing directory **nests** the new tree inside it, which is the state a cycle
  killed after the rename but before the swap leaves behind.
- **In the swap step, beside the database rename**: `rm -f current.tmp` first,
  then `ln -s "gen-<A>" current.tmp && mv -T current.tmp current`. `mv -T` over a
  symlink is atomic; `ln -sfn` is not. The `rm -f` matters because a cycle killed
  between the `ln` and the `mv` leaves `current.tmp`, and the next cycle's `ln -s`
  would then fail under `set -e` **inside the `app_stopped` window**, with the
  database already renamed.
- **After the swap**: remove every `gen-*` directory other than `gen-<A>`, and any
  stale `gen-*.tmp`.
- **The `app_stopped` recovery message** gains the `ln -s`/`mv -T` pair. Without
  it an operator finishing by hand restarts the app on the previous generation
  and sees broken images against restored rows.
- **State**: the serving generation is `readlink current`, not a second state
  file — one source of truth that survives losing `$STATE_FILE`.

A cycle that aborts before the swap leaves both halves on the previous
generation. A cycle killed between the database rename and the symlink swap
leaves new rows against the previous generation's files, which
`attachment_verify` (§10) reports and the next cycle repairs through the
attachments-only path.

## 8. Inventory and the Backups tab

`DestinationInventory` gains three fields:

```python
attachments_retention_keep: int
attachment_snapshots: list[SnapshotRow]
last_attachment_outcome: OutcomeRow | None
```

The route makes one extra `list_snapshots(ATTACHMENTS)` call per destination,
inside the same `try` as the dump listing, so one unreachable NAS still cannot
blank the page. `_last_outcomes` becomes `DISTINCT ON (destination, family)` over
`coalesce(payload->>'family','dump')` and returns a `(destination, family)` map.

Frontend — **three files, not two**:

- `use-backups-api.ts`: the three fields on `DestinationInventory`,
  `attachments_retention_keep` on `BackupDestination`.
- `use-backups-tab-binding.ts`: `recentOutcomes` keys its map on
  `(destination, family)`. It reads `GET /events` directly and keeps the newest
  row per destination, so without this a tarball `backup_verify_failed` overwrites
  the dump's `backup_shipped` on the destination card — the exact masking §5.5
  prevents on the inventory route.
- `backups-tab.tsx`: a number control beside the existing retention control on
  the destination form, a second snapshot list on the card, and a second outcome
  line, so an operator choosing a dump can see whether a tarball that pairs with
  it survives and verified.

## 9. The row-less-file sweep

Sub-project 1 parked this: `page_attachment_cleanup` deletes every row-less file
older than one hour, so an app booted against a freshly recreated or wrong
database while `ATTACHMENTS_DIR` points at the real volume wipes the attachments
within about eighty minutes. Restoring is exactly that scenario, so it is closed
here — with **two** guards, because neither closes it alone.

`PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA` gains `rowless_bulk_limit`, an int with
default 100 and a min of 1. `run_cleanup` takes it as a keyword argument. The
row-less arm is **skipped in full** — no file unlinked — when either holds:

1. `page_attachments` is empty and the scan found any file at all. This is the
   parked scenario's signature, and it is the guard that matters for a small
   corpus: a count threshold alone still wipes a corpus of ninety attachments.
2. `len(rowless) > rowless_bulk_limit`.

`CleanupReport` gains `rowless_skipped: int`, carried in the `job_runs` row, and
the skip logs an error naming the count, which guard fired, and
`attachment_verify` as the way to tell the three causes apart. That log line plus
the `job_runs` field is the only signal — the run's status is still ok, which is
a weak signal, stated rather than glossed.

The threshold is a plain count rather than a ratio, but **not** because a crash
can only ever leave one or two files: the programme's import (§4.1) moves every
staged attachment and then commits once, so an import of a large export that
fails between the moves and the commit leaves hundreds of row-less files at once.
That is a real producer of a large set, and it is why the error log routes the
operator to `attachment_verify` rather than telling them to raise the limit. An
operator who has confirmed a genuine backlog raises the value for one run.

The unreferenced-rows arm, the `.part` arm and the staging arm are unaffected.

## 10. Post-restore verification

`app/services/attachment_verify.py` with a `__main__`, following
`backup_pull`'s precedent. The programme spec named `scripts/verify_attachments.py`;
that path cannot work, because the image copies only `app/`, `migrations/`,
`alembic.ini`, `entrypoint.sh` and the built `web/`, and the check needs both the
database and the volume. **This is a deliberate deviation from §3.7.**

```
docker compose exec darkmem python -m app.services.attachment_verify
```

Reports, in two sections: rows whose file is missing (the damaging direction — a
dump newer than its tarball, a tarball that never paired, or a cycle killed
between the database rename and the symlink swap) and files with no row
(harmless, swept by the cleanup job unless §9's guards hold them). Prints counts
and up to twenty ids per section. Exit 0 when both are empty, 1 otherwise, so an
operator can chain it after a restore. Read-only: it opens no write transaction
and unlinks nothing.

## 11. Documentation

- `docs/runbook-deployment.md`: restore the dump, then the paired tarball by §7.2;
  run `attachment_verify` after any restore; and **three** stated limits — 14
  dumps against 3 tarballs, so an old dump may pair with no surviving tarball; a
  cleanup that deletes a row between the dump and the tar leaves that dump one row
  without a file; and a night whose tarball failed on every destination leaves its
  dump pairing with an older set than it should (§7.2).
- `scripts/restore.sh`: after a successful `--from` pull it prints the exact
  `backup_pull --family attachments --paired-with <name>` command for the other
  half. The tab offers `restore.sh --from X --latest` as a copyable command
  (`backups-tab.tsx`), and after this sub-project that command restores half a
  backup; the reminder is where the operator already is.
- `docs/runbook-backup-worker.md`: the attachment bind mount and its ownership, the
  generation layout, the attachments-only swap, what a missing tarball does, and
  `RECEIVER_MAX_BYTES`.
- `CLAUDE.md`'s Backups bullet: the second artefact family on both producers, the
  pairing rule, `BACKUP_ATTACHMENTS_KEEP` and `attachments_retention_keep` both
  defaulting to 3, and the worker's generations. The job roster count does not
  change — this sub-project registers no job.

## 12. Testing

| Area | What is asserted |
|---|---|
| `test_backup_script.py` | Manifest and count SQL match the Python constants; the volume-inspect guard refuses a missing volume; an empty archive against a non-zero row count fails without renaming; the glob, excludes, `.part`-then-`mv`, sidecar content, accepted tar exit 1, name-ordered prune, `KEEP=0`, prune-glob disjointness, and that a stage failure leaves the dump and its prune intact |
| `test_backup_ship.py` | `DUMPS`/`ATTACHMENTS` classify every artefact name including `.part` and a foreign prefix; `stamp_of` returns the token and `stamp_datetime` the display value; prune of one family never deletes the other; the build decision over changed / unchanged-and-complete / unchanged-with-one-destination-behind / listed-but-verify-failed; stamp reuse converging over three runs and three destinations; `run_dump(stamp=...)`; per-artefact failure isolation; state written only after a verified ship; the S3 chunked stream and chunked read-back |
| `test_attachment_manifest.py` | Empty table, one row, order independence of insert order, a delete-plus-add changing the hash |
| `test_worker_receiver.py` | Both families accepted, `..`, separators, a `.part` and a foreign prefix refused; `/snapshots` lists both |
| `test_deployment_artifact.py` | The worker compose's bind mount, `:ro` and `ATTACHMENTS_DIR`; the three-compose worker-count and `--no-proxy-headers` guards still pass; and the restore-cycle arms extend the **existing behavioural harness** in this file (`_run_cycle`, stub `age` on `PATH`) rather than a new one — with `ATTACHMENT_STORE` pointed into `tmp_path` and stub `tar`/`readlink` coverage of the pairing, the unpack-before-swap order, `mv -T` (not `ln -sfn`), the `rm -f current.tmp` re-entry, the attachments-only swap, and old-generation removal |
| `test_page_attachment_cleanup.py` | At the limit deletes, one past it skips whole and reports; an empty table with files present skips whatever the count; the other three arms unaffected |
| `test_attachment_verify.py` | Both directions, exit codes |
| `test_backups_inventory.py` | Both families listed; a per-family last outcome; a tarball row not masking a dump row; one unreachable destination not blanking the page |
| `backups.test.tsx` | The new fields and control render; outcomes keyed per family; a destination with dumps and no tarballs |

Two harness notes an implementer needs before writing the first test.
`test_backup_script.py`'s stub compose answers every invocation with the dump
body, so it must learn to dispatch on argv — `pg_dump` returns the body, `psql`
returns a hash or a count — or the "manifest" is multi-line garbage. And
`test_a_successful_dump_lands_under_the_retention_name` asserts
`list(dest.iterdir()) == [dump]`, which the tarball and its sidecar violate; that
assertion changes to a dump-glob comparison.

Not tested, and stated rather than discovered: there is no live sshd or S3 fixture
on this host, so the ssh and s3 destinations are proven on argv, the pinned host
key, the `.part` discipline and the family-scoped prune only. A real transfer is an
operator bring-up step. The worker's restore cycle runs against stubs; the machine
it runs on is not part of this repo's gate.

## 13. Accepted costs

- Peak disk in `/dumps` during a run is the plaintext tarball, **plus a copy of
  it per distinct recipient** (`_artifacts_for` copies before encrypting), plus
  one `.age` per recipient. At a multi-gigabyte set with two recipients that is
  roughly five times the set on the same disk the dumps use. Both producers keep
  3 tarballs.
- Tarring a live volume can race the cleanup job. `--ignore-failed-read` and the
  accepted exit 1 cover it; the loser is one file in one tarball, and the next
  manifest change rewrites it. A member count below the row count is logged, not
  failed, for this reason.
- 14 dumps against 3 tarballs means an old dump may pair with no surviving
  tarball. Restoring it serves rows whose files are gone, which
  `attachment_verify` reports.
- A whole-set tarball rewrites every byte when one file is added. Incremental
  backup is out of scope; the manifest gate is what keeps an unchanged set from
  being copied nightly.

## 14. Deploy

This sub-project changes no schema, but the branch inherits sub-project 1's
regenerated `0001_baseline.py`, so the eventual deploy is still the
drop/recreate/re-seed the owner has not yet authorised
(`docs/runbook-deployment.md`, CLAUDE.md "The schema is ONE revision"). No task
deploys, builds `darkraise/darkmem:latest` or touches the `:8000` instance.

## 15. Review disposition

Revision 2 addresses an independent adversarial review of revision 1. What it
changed, by that review's numbering:

| # | Finding | Where addressed |
|---|---|---|
| 1 | `docker run -v NAME` auto-creates a missing volume → a silent empty tarball the manifest gate then treats as current forever | §4 steps 1 and 6; §5.3's `expect_rows` |
| 2 | A tarball that failed verification is listed, so it is never re-shipped | §5.3 step 3 (journal-backed `holds`); §7.3 (a bad tarball no longer blocks the database restore) |
| 3 | `holds` compared a `datetime` to a `str`, so no destination ever held and the manifest gate was defeated | §5.1 (`stamp_of` → `str`, `stamp_datetime` → `datetime`) |
| 4 | Programme §3.7's S3 streaming requirement was dropped | §5.2 |
| 5 | The worker's `NEWEST = SERVING` early exit precedes the pairing, stranding a late tarball | §7.3 (both-halves predicate, attachments-only swap) |
| 6 | §9's threshold rested on a false premise and missed small corpora | §9 (the empty-table guard; the import-failure producer named) |
| 7 | The symlink swap was not crash-safe on re-entry | §7.3 (`rm -f current.tmp`, `mv -T` with `test -d`, the recovery message) |
| 8 | The tab's own outcome binding is keyed on destination alone | §8 (third frontend file) |
| 9 | No `docker` seam for the tests, and an existing assertion breaks | §4 (`DOCKER_CMD`); §12's harness notes |
| 10 | The pairing rule's correctness claim was overstated | §7.2 and §11's third limit |
| 11 | Run budget and transfer timeouts unaddressed for a multi-gigabyte artefact | §5.4 |
| 12 | Decrypting to `$TMPDIR` on the worker | §7.3 (the `age \| tar` pipe) |
| 13 | Under-specifications: `run_dump`'s stamp, `_stamp_of`'s importer, name-versus-mtime ordering, `KEEP=0`, the `set -e` subshell, peak disk, `restore.sh`'s half-backup command, the duplicate restore-cycle harness, §9's weak signal | §4, §5.1, §5.3, §9, §11, §12, §13 |

The review found no CLAUDE.md invariant violation, and confirmed the revision-1
claims that `_is_snapshot` already excludes `.tar.gz`, that
`assert_attachments_dir_usable(read_only=True)` warns rather than refuses, that
the image copies no `scripts/`, and that the two family predicates are
prefix-and-suffix disjoint.
