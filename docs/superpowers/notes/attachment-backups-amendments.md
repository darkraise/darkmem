# Attachment backups — plan amendments

The 16 amendments made to `docs/superpowers/plans/2026-09-20-attachment-backups.md` while it ran (A1–A4 Task 2, A5–A7 and A10–A13 Task 7, A8 Task 3, A9 header, A14 Task 16, A15–A16 Task 13). The plan file on disk is the original text; where it differs from an entry here, the entry is what was built. Kept because the ledger that recorded them is deleted after the merge.

## A1 — Task 2
Reason: the new diagnostics test needs `socket`, which the test file does not import.
Cost if wrong: `NameError` in one test; caught on the first run of Step 4.
### Old
````text
import tarfile
from datetime import timezone
from pathlib import Path
````
### New
````text
import socket
import tarfile
from datetime import timezone
from pathlib import Path
````

## A2 — Task 2
Reason: the builder now writes a second temporary file, so the success test must assert no leftovers at all, not only no `.part`.
Cost if wrong: a stray `.index` file accumulates in the dump directory an operator reads; it matches neither family, so no prune is affected.
### Old
````text
    assert members == {"ab/abcd"}
    assert not list(tmp_path.glob("*.part"))
````
### New
````text
    assert members == {"ab/abcd"}
    # Neither the `.part` nor the listing file survives: the listing has a file
    # of its own so stderr can stay diagnostics-only, and a dump directory an
    # operator reads is the wrong place to leave it.
    assert {p.name for p in tmp_path.iterdir()} == {"attachments", out.name}
````

## A3 — Task 2
Reason: nothing pins the property the completeness guard rests on — that tar's diagnostics are not counted as archived files.
Cost if wrong: the guard can be re-broken by anyone who folds the two streams back together, with no test to say so.
### Old
````text
    out = await build_archive(tmp_path, "20260920-043000", expect_rows=0)
    assert out.is_file()
````
### New
````text
    out = await build_archive(tmp_path, "20260920-043000", expect_rows=0)
    assert out.is_file()


async def test_a_tar_diagnostic_is_not_counted_as_a_member(tmp_path, monkeypatch):
    """stderr carries tar's diagnostics; the member listing has its own file.

    A unix socket is the one entry tar refuses deterministically for every
    user, root included -- these tests run as root, where a `chmod 000` file is
    still readable, so it cannot stand in for the unreadable-store case this
    guard exists for. tar writes `socket ignored` to stderr, mints no member
    and exits 0. Counting stderr reads that line as one archived file, so a
    store whose files are ALL unreadable would pass the completeness check and
    an empty tarball would land under the canonical name -- the inflation is
    exactly inverse to the signal.
    """
    store = tmp_path / "attachments"
    store.mkdir()
    # sun_path caps near 108 bytes; keep this name and the test's own short.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(store / "s"))
    finally:
        sock.close()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    with pytest.raises(ArchiveIncomplete):
        await build_archive(tmp_path, "20260920-043000", expect_rows=1)
    assert list(tmp_path.iterdir()) == [store]
````

## A4 — Task 2
Reason: counting stderr counts tar's diagnostics as archived files, so each failed file inflates the completeness check that exists to catch failed files.
Cost if wrong: a tar without GNU's `--index-file` exits 2 and every nightly build raises `ArchiveIncomplete` — no tarball ships, but loudly rather than silently empty.
### Old
````text
def _count_members(listing: str) -> int:
    """Regular files in tar's own `-v` output.

    Counted from the listing tar already produces rather than by reading the
    archive back: a second pass over a multi-gigabyte artefact costs the whole
    decompression for a number tar just told us.
    """
    return sum(
        1
        for line in listing.splitlines()
        if line.strip() and not line.rstrip().endswith("/")
    )


