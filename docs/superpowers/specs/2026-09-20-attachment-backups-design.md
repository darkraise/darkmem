# Attachment backups — design

Date: 2026-09-20. Status: approved in chat, awaiting spec review.

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
| Family separation | A second family beside dumps; `_is_snapshot` is never widened |
| Restore pairing | The newest tarball whose stamp is ≤ the dump's stamp |
| Worker store | A **host bind mount**, mounted `:ro` into the app |
| Worker swap | Unpack a new generation beside the serving one; swap a relative symlink |
| Inventory | Lists both families, with a per-family last outcome |
| Row-less sweep | Refuses on a bulk mismatch rather than wiping a restored volume |

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

New module `backend/app/services/attachment_manifest.py`:

- `MANIFEST_SQL: str` — the statement above, as one line.
- `async manifest_hash(session) -> str`.

`scripts/backup.sh` carries the same literal. `tests/test_backup_script.py`
asserts the two spellings are byte-identical after whitespace collapse, so a
change to one fails the build rather than drifting.

Why `(id, sha256)` and not an mtime or a count: an attachment's bytes never
change after `os.replace` (the id is the filename and there is no update path),
so the pair set changes if and only if a row was added or deleted. A count alone
would miss a delete-plus-add inside one interval.

## 4. `scripts/backup.sh` — the tarball stage

Appended after the existing dump, marker check, rename and dump prune. The
existing flow is not restructured.

```
ATTACHMENT_VOLUME="${ATTACHMENT_VOLUME:-darkmem-prod_attachment_data}"
DARKMEM_IMAGE="${DARKMEM_IMAGE:-darkraise/darkmem:latest}"
BACKUP_ATTACHMENTS_KEEP="${BACKUP_ATTACHMENTS_KEEP:-3}"
```

1. **Manifest.** `$COMPOSE exec -T "$SERVICE" psql -U "$USER" -d "$DB" -At -c "$MANIFEST_SQL"`.
2. **Compare.** The newest existing `darkmem-attachments-*.tar.gz` in `$DEST_DIR`
   has a sidecar `<same name>.manifest` holding one hash. Equal → log the skip and
   finish. Absent sidecar or different hash → build.
3. **Build.** `docker run --rm --entrypoint tar -v "$ATTACHMENT_VOLUME:/src:ro"
   "$DARKMEM_IMAGE" -czf - -C /src --exclude='*.part' --exclude='./.staging'
   --ignore-failed-read --warning=no-file-changed .` redirected to
   `darkmem-attachments-$STAMP.tar.gz.part`. `docker run` rather than
   `docker compose exec` into the app: the floor exists for the case where the app
   is down. `$STAMP` is the dump's own, so the pairing rule is satisfied by
   construction.
4. **Accept tar's exit 1.** "file changed as we read it" is expected against a live
   volume and must not fail the backup under `set -euo pipefail`. Any other
   non-zero status is a failure.
5. **Rename** the `.part`, then write the sidecar.
6. **Prune** `darkmem-attachments-*.tar.gz` to `BACKUP_ATTACHMENTS_KEEP`, newest
   first, NUL-delimited like the dump prune, removing each sidecar with its
   tarball. The dump glob `darkmem-*.sql.gz` cannot match a `.tar.gz`, and this
   glob cannot match a dump.

**Failure policy.** The dump is the more valuable artefact and is already on disk
by the time this stage runs, so a tar or manifest failure must not unwind it. The
stage runs guarded: on failure it writes the reason to stderr, removes its
`.part`, leaves the dump and its prune intact, and the script exits non-zero at
the very end so the systemd unit goes red.

## 5. `backup_ship` — the second family

### 5.1 Module split

`backup_ship.py` is already 1027 lines. New work lands in two modules:

- `app/services/attachment_manifest.py` (§3).
- `app/services/attachment_archive.py`:
  - `ATTACHMENTS_PREFIX = "darkmem-app-attachments-"`
  - `@dataclass(frozen=True) class Family: prefix: str; suffixes: tuple[str, ...]`
    with `matches(name) -> bool` and `stamp_of(name) -> datetime`
  - `DUMPS = Family("darkmem-app-", (".sql.gz", ".sql.gz.age"))`
  - `ATTACHMENTS = Family(ATTACHMENTS_PREFIX, (".tar.gz", ".tar.gz.age"))`
  - `async build_archive(dest_dir: Path, stamp: str) -> Path`
  - `ATTACHMENTS_STATE_KEY = "backup_ship_attachments_state"`,
    `async load_state(session) -> ArchiveState | None`, `async save_state(session, state)`

`backup_ship.py` keeps `ship_all`, `run_dump`, `_artifacts_for`, `encrypt` and the
four destination classes.

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
each is then updated to pass `DUMPS` explicitly. `_stamp_of` moves onto `Family`
and keeps its epoch fallback for an unparseable name (it is a display field, and
a listing that 500s over one foreign file is the worse surface).