async def build_archive(dest_dir: Path, stamp: str, *, expect_rows: int) -> Path:
    """Tar the attachment store into `dest_dir`, `.part` then `os.replace`.

    A subprocess rather than `tarfile`: compressing gigabytes on the event loop
    would stall the single worker (invariant 13) for the whole run.
    """
    dest_dir = Path(dest_dir)
    out = dest_dir / f"{ATTACHMENTS_PREFIX}{stamp}.tar.gz"
    part = out.with_name(out.name + ".part")
    root = attachments_root()

    argv = [
        "tar",
        "-czvf",
        "-",
        "-C",
        str(root),
        "--exclude=*.part",
        f"--exclude=./{STAGING_DIRNAME}",
        "--ignore-failed-read",
        "--warning=no-file-changed",
        ".",
    ]
    try:
        with open(part, "wb") as sink:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=sink, stderr=asyncio.subprocess.PIPE
            )
            listing = (await proc.stderr.read()) if proc.stderr else b""
            code = await proc.wait()
        if code not in (0, _TAR_FILE_CHANGED):
            raise ArchiveIncomplete(
                f"tar exited {code}: "
                f"{listing.decode('utf-8', 'replace')[-500:]}"
            )
        members = _count_members(listing.decode("utf-8", "replace"))
        if expect_rows > 0 and members == 0:
            raise ArchiveIncomplete(
                f"{root} archived no files while page_attachments holds "
                f"{expect_rows} rows -- the attachment store is empty or not "
                f"mounted. Nothing renamed."
            )
        if members < expect_rows:
            logger.warning(
                "attachment archive holds %s files against %s rows; the "
                "cleanup job may have unlinked one mid-run",
                members,
                expect_rows,
            )
    except BaseException:
        part.unlink(missing_ok=True)
        raise

    os.replace(part, out)
    return out
````
### New
````text
def _count_members(index_path: Path) -> int:
    """Regular files in tar's own `-v` listing, read from `--index-file`.

    Counted from the listing tar already produces rather than by reading the
    archive back: a second pass over a multi-gigabyte artefact costs the whole
    decompression for a number tar just told us. The listing gets a file of its
    own -- a GNU extension, as `--warning=` already is -- because stderr also
    carries tar's *diagnostics*, and `--ignore-failed-read` turns every
    unreadable file into one. Counting that stream would add one "archived"
    member per file that failed to be archived, which is exactly inverse to the
    signal `ArchiveIncomplete` exists for. Read a line at a time: this listing
    is one line per attachment, so the store's size is its size.
    """
    count = 0
    with open(index_path, "r", encoding="utf-8", errors="replace") as listing:
        for line in listing:
            stripped = line.rstrip("\n")
            if stripped.strip() and not stripped.rstrip().endswith("/"):
                count += 1
    return count


async def build_archive(dest_dir: Path, stamp: str, *, expect_rows: int) -> Path:
    """Tar the attachment store into `dest_dir`, `.part` then `os.replace`.

    A subprocess rather than `tarfile`: compressing gigabytes on the event loop
    would stall the single worker (invariant 13) for the whole run.
    """
    dest_dir = Path(dest_dir)
    out = dest_dir / f"{ATTACHMENTS_PREFIX}{stamp}.tar.gz"
    part = out.with_name(out.name + ".part")
    # Neither family's suffixes match `.index`, so no prune can see it; it is
    # removed on every path regardless.
    index = out.with_name(out.name + ".index")
    root = attachments_root()

    argv = [
        "tar",
        "-czvf",
        "-",
        "-C",
        str(root),
        "--exclude=*.part",
        f"--exclude=./{STAGING_DIRNAME}",
        "--ignore-failed-read",
        "--warning=no-file-changed",
        f"--index-file={index}",
        ".",
    ]
    try:
        with open(part, "wb") as sink:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=sink, stderr=asyncio.subprocess.PIPE
            )
            diagnostics = (await proc.stderr.read()) if proc.stderr else b""
            code = await proc.wait()
        detail = diagnostics.decode("utf-8", "replace")[-500:]
        if code not in (0, _TAR_FILE_CHANGED):
            raise ArchiveIncomplete(f"tar exited {code}: {detail}")
        members = await asyncio.to_thread(_count_members, index)
        if expect_rows > 0 and members == 0:
            raise ArchiveIncomplete(
                f"{root} archived no files while page_attachments holds "
                f"{expect_rows} rows -- the attachment store is empty, not "
                f"mounted, or unreadable. Nothing renamed. tar said: {detail}"
            )
        if members < expect_rows:
            logger.warning(
                "attachment archive holds %s files against %s rows; the "
                "cleanup job may have unlinked one mid-run. tar said: %s",
                members,
                expect_rows,
                detail,
            )
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    finally:
        index.unlink(missing_ok=True)

    os.replace(part, out)
    return out