`backup_pull.pull` gains the same `family` argument, plus CLI flags
`--family {dump,attachments}` and `--paired-with NAME`, which applies §7's pairing
rule so an operator restoring in anger can fetch both halves from one destination.

### 5.3 The build-and-ship decision

`build_archive` tars `settings.attachments_dir` into
`DUMP_DIR/darkmem-app-attachments-<stamp>.tar.gz`, `.part` then `os.replace`,
excluding `*.part` and `.staging`, as a `tar` subprocess (never in-process): the
work must not run on the event loop, and invariant 13's single worker makes that
a real stall otherwise. tar's exit 1 is accepted exactly as in §4.

Inside `ship_all`, after the dump and before the per-destination loop:

1. `current = await manifest_hash(session)`; `state = await load_state(session)`.
2. `changed = state is None or state.manifest_hash != current`.
3. Per enabled destination, `holds = any(ATTACHMENTS.stamp_of(s.name) == state.stamp
   for s in await destination.list_snapshots(ATTACHMENTS))`, comparing stamps rather
   than names because one destination may hold the plaintext where another holds the
   `.age`. `needs[cfg.name] = changed or not holds`; a listing that raises counts as
   not holding, and the failure is caught per destination as everywhere else.
4. If no destination needs it, no tarball is built at all.
5. Otherwise `stamp = run_stamp if changed else state.stamp`, and the archive is
   built once under that stamp and encrypted per distinct recipient through the
   existing `_artifacts_for`.

**Why the stamp is reused on a catch-up.** A destination that was down one night
must catch up the next. If a catch-up minted a fresh stamp, every *other*
destination would then lack that stamp and ship again the night after, forever.
Reusing the recorded stamp makes the catch-up converge, and it is also the
honest label: a tarball's stamp is when its content was captured, which is what
the pairing rule in §7 reads. The rebuilt bytes may differ from the original's
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

### 5.5 Journal

No new event type. `BACKUP_SHIPPED` and `BACKUP_VERIFY_FAILED` payloads gain
`"family": "dump" | "attachments"`. Without it the inventory's
`DISTINCT ON (destination)` would let a tarball row mask the dump's outcome for
the same destination. Existing rows are read as
`coalesce(payload->>'family', 'dump')`. Both writers keep ignoring
`record_event`'s boolean return: a snapshot that landed and verified must not be
reported failed because a journal row did not land.

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

The rule is correct precisely because an unchanged set writes no tarball: the
newest tarball at or before the dump's stamp is the set that was live when the
dump was taken.

### 7.3 `restore-cycle.sh`

Additions, in order, to the existing script:

- **Config**: `ATTACHMENT_STORE="${ATTACHMENT_STORE:-/srv/darkmem-attachments}"`.
- **After picking the dump (§1)**: pick the paired tarball by §7.2. None found →
  warn and continue with the database restore; the current generation keeps
  serving.
- **Before the swap window**, alongside the side-database work: if
  `readlink "$ATTACHMENT_STORE/current"` already equals `gen-<A>`, skip. Otherwise
  decrypt with `$AGE_IDENTITY` and unpack into `$ATTACHMENT_STORE/gen-<A>.tmp`,
  then `mv` it to `gen-<A>`. The viewer is still serving the previous generation
  throughout, and a failure here exits through the existing cleanup with nothing
  swapped.
- **In step 6, beside the database rename**:
  `ln -s "gen-<A>" "$ATTACHMENT_STORE/current.tmp" && mv -T "$ATTACHMENT_STORE/current.tmp" "$ATTACHMENT_STORE/current"`.
  `mv -T` over a symlink is atomic; `ln -sfn` is not.
- **After the swap**: remove every `gen-*` directory other than `gen-<A>`, and any
  stale `gen-*.tmp`.
- **State**: the serving generation is `readlink current`, not a second state
  file — one source of truth that survives losing `$STATE_FILE`.

A cycle that aborts before the swap leaves both halves on the previous
generation. A cycle killed between the database rename and the symlink swap
leaves new rows against the previous generation's files, which
`attachment_verify` (§10) reports and which the next cycle repairs.

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

Frontend (`use-backups-api.ts`, `backups-tab.tsx`): the three fields on
`DestinationInventory`, `attachments_retention_keep` on `BackupDestination`, a
number control beside the existing retention control on the destination form, and
a second snapshot list on the destination card labelled so an operator choosing a
dump can see whether a tarball that pairs with it survives. `backups.test.tsx`
covers the new fields and a destination that lists dumps but no tarballs.

## 9. The row-less-file sweep

Sub-project 1 parked this: `page_attachment_cleanup` deletes every row-less file
older than one hour, so an app booted against a freshly recreated or wrong
database while `ATTACHMENTS_DIR` points at the real volume wipes the attachments
within about eighty minutes. Restoring is exactly that scenario, so it is closed
here.