````

## A5 — Task 7
Reason: counting stderr counts tar's diagnostics as archived members, inverse to the completion check's signal.
Cost if wrong: a listing line without the `./` prefix is uncounted and the stage refuses loudly; nothing is renamed on the wrong side.
### Old
````text
    # Directories end in '/' in tar's listing; everything else is a member.
    MEMBERS="$(grep -c -v '/$' "$TAR_LIST" || true)"
````
### New
````text
    # Members are the lines tar itself lists, which under `-C /src .` all
    # begin with `./`; directories end in '/'. The same stream carries tar's
    # DIAGNOSTICS (`tar: ./x: Cannot open ...`, one per file that
    # --ignore-failed-read skipped), and counting those would score one
    # archived member per file that failed to be archived -- exactly inverse
    # to the signal this check exists for.
    MEMBERS="$(grep -c '^\./.*[^/]$' "$TAR_LIST" || true)"
````

## A6 — Task 7
Reason: the new diagnostics test needs `socket`, which the test file does not import.
Cost if wrong: `NameError` in one test, caught on the first run.
### Old
````text
from app.services.attachment_manifest import COUNT_SQL, MANIFEST_SQL  # noqa: E402
````
### New
````text
import socket  # noqa: E402

from app.services.attachment_manifest import COUNT_SQL, MANIFEST_SQL  # noqa: E402
````

## A7 — Task 7
Reason: nothing pins that a tar diagnostic is not counted as a member; without it the count can be folded back together with no test going red.
Cost if wrong: one extra shell test; the socket path stays under the 108-byte `sun_path` cap as Task 2's does.
### Old
````text
    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1


def test_a_file_changed_under_tar_is_not_a_failure(dest, tmp_path):
````
### New
````text
    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1


def test_a_tar_diagnostic_is_not_counted_as_a_member(dest, tmp_path):
    """stderr carries tar's member listing AND its diagnostics. A unix socket
    is the one entry tar refuses for every user, root included (these tests
    run as root, where a chmod 000 file is still readable): tar writes
    `socket ignored` to stderr, mints no member and exits 0. A count that read
    that line as a member would rename an empty tarball onto the canonical
    name and write the real manifest beside it, after which every later night
    compares equal and skips."""
    store = tmp_path / "socket-volume"
    store.mkdir()
    # sun_path caps near 108 bytes; keep this name and the test's own short.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(store / "s"))
    finally:
        sock.close()
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, store),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert not list(dest.glob("*.manifest"))
    assert len(_dumps(dest)) == 1


def test_a_file_changed_under_tar_is_not_a_failure(dest, tmp_path):
````

## A8 — Task 3
Reason: `WorkerDestination` has no per-call transfer bound to resolve; the constant it uses is the injected client's default, and httpx bounds operations, not transfers.
Cost if wrong: the worker kind keeps a per-read 3600 s bound a live transfer never reaches; nothing is cut off.
### Old
````text
`SshDestination` (`:696`, `:748`) and `WorkerDestination` (`:963`, `:992`) are
the two that bound transfers. Both take the same two signatures:

```python
    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
```

```python
    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str:
```

and each resolves `timeout or SHIP_TIMEOUT_SECONDS` — or
`timeout or READ_BACK_TIMEOUT_SECONDS` on the read-back path — at every place
those constants appear in its body today. `SshDestination._remote_names` gains
`timeout: float | None = None` after its `family` argument, resolved the same
way. Nothing changes for a caller that passes no bound.
````
### New
````text
`SshDestination` (`:696`, `:748`) is the one kind that bounds a transfer as a
whole: `_run` wraps its pump in `asyncio.wait_for`, so its constant is a total
bound and the attachment tarball needs the larger one. It takes the same two
signatures:

```python
    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
```

```python
    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str:
```

and resolves `timeout or SHIP_TIMEOUT_SECONDS` — or
`timeout or READ_BACK_TIMEOUT_SECONDS` on the read-back path — at every
`_run(..., timeout=...)` those constants reach today (`:703`, `:710`, `:755`,
`:766`, `:797`). `SshDestination._remote_names` gains
`timeout: float | None = None` after its `family` argument, resolved the same
way. Nothing changes for a caller that passes no bound.

`WorkerDestination` (`:963`, `:992`) takes the same two signatures and, like
`LocalDestination` and `S3Destination`, **accepts and ignores** the bound. Its
only use of `SHIP_TIMEOUT_SECONDS` is the httpx client default in `_client()`
(`:949`), and an httpx timeout is per read, write and connect operation, never
per transfer — a multi-gigabyte upload that keeps moving never trips it, so a
larger constant buys nothing there. Leave `_client()` and the injected
`client_factory` exactly as they are: the tests build the destination with a
zero-argument factory, and threading a bound through it is a `TypeError` in
`test_worker_ship_and_read_back_agree_with_the_local_hash`. Say so in a
one-line comment on each of the two methods.
````

## A9 — Header
Reason: the Contracts line names `WorkerDestination` as a resolver of the bound, which the Task 3 amendment retracts.
Cost if wrong: a later reader expects the worker kind to honour `timeout=` and it does not; the ssh kind, the only whole-transfer bound, is unaffected.
### Old
````text
  - `async ship(self, local_path: Path, *, timeout: float | None = None)` and `async read_back_sha256(self, name: str, *, timeout: float | None = None)` on the protocol and all four destinations; `SshDestination` and `WorkerDestination` resolve `timeout or SHIP_TIMEOUT_SECONDS` / `READ_BACK_TIMEOUT_SECONDS`, the other two accept and ignore it (Task 3)
````
### New
````text
  - `async ship(self, local_path: Path, *, timeout: float | None = None)` and `async read_back_sha256(self, name: str, *, timeout: float | None = None)` on the protocol and all four destinations; `SshDestination` resolves `timeout or SHIP_TIMEOUT_SECONDS` / `READ_BACK_TIMEOUT_SECONDS` (its `_run` bound is a whole-transfer `wait_for`), the other three accept and ignore it — httpx's timeout on `WorkerDestination` is per operation, not per transfer (Task 3)
````

## A10 — Task 7
Reason: a `set -e` inside a function called from `if !` is inert by bash's documented rule, subshell body or not; the stage's guards then fall through.
Cost if wrong: none observable — under either reading of bash the amended call site runs the stage with its own errexit live.
### Old
````text
if ! attachment_stage; then
    echo "Attachment backup FAILED. The database dump above is intact." >&2
    exit 1
fi
````
### New
````text
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
````

## A11 — Task 7
Reason: the stage's header comment states the subshell escapes the `if !` rule, which is the claim the call-site amendment corrects.
Cost if wrong: a stale comment beside a correct call site.
### Old
````text
# The dump above is already on disk and already pruned, and nothing here may
# unwind it. The stage runs in a subshell with its own errexit (an `if !`
# guard around a plain function would disable errexit inside it) and reports
# through its exit status, which is read at the very end.
````
### New
````text
# The dump above is already on disk and already pruned, and nothing here may
# unwind it. The stage runs in a subshell with its own errexit and reports
# through its exit status, which is read at the very end -- with this shell's
# errexit switched off for the one call, for the reason given there.
````

## A12 — Task 7
Reason: the stub's missing-volume `run` branch fails at tar, so the volume-inspect guard's test passes on the member count rather than on the guard.
Cost if wrong: the stub archives an empty directory where the real docker would; no test that passes today goes red.
### Old
````text
    missing = "exit 1" if volume_dir is None else "exit 0"
    src = str(volume_dir) if volume_dir else "/nonexistent"