`PAGE_ATTACHMENT_CLEANUP_CONFIG_SCHEMA` gains `rowless_bulk_limit`, an int with
default 100 and a min of 1. `run_cleanup` takes it as a keyword argument. When
`len(rowless) > rowless_bulk_limit` the arm is **skipped in full** — no file is
unlinked — and logs an error naming the count, the limit, and the two causes
worth checking (a restored volume against an unrestored database, or a
mis-pointed `ATTACHMENTS_DIR`). `CleanupReport` gains
`rowless_skipped: int` so the `job_runs` row records it.

The threshold is a plain count, not a ratio: the crash this arm exists for —
between `os.replace` and commit — leaves one or two files, never a hundred, and a
genuine accumulation past a hundred is itself worth a human look. An operator who
has confirmed a real backlog raises the config value for one run.

The unreferenced-rows arm, the `.part` arm and the staging arm are unaffected.

## 10. Post-restore verification

`app/services/attachment_verify.py` with a `__main__`, following
`backup_pull`'s precedent. The programme spec named `scripts/verify_attachments.py`;
that path cannot work, because the image copies only `app/`, `migrations/`,
`alembic.ini` and `entrypoint.sh`, and the check needs both the database and the
volume. **This is a deliberate deviation from §3.7.**

```
docker compose exec darkmem python -m app.services.attachment_verify
```

Reports, in two sections: rows whose file is missing (the damaging direction — a
dump newer than its tarball, or a tarball that never paired) and files with no row
(harmless, swept by the cleanup job unless §9's limit holds them). Prints counts
and up to twenty ids per section. Exit 0 when both are empty, 1 otherwise, so an
operator can chain it after a restore. Read-only: it opens no write transaction
and unlinks nothing.

## 11. Documentation

- `docs/runbook-deployment.md`: restore the dump, then the paired tarball by §7.2;
  run `attachment_verify` after any restore; the two stated limits (14 dumps
  against 3 tarballs, so an old dump may pair with no surviving tarball; and a
  cleanup that deletes a row between the dump and the tar leaves that dump one row
  without a file).
- `docs/runbook-backup-worker.md`: the attachment bind mount and its ownership, the
  generation layout, what a missing tarball does, and `RECEIVER_MAX_BYTES`.
- `CLAUDE.md`'s Backups bullet: the second artefact family on both producers, the
  pairing rule, `BACKUP_ATTACHMENTS_KEEP` and `attachments_retention_keep` both
  defaulting to 3, and the worker's generations. The job roster count does not
  change — this sub-project registers no job.

## 12. Testing

| Area | What is asserted |
|---|---|
| `test_backup_script.py` | The manifest SQL matches `MANIFEST_SQL`; the tarball stage's glob, excludes, `.part`-then-`mv`, sidecar write, accepted tar exit 1, prune glob disjointness, and that a tar failure leaves the dump and its prune intact |
| `test_backup_ship.py` | `DUMPS`/`ATTACHMENTS` classify every artefact name including `.part` and a foreign prefix; prune of one family never deletes the other; the build decision (changed, unchanged-and-complete, unchanged-with-one-destination-behind); stamp reuse on catch-up and convergence over two runs; per-artefact failure isolation; state row written only after a verified ship |
| `test_attachment_manifest.py` | Empty table, one row, order independence of insert order, a delete-plus-add changing the hash |
| `test_worker_receiver.py` | Both families accepted, `..`, separators, a `.part` and a foreign prefix refused; `/snapshots` lists both |
| `test_deployment_artifact.py` | The worker compose's bind mount, `:ro`, `ATTACHMENTS_DIR`; the three-compose worker-count and `--no-proxy-headers` guards still pass |
| `test_worker_restore_cycle.py` (script text) | Pairing predicate, unpack-before-swap ordering, `mv -T` (not `ln -sfn`), old-generation removal after the swap |
| `test_page_attachment_cleanup.py` | At the limit deletes, one past it skips whole and reports; the other three arms unaffected |
| `test_attachment_verify.py` | Both directions, exit codes |
| `test_backups_inventory.py` | Both families listed; a per-family last outcome; a tarball row not masking a dump row; one unreachable destination not blanking the page |
| `backups.test.tsx` | The new fields and control render; a destination with dumps and no tarballs |

Not tested, and stated rather than discovered: there is no live sshd or S3 fixture
on this host, so the ssh and s3 destinations are proven on argv, the pinned host
key, the `.part` discipline and the family-scoped prune only. A real transfer is an
operator bring-up step. The worker's restore cycle is likewise asserted as script
text; the machine it runs on is not part of this repo's gate.

## 13. Accepted costs

- A multi-gigabyte tarball, plus one encrypted copy per distinct recipient,
  transits `/dumps` — the same disk the dumps use. Sized against today's ~250 MB
  dumps, the attachment set is the larger risk; both producers keep 3.
- Tarring a live volume can race the cleanup job. `--ignore-failed-read` and the
  accepted exit 1 cover it; the loser is one file in one tarball, and the next
  manifest change rewrites it.
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