````
### New
````text
    missing = "exit 1" if volume_dir is None else "exit 0"
    # A missing volume is one `docker run -v NAME` silently CREATES, so the
    # run branch archives an empty directory rather than failing. A stub that
    # failed at tar would let the inspect guard's test pass for the wrong
    # reason -- the member count, not the guard, would be what refused.
    if volume_dir is None:
        volume_dir = tmp_path / "autocreated-volume"
        volume_dir.mkdir(exist_ok=True)
    src = str(volume_dir)
````

## A13 — Task 7
Reason: no test distinguishes a live inspect guard from a dead one; with rows present the member count refuses the empty volume regardless.
Cost if wrong: one extra shell test that exercises the same stub path.
### Old
````text
    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1, "the dump must survive an attachment failure"
````
### New
````text
    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1, "the dump must survive an attachment failure"


def test_a_missing_volume_fails_even_when_the_table_is_empty(dest, tmp_path):
    """The inspect guard on its own. With rows present the member count would
    refuse an auto-created empty volume anyway, so only the empty-table case
    tells the guard apart from the count -- and only when the stage's own
    `set -e` is live, which it is not if the stage is called from `if !`."""
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=0),
        _docker_stub(tmp_path, None),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1
````

## A14 — Task 16
Reason: the worker runbook covers a missing tarball but not a torn or undecryptable one, which takes the same spec-§7.3 path and leaves the viewer serving restored rows against the previous generation's files.
Cost if wrong: one extra runbook bullet; no code changes.
### Old
````text
- A dump with no tarball at or before its stamp restores the database and keeps
  the current generation, with a warning.
````
### New
````text
- A dump with no tarball at or before its stamp restores the database and keeps
  the current generation, with a warning.
- A paired tarball that fails to decrypt or unpack takes the same path. The
  line `Could not unpack <name>; keeping the current attachment generation.`
  means the database still swapped and the viewer is serving the restored rows
  against the previous generation's files. Every later cycle retries the unpack
  on the attachments-only path and exits 0 either way, so the unit does not go
  red — watch for that line, run `python -m app.services.attachment_verify` to
  list the rows without files, and re-ship the tarball; the retry picks up a
  re-shipped or newer tarball without another dump.
````

## A15 — Task 13
Reason: the plan prescribes two unlabelled outcome lines that render indistinguishably on the surface that decides whether a restore is possible.
Cost if wrong: six words of chrome per destination row and one extra prop on a local component; reversible in one edit.
### Old
````text
In `DestinationRow`, render the second outcome line beside the first:

```tsx
      <OutcomeLine outcome={outcome} />
      <OutcomeLine outcome={attachmentOutcome} />
```

adding `attachmentOutcome: BackupOutcome | null` to its props and passing
`recentOutcomes.get(outcomeKey(destination.name, "attachments")) ?? null` at the
call site.
````
### New
````text
In `DestinationRow`, render the second outcome line beside the first, each
labelled with its family:

```tsx
      <OutcomeLine outcome={outcome} label="database" />
      <OutcomeLine outcome={attachmentOutcome} label="attachments" />
```

adding `attachmentOutcome: BackupOutcome | null` to its props and passing
`recentOutcomes.get(outcomeKey(destination.name, "attachments")) ?? null` at the
call site.

`OutcomeLine` (same file, `:363-380`) takes the label and prefixes all three of
its branches, mirroring `OutcomeBadge`'s `{label}: {…}` shape. Without it the
row draws two lines an operator cannot tell apart — `verified 9/1/2026,
4:30:00 AM` followed by a bare `no run yet`, or `no run yet no run yet` when
neither family has run — and this is the surface that decides whether a restore
is possible. The prefix must be a direct text child of the same `<span>` as the
rest of the line, never a nested element: Testing Library's default matcher
joins an element's own text children, so an existing `findByText(/verified/i)`
keeps matching the one line it matched before.

```tsx
function OutcomeLine({
  outcome,
  label,
}: {
  outcome: BackupOutcome | null
  label: string
}) {
  if (!outcome) {
    return (
      <span className="text-muted-foreground text-sm">{label}: no run yet</span>
    )
  }
  if (outcome.event_type === "backup_shipped") {
    return (
      <span className="text-muted-foreground flex items-center gap-1 text-sm">
        <ShieldCheck aria-hidden className="h-3.5 w-3.5" />
        {label}: verified {new Date(outcome.at).toLocaleString()}
      </span>
    )
  }
  return (
    <span className="text-destructive flex items-center gap-1 text-sm">
      <ShieldAlert aria-hidden className="h-3.5 w-3.5" />
      {label}: {outcome.error ?? "not restorable"}
    </span>
  )
}
```
````

## A16 — Task 13
Reason: no test asserts the second outcome line or the `database:` / `attachments:` badge text, so an implementation that renders only the dump family passes the whole suite.
Cost if wrong: two extra render tests in a file that already owns this surface; they add no fixtures beyond the existing `routes()` idiom.
### Old
````text
      expect(disk.attachments_retention_keep).toBe(5)
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- backups
```

Expected: FAIL — no tarball name, no empty-state text, no retention field.
````
### New
````text
      expect(disk.attachments_retention_keep).toBe(5)
    })
  })

  it("labels each family's badge on the inventory card", async () => {
    routes({
      "/backups/inventory": {
        destinations: [
          {
            ...INVENTORY_ROW,
            last_outcome: {
              event_type: "backup_shipped",
              at: "2026-09-01T04:30:00Z",
              sha256: "a".repeat(64),
              error: null,
            },
            last_attachment_outcome: {
              event_type: "backup_verify_failed",
              at: "2026-09-01T04:31:00Z",
              sha256: null,
              error: "the tarball is torn",
            },
          },
        ],
      },
    })
    render(<BackupsTab />, { wrapper })

    expect(await screen.findByText(/database: verified/i)).toBeInTheDocument()
    expect(
      screen.getByText(/attachments: not restorable/i),
    ).toBeInTheDocument()
  })

  it("labels each outcome line, so a never-run family is not read as the other", async () => {
    // The dump verified on disk, the tarball failed on disk, nas ran neither.
    // Unlabelled, the disk row reads `verified ...` then `the tarball is torn`
    // and the nas row reads `no run yet no run yet` -- an operator cannot tell
    // which artefact either verdict belongs to.
    routes({
      "/events?event_type=backup_shipped&limit=50": {
        items: [
          {
            id: 4,
            created_at: "2026-09-01T04:30:00Z",
            event_type: "backup_shipped",
            object_type: "system",
            object_id: null,
            project: null,
            actor: null,
            api_key_id: null,
            source: "backup_ship",
            payload: { destination: "disk", file: "darkmem-app-x.sql.gz" },
          },
        ],
        total: 1,
      },
      "/events?event_type=backup_verify_failed&limit=50": {
        items: [
          {
            id: 5,
            created_at: "2026-09-01T04:31:00Z",
            event_type: "backup_verify_failed",
            object_type: "system",
            object_id: null,
            project: null,
            actor: null,
            api_key_id: null,
            source: "backup_ship",
            payload: {
              destination: "disk",
              family: "attachments",
              file: "darkmem-app-attachments-x.tar.gz.age",
              error: "the tarball is torn",
            },
          },
        ],
        total: 1,
      },
    })
    render(<BackupsTab />, { wrapper })

    expect(await screen.findByText(/database: verified/i)).toBeInTheDocument()
    expect(
      screen.getByText(/attachments: the tarball is torn/i),
    ).toBeInTheDocument()
    expect(screen.getByText("database: no run yet")).toBeInTheDocument()
    expect(screen.getByText("attachments: no run yet")).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- backups
```

Expected: FAIL — no tarball name, no empty-state text, no retention field, and
no `database:` / `attachments:` labels on either the badges or the outcome
lines.
````
