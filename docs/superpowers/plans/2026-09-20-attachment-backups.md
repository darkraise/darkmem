# Attachment Backups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: the skill the **Execution:** line names — dr-superpowers:subagent-driven-development for `subagent`, dr-superpowers:executing-plans for `inline`. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Back up the page-attachment volume as a second artefact family carried by both existing backup producers, restorable in step with a database dump, and served by the backup worker from versioned generations.

**Architecture:** A manifest hash over `(id, sha256)`, computed by Postgres so the shell and Python producers cannot drift, decides whether the set changed. When it did, each producer writes one whole-set `tar.gz` beside its dump under a shared stamp. A `Family` value (prefix + suffixes) separates the two artefact families at every listing and prune, so no cross-family deletion is possible. A restore pairs a dump with the newest tarball whose stamp is at or before it; on the worker that tarball is unpacked into a new generation directory and a relative `current` symlink is swapped atomically beside the database rename.

**Tech Stack:** FastAPI, SQLAlchemy async raw SQL, asyncpg, `tar`/`age` subprocesses, Docker Compose, bash, pytest-asyncio, React + TanStack Query, vitest.

**Spec:** docs/superpowers/specs/2026-09-20-attachment-backups-design.md

**Execution:** inline — `claude --model sonnet --effort high` — 5 of 16 tasks are heavy (risk 3 or total 6), short of the majority that would make this a subagent plan; the 5 heavy and 5 four-band tasks are delegated, and the 6 remaining tasks top out at total 3.

**Program:** docs/superpowers/specs/2026-09-19-notion-import-design.md — sub-project 2 of 4 — next: Editor rendering and upload of images and files (spec §5.2-5.3)

**Plan review:** 2026-09-20 — dr-superpowers:judge-opus — executability 18 / coherence 17 / coverage 15 / assumptions 15 (round 4)

## Global Constraints

- Greenfield until the freeze: no migration, no compatibility shim. **This plan contains no schema change**; if a task appears to need one, stop and report rather than regenerating `0001_baseline.py`.
- `_is_snapshot` is never widened to match a tarball. The two families are separated by `Family.matches`, and a prune always takes a family argument.
- Ordering inside an artefact family is by the stamp in the name, never by mtime, except in `LocalDestination.prune` and `scripts/backup.sh`'s dump prune where mtime ordering is pre-existing and unchanged.
- No new `events` event type. The two existing backup event types gain payload keys only.
- Invariant 13 (single worker): `tar`, `age` and hashing run as subprocesses or through `asyncio.to_thread`, never on the event loop.
- Pages and attachments stay REST-only: no MCP tool, no scope.
- Backend tests run from `backend/` as `.venv/bin/python -m pytest -q ...` with `TEST_DATABASE_URL` pointing at a lane database (`darkmem_test_2`..`_5`), never at a real database.
- Frontend commands run from `frontend/`: `npm run typecheck`, `npm test`, `npm run build`.
- Every Bash test command carries an explicit timeout (the Bash tool's `timeout` parameter, e.g. 600000).
- **No task deploys.** No implementer runs `docker compose up`, runs `scripts/build-push.sh`, or touches the `:8000` instance. The branch inherits sub-project 1's regenerated baseline, so the deploy is a drop/recreate the owner has not authorised.
- Commits follow `<type>(<scope>): <subject>` (≤ 50 chars, imperative).
- Comments only where the WHY is non-obvious; never reference the task or the plan.

## Contracts

- **Module** `backend/app/services/attachment_manifest.py` (Task 1) exports:
  - `MANIFEST_SQL: str` — one line: `SELECT encode(sha256(convert_to(coalesce(string_agg(id::text || ':' || sha256, E'\n' ORDER BY id), ''), 'UTF8')), 'hex') FROM page_attachments`
  - `COUNT_SQL: str` — `SELECT count(*) FROM page_attachments`
  - `async manifest_hash(session) -> str`
  - `async attachment_count(session) -> int`
- **Module** `backend/app/services/attachment_archive.py` (Task 2) exports:
  - `DUMP_PREFIX = "darkmem-app-"`, `ATTACHMENTS_PREFIX = "darkmem-app-attachments-"`
  - `@dataclass(frozen=True) class Family: prefix: str; suffixes: tuple[str, ...]` with `matches(name: str) -> bool`, `stamp_of(name: str) -> str | None`, `stamp_datetime(name: str) -> datetime`
  - `DUMPS = Family(DUMP_PREFIX, (".sql.gz", ".sql.gz.age"))`
  - `ATTACHMENTS = Family(ATTACHMENTS_PREFIX, (".tar.gz", ".tar.gz.age"))`
  - `class ArchiveIncomplete(RuntimeError)`
  - `async build_archive(dest_dir: Path, stamp: str, *, expect_rows: int) -> Path`
  - `ATTACHMENTS_STATE_KEY = "backup_ship_attachments_state"`
  - `@dataclass(frozen=True) class ArchiveState: stamp: str; manifest_hash: str`
  - `async load_state(session) -> ArchiveState | None`, `async save_state(session, state: ArchiveState) -> None`
- **`backend/app/services/backup_ship.py`**:
  - `Destination` protocol (Task 3): `async list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]`, `async prune(self, keep: int, family: Family = DUMPS) -> list[str]`; the same two signatures on `LocalDestination`, `SshDestination`, `S3Destination`, `WorkerDestination`
  - `_is_snapshot(name) -> bool` and `_stamp_of(name) -> datetime` survive as one-line aliases for `DUMPS.matches` / `DUMPS.stamp_datetime` (Task 3); removing a public name costs more than a one-line forward, and Task 11 is what retires this plan's last importer of `_stamp_of`
  - `async run_dump(*, dest_dir: Path | None = None, stamp: str | None = None) -> Path` (Task 5)
  - `async ship(self, local_path: Path, *, timeout: float | None = None)` and `async read_back_sha256(self, name: str, *, timeout: float | None = None)` on the protocol and all four destinations; `SshDestination` and `WorkerDestination` resolve `timeout or SHIP_TIMEOUT_SECONDS` / `READ_BACK_TIMEOUT_SECONDS`, the other two accept and ignore it (Task 3)
  - `ATTACHMENTS_SHIP_TIMEOUT_SECONDS = 7200`, `ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS = 3600`, `BACKUP_SHIP_MAX_RUN_SECONDS = 21600` (Task 5); Task 6 passes the first two on the tarball leg
  - `ship_all`'s summary gains `"attachments": {"stamp": str | None, "built": bool, "shipped": int, "skipped": list[str], "verify_failed": list[str], "pruned": dict}` (Task 6)
  - `BACKUP_SHIPPED` / `BACKUP_VERIFY_FAILED` payloads gain `"family": "dump" | "attachments"`, and the attachments family also carries `"stamp"` (Task 6)
- **`backend/app/services/backup_config.py`** (Task 5): `DestinationConfig.attachments_retention_keep: int = 3`, validated in 1..3650.
- **`backend/app/services/backup_pull.py`** (Task 10): `async pull(destination, *, name: str | None, out_dir: Path, family: Family = DUMPS) -> Path`; `async paired_name(destination, dump_name: str) -> str` (raises `SnapshotNotFound` when nothing pairs); CLI flags `--family {dump,attachments}` and `--paired-with NAME`.
- **`backend/app/api/routes/backups.py`** (Task 11): `DestinationInventory` gains `attachments_retention_keep: int`, `attachment_snapshots: list[SnapshotRow]`, `last_attachment_outcome: OutcomeRow | None`.
- **`backend/app/worker_receiver.py`** (Task 8): `SNAPSHOT_NAME` matches `darkmem-app-<name>.sql.gz[.age]` and `darkmem-app-attachments-<name>.tar.gz[.age]`, where `<name>` is `[A-Za-z0-9._-]+`. No path separator — which is what prevents traversal, not the absence of dots — no `.part`, and no foreign prefix.
- **`backend/app/services/page_attachment_cleanup.py`** (Task 14): `ROWLESS_BULK_LIMIT_DEFAULT = 100`; `run_cleanup(..., rowless_bulk_limit: int = ROWLESS_BULK_LIMIT_DEFAULT)`; `CleanupReport.rowless_skipped: int`.
- **Module** `backend/app/services/attachment_verify.py` (Task 15): `@dataclass(frozen=True) class VerifyReport: missing_files: list[str]; rowless_files: list[str]` with `ok() -> bool`; `async verify(session) -> VerifyReport`; `python -m app.services.attachment_verify` exits 0 when both lists are empty, 1 otherwise.
- **`scripts/backup.sh`** (Task 7): environment `ATTACHMENT_VOLUME` (default `darkmem-prod_attachment_data`), `DARKMEM_IMAGE` (default `darkraise/darkmem:latest`), `DOCKER_CMD` (default `docker`), `BACKUP_ATTACHMENTS_KEEP` (default 3, 0 disables). Artefacts `darkmem-attachments-<stamp>.tar.gz` with a sidecar `darkmem-attachments-<stamp>.tar.gz.manifest` holding one line, the 64-hex manifest hash.
- **`scripts/worker/restore-cycle.sh`** (Task 9): environment `ATTACHMENT_STORE` (default `/srv/darkmem-attachments`); generations `gen-<stamp>/`; the served generation is `readlink current`.
- **Frontend** (Tasks 12, 13): `DestinationInventory` in `use-backups-api.ts` gains `attachments_retention_keep: number`, `attachment_snapshots: InventorySnapshot[]`, `last_attachment_outcome: InventoryOutcome | null`; `BackupDestination` gains `attachments_retention_keep: number`; `use-backups-tab-binding.ts` exports `outcomeKey(destination: string, family: string) -> string` and `recentOutcomes` is keyed by it.

## Assumptions (evidence)

- `sha256(bytea)` and `convert_to` are core Postgres functions; the stack runs `pgvector/pgvector:0.8.2-pg17` (`docker-compose.yml`, read 2026-09-20). Task 1 verifies the manifest SQL executes.
- The manifest literal survives SQLAlchemy `text()` unchanged: neither `':'` inside a quoted literal nor `::` matches its bind-parameter pattern. `unverified — Task 1 verifies it` by executing it through `text()`.
- `_is_snapshot` already excludes `.tar.gz` by suffix (`backend/app/services/backup_ship.py:292-301`, read 2026-09-20), so the two families are disjoint before any change.
- `_stamp_of` is imported by `backend/tests/test_backups_inventory.py:19` (read 2026-09-20), which is why Task 3 keeps it as an alias rather than moving it.
- `run_dump` mints its own stamp internally and returns only a `Path` (`backup_ship.py:132-196`, read 2026-09-20), so Task 5 adds the parameter that lets a dump and a tarball share one stamp.
- `S3Destination.stream` materialises the whole object and says so in its docstring (`backup_ship.py:858-868`, read 2026-09-20); the container is capped at 1 GB (`docker-compose.yml`).
- `restore-cycle.sh:90-93` exits 0 when the newest dump equals the served one, before anything else runs (read 2026-09-20), which is the stranded-tarball hole Task 9 closes.
- `test_backup_script.py`'s stub compose answers every invocation with the dump body (`:44-45`), and `test_a_successful_dump_lands_under_the_retention_name` asserts `list(dest.iterdir()) == [dump]` (`:94`), both read 2026-09-20 — Task 7 changes both.
- `use-backups-tab-binding.ts:64-87` keys `recentOutcomes` on `payload.destination` alone (read 2026-09-20), which Task 12 changes.
- `assert_attachments_dir_usable(read_only=True)` warns rather than raising when the directory is absent (`backend/app/services/page_attachments.py:216-223`, read 2026-09-20), so the worker needs no change for its pre-first-restore state.
- The image copies only `app/`, `migrations/`, `alembic.ini`, `entrypoint.sh` and the built `web/` (`Dockerfile:63-74`, read 2026-09-20), which is why Task 15 puts the verifier under `app/services/` rather than `scripts/`.
- `ATTACHMENT_VOLUME`'s default `darkmem-prod_attachment_data` is the compose project name `darkmem-prod` (`docker-compose.yml:10`) joined to the volume key `attachment_data` (`:162`), read 2026-09-20. It is a variable precisely because a differently-named project produces a different volume name.
- `backend/tests/test_jobs.py` does not exist (`ls backend/tests`, 2026-09-20); Task 14's verification command names only files that do.
- A plan-review score in the borderline 9-13 band, if any, is accepted rather than re-reviewed: this plan's risk is concentrated in prune and delete paths, and every one of those tasks carries a test that asserts the other family survives.

## Task index

1. The manifest module
2. Families, the archive builder and the state row
3. Family arguments across every destination
4. S3 streaming
5. Retention config, the shared stamp and the time budget
6. The ship decision and the attachments loop
7. The `backup.sh` tarball stage
8. The worker surface: receiver pattern and attachment mount
9. The worker restore cycle
10. Pulling the other half
11. The inventory route
12. Inventory types and the outcome binding
13. The Backups tab
14. The row-less sweep guards
15. Post-restore verification
16. Documentation

---
### Task 1: The manifest module

**Files:**
- Create: `backend/app/services/attachment_manifest.py`
- Test: `backend/tests/test_attachment_manifest.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `MANIFEST_SQL`, `COUNT_SQL`, `manifest_hash`, `attachment_count` — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_attachment_manifest.py`:

```python
"""The attachment set's change gate (spec §3).

The property that matters is not "it hashes something" but that the hash is a
function of the *set*: insertion order must not move it, and a delete followed
by an add of a different file must. A count would satisfy neither.
"""
from __future__ import annotations

import hashlib
from uuid import uuid4

from sqlalchemy import text as sa_text

from app.services.attachment_manifest import attachment_count, manifest_hash

EMPTY_SHA = hashlib.sha256(b"").hexdigest()


async def _insert(session, attachment_id, sha256: str) -> None:
    await session.execute(
        sa_text(
            "INSERT INTO page_attachments "
            "(id, project, filename, content_type, size_bytes, sha256) "
            "VALUES (CAST(:id AS uuid), 'default', 'f.png', 'image/png', 1, :sha)"
        ),
        {"id": str(attachment_id), "sha": sha256},
    )


async def test_an_empty_table_hashes_the_empty_string(session):
    assert await manifest_hash(session) == EMPTY_SHA
    assert await attachment_count(session) == 0


async def test_the_hash_moves_when_a_row_is_added(session):
    before = await manifest_hash(session)
    await _insert(session, uuid4(), "a" * 64)
    after = await manifest_hash(session)
    assert after != before
    assert await attachment_count(session) == 1


async def test_insertion_order_does_not_change_the_hash(session):
    first, second = uuid4(), uuid4()
    await _insert(session, first, "a" * 64)
    await _insert(session, second, "b" * 64)
    forwards = await manifest_hash(session)

    await session.execute(sa_text("DELETE FROM page_attachments"))
    await _insert(session, second, "b" * 64)
    await _insert(session, first, "a" * 64)
    assert await manifest_hash(session) == forwards


async def test_a_delete_plus_add_changes_the_hash(session):
    old = uuid4()
    await _insert(session, old, "a" * 64)
    before = await manifest_hash(session)

    await session.execute(
        sa_text("DELETE FROM page_attachments WHERE id = CAST(:id AS uuid)"),
        {"id": str(old)},
    )
    await _insert(session, uuid4(), "c" * 64)
    assert await manifest_hash(session) != before
    assert await attachment_count(session) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_attachment_manifest.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attachment_manifest'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/attachment_manifest.py`:

```python
"""The attachment set's change gate (spec §3).

One SQL scalar, computed by Postgres, so `scripts/backup.sh` and `backup_ship`
cannot disagree about ordering, formatting or encoding: the shell producer runs
the same literal through `psql -At` and gets the same 64 hex characters this
returns. Aggregating client-side would put an ordering and a newline convention
in two places, and the two producers would drift the first time one changed.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

#: An attachment's bytes never change after `os.replace` -- the id is the
#: filename and there is no update path -- so the (id, sha256) set changes if
#: and only if a row was added or deleted. A bare count would miss a delete
#: plus an add inside one interval.
MANIFEST_SQL = (
    "SELECT encode(sha256(convert_to(coalesce(string_agg(id::text || ':' || "
    "sha256, E'\\n' ORDER BY id), ''), 'UTF8')), 'hex') FROM page_attachments"
)

#: The completion check's other half: a non-zero row count against an archive
#: holding no members is a mis-mounted volume, not an empty corpus.
COUNT_SQL = "SELECT count(*) FROM page_attachments"


async def manifest_hash(session: AsyncSession) -> str:
    """The 64-hex manifest of the whole attachment set.

    An empty table hashes the empty string rather than returning NULL, so a
    corpus with no attachments still has a stable value to compare against.
    """
    return (await session.execute(text(MANIFEST_SQL))).scalar_one()


async def attachment_count(session: AsyncSession) -> int:
    return int((await session.execute(text(COUNT_SQL))).scalar_one())
```

- [ ] **Step 4: Run test to verify it passes**

Run the same command. Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attachment_manifest.py backend/tests/test_attachment_manifest.py
git commit -m "feat(backup): add the attachment manifest gate"
```

---

### Task 2: Families, the archive builder and the state row

**Files:**
- Create: `backend/app/services/attachment_archive.py`
- Test: `backend/tests/test_attachment_archive.py`

**Interfaces:**
- Consumes: nothing at runtime; `build_archive`'s `expect_rows` is supplied by Task 6 from Task 1's `attachment_count`.
- Produces: `Family`, `DUMPS`, `ATTACHMENTS`, `ArchiveIncomplete`, `build_archive`, `ArchiveState`, `load_state`, `save_state` — see Contracts.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_attachment_archive.py`:

```python
"""The second artefact family, its builder and its state row (spec §5.1, §5.3).

The classification tests are the load-bearing ones. Every prune in this system
takes a family, so a predicate that let a tarball read as a dump would let a
retention pass delete dumps -- which is why the disjointness is asserted in
both directions rather than by checking one example of each.
"""
from __future__ import annotations

import tarfile
from datetime import timezone
from pathlib import Path

import pytest
from sqlalchemy import text as sa_text

from app.services.attachment_archive import (
    ATTACHMENTS,
    ATTACHMENTS_STATE_KEY,
    DUMPS,
    ArchiveIncomplete,
    ArchiveState,
    build_archive,
    load_state,
    save_state,
)

DUMP = "darkmem-app-20260920-043000.sql.gz"
DUMP_AGE = "darkmem-app-20260920-043000.sql.gz.age"
TAR = "darkmem-app-attachments-20260920-043000.tar.gz"
TAR_AGE = "darkmem-app-attachments-20260920-043000.tar.gz.age"


@pytest.mark.parametrize("name", [DUMP, DUMP_AGE])
def test_dumps_match_only_dumps(name):
    assert DUMPS.matches(name)
    assert not ATTACHMENTS.matches(name)


@pytest.mark.parametrize("name", [TAR, TAR_AGE])
def test_attachments_match_only_attachments(name):
    assert ATTACHMENTS.matches(name)
    assert not DUMPS.matches(name)


@pytest.mark.parametrize(
    "name",
    [
        "darkmem-app-20260920-043000.sql.gz.part",
        "darkmem-app-attachments-20260920-043000.tar.gz.part",
        "darkmem-20260920-043000.sql.gz",
        "darkmem-attachments-20260920-043000.tar.gz",
        "notes.txt",
        "",
    ],
)
def test_neither_family_matches_a_foreign_or_in_flight_name(name):
    assert not DUMPS.matches(name)
    assert not ATTACHMENTS.matches(name)


def test_stamp_of_returns_the_token_and_stamp_datetime_the_value():
    assert DUMPS.stamp_of(DUMP_AGE) == "20260920-043000"
    assert ATTACHMENTS.stamp_of(TAR_AGE) == "20260920-043000"
    moment = ATTACHMENTS.stamp_datetime(TAR_AGE)
    assert (moment.year, moment.hour, moment.tzinfo) == (2026, 4, timezone.utc)


def test_an_unparseable_stamp_is_none_and_the_epoch():
    name = "darkmem-app-attachments-nonsense.tar.gz"
    assert ATTACHMENTS.stamp_of(name) is None
    assert ATTACHMENTS.stamp_datetime(name).year == 1970


async def test_build_archive_writes_a_tarball_of_the_store(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    (store / "ab").mkdir(parents=True)
    (store / "ab" / "abcd").write_bytes(b"payload")
    (store / "ab" / "abcd.part").write_bytes(b"in flight")
    (store / ".staging" / "job").mkdir(parents=True)
    (store / ".staging" / "job" / "x").write_bytes(b"staged")
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    out = await build_archive(tmp_path, "20260920-043000", expect_rows=1)

    assert out.name == "darkmem-app-attachments-20260920-043000.tar.gz"
    with tarfile.open(out) as archive:
        members = {m.name.lstrip("./") for m in archive.getmembers() if m.isfile()}
    assert members == {"ab/abcd"}
    assert not list(tmp_path.glob("*.part"))


async def test_build_archive_refuses_an_empty_store_when_rows_exist(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    store.mkdir()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    with pytest.raises(ArchiveIncomplete):
        await build_archive(tmp_path, "20260920-043000", expect_rows=4)
    assert not list(tmp_path.glob("darkmem-app-attachments-*"))


async def test_build_archive_allows_an_empty_store_when_no_rows(tmp_path, monkeypatch):
    store = tmp_path / "attachments"
    store.mkdir()
    monkeypatch.setattr("app.services.attachment_archive.attachments_root", lambda: store)

    out = await build_archive(tmp_path, "20260920-043000", expect_rows=0)
    assert out.is_file()


async def test_state_round_trips_and_starts_absent(session):
    assert await load_state(session) is None
    await save_state(session, ArchiveState(stamp="20260920-043000", manifest_hash="ab" * 32))
    loaded = await load_state(session)
    assert loaded == ArchiveState(stamp="20260920-043000", manifest_hash="ab" * 32)

    row = (
        await session.execute(
            sa_text("SELECT key FROM config WHERE key = :k"),
            {"k": ATTACHMENTS_STATE_KEY},
        )
    ).scalar_one()
    assert row == ATTACHMENTS_STATE_KEY
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/`:

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_attachment_archive.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attachment_archive'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/attachment_archive.py`:

```python
"""The attachment artefact family: what its names look like, how one is built,
and what the ship job remembers between runs (spec §5.1, §5.3).

Separate from `backup_ship` for two reasons. That module is already a thousand
lines, and the family predicate has to be importable by anything that lists or
prunes -- a prune that guessed at a name would be a retention pass over the
wrong artefacts, which is data loss rather than a bug.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.page_attachments import STAGING_DIRNAME, attachments_root

logger = logging.getLogger(__name__)

DUMP_PREFIX = "darkmem-app-"
ATTACHMENTS_PREFIX = "darkmem-app-attachments-"

ATTACHMENTS_STATE_KEY = "backup_ship_attachments_state"

_STAMP_FORMAT = "%Y%m%d-%H%M%S"
#: tar's own exit code for "file changed as we read it". Expected against a
#: live volume the cleanup job may be unlinking from, and accepted; any other
#: non-zero status is a real failure.
_TAR_FILE_CHANGED = 1


class ArchiveIncomplete(RuntimeError):
    """The archive holds no files while the database holds rows.

    The tarball's equivalent of pg_dump's completion marker. Without it a
    mis-mounted or empty volume produces a well-formed archive under the
    canonical name, whose manifest then reads as current forever.
    """


@dataclass(frozen=True)
class Family:
    """One artefact family's naming, and the only way to classify a name.

    Prefix *and* suffix, because the attachments prefix is a strict extension
    of the dump prefix: `darkmem-app-attachments-...` starts with
    `darkmem-app-`, and only the suffix separates them. A `.part` matches
    neither, which is what keeps an in-flight write out of a prune's set.
    """

    prefix: str
    suffixes: tuple[str, ...]

    def matches(self, name: str) -> bool:
        if not name.startswith(self.prefix):
            return False
        if self is DUMPS and name.startswith(ATTACHMENTS_PREFIX):
            return False
        return any(name.endswith(suffix) for suffix in self.suffixes)

    def stamp_of(self, name: str) -> str | None:
        """The stamp token, for comparing against a recorded one."""
        if not self.matches(name):
            return None
        core = name[len(self.prefix):].split(".")[0]
        try:
            datetime.strptime(core, _STAMP_FORMAT)
        except ValueError:
            return None
        return core

    def stamp_datetime(self, name: str) -> datetime:
        """The display value. An unparseable name falls back to the epoch
        rather than raising: a listing that 500s over one foreign file is the
        worse surface."""
        token = self.stamp_of(name)
        if token is None:
            return datetime.fromtimestamp(0, timezone.utc)
        return datetime.strptime(token, _STAMP_FORMAT).replace(tzinfo=timezone.utc)


DUMPS = Family(DUMP_PREFIX, (".sql.gz", ".sql.gz.age"))
ATTACHMENTS = Family(ATTACHMENTS_PREFIX, (".tar.gz", ".tar.gz.age"))


@dataclass(frozen=True)
class ArchiveState:
    """What the last tarball this job produced was, and of which set.

    Its own `config` row rather than `job:backup_ship`, which the job registry
    validates against a `config_schema` whose `FieldDescriptor.default` is
    typed `int` and so cannot carry either of these strings.
    """

    stamp: str
    manifest_hash: str


async def load_state(session: AsyncSession) -> ArchiveState | None:
    row = (
        await session.execute(
            select(Config).where(Config.key == ATTACHMENTS_STATE_KEY)
        )
    ).scalar_one_or_none()
    if row is None or not row.value:
        return None
    stamp = row.value.get("stamp")
    manifest = row.value.get("manifest_hash")
    if not stamp or not manifest:
        return None
    return ArchiveState(stamp=stamp, manifest_hash=manifest)


async def save_state(session: AsyncSession, state: ArchiveState) -> None:
    payload = {"stamp": state.stamp, "manifest_hash": state.manifest_hash}
    row = (
        await session.execute(
            select(Config).where(Config.key == ATTACHMENTS_STATE_KEY)
        )
    ).scalar_one_or_none()
    if row:
        row.value = payload
    else:
        session.add(Config(key=ATTACHMENTS_STATE_KEY, value=payload))
    await session.commit()


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
```

- [ ] **Step 4: Run test to verify it passes**

Run the same command. Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attachment_archive.py backend/tests/test_attachment_archive.py
git commit -m "feat(backup): add the attachment artefact family"
```

---
### Task 3: Family arguments across every destination

**Files:**
- Modify: `backend/app/services/backup_ship.py` (the `_is_snapshot` / `_stamp_of` helpers at `:292-301` and `:376-387`, the `Destination` protocol at `:255-279`, and the four destination classes)
- Test: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: `Family`, `DUMPS` from Task 2 — see Contracts.
- Produces: the family-taking `list_snapshots` / `prune` every later task calls — see Contracts.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

Risk 3 because every one of these methods feeds a deletion. A predicate that
let one family read as the other would make a retention pass delete the other
family's artefacts, which is the failure this whole separation exists to
prevent — hence a test that asserts the survivors, not only the deletions.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_backup_ship.py`:

```python
# ── Task 3: the two families never see each other ────────────────────

from app.services.attachment_archive import ATTACHMENTS, DUMPS  # noqa: E402

DUMP_OLD = "darkmem-app-20260101-000000.sql.gz"
DUMP_NEW = "darkmem-app-20260102-000000.sql.gz"
TAR_OLD = "darkmem-app-attachments-20260101-000000.tar.gz"
TAR_NEW = "darkmem-app-attachments-20260102-000000.tar.gz"


def _seed_both_families(directory) -> None:
    """Explicit mtimes: LocalDestination.prune orders on (mtime, name), and
    two files written inside one second would leave the order to the tie-break
    rather than to the property under test."""
    for index, name in enumerate((DUMP_OLD, DUMP_NEW, TAR_OLD, TAR_NEW)):
        path = directory / name
        path.write_bytes(b"x")
        os.utime(path, (1_700_000_000 + index, 1_700_000_000 + index))
    os.utime(directory / TAR_OLD, (1_700_000_000, 1_700_000_000))
    os.utime(directory / TAR_NEW, (1_700_000_001, 1_700_000_001))


async def test_local_listing_is_family_scoped(tmp_path):
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    assert {s.name for s in await dest.list_snapshots()} == {DUMP_OLD, DUMP_NEW}
    assert {s.name for s in await dest.list_snapshots(DUMPS)} == {DUMP_OLD, DUMP_NEW}
    assert {s.name for s in await dest.list_snapshots(ATTACHMENTS)} == {TAR_OLD, TAR_NEW}


async def test_pruning_one_family_leaves_the_other_whole(tmp_path):
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    assert await dest.prune(1, ATTACHMENTS) == [TAR_OLD]
    assert {p.name for p in tmp_path.iterdir()} == {DUMP_OLD, DUMP_NEW, TAR_NEW}

    assert await dest.prune(1) == [DUMP_OLD]
    assert {p.name for p in tmp_path.iterdir()} == {DUMP_NEW, TAR_NEW}


async def test_local_dates_from_mtime_and_the_helper_from_the_name(tmp_path):
    """Local is the one kind that can see a real mtime, and keeps using it.
    The remote kinds have no mtime to trust, so they date from the stamp --
    asserting both here keeps the difference deliberate rather than accidental."""
    _seed_both_families(tmp_path)
    dest = backup_ship.LocalDestination(name="disk", directory=tmp_path)

    tarballs = {s.name: s for s in await dest.list_snapshots(ATTACHMENTS)}
    assert tarballs[TAR_NEW].modified_at.year == 2023
    assert ATTACHMENTS.stamp_datetime(TAR_NEW).year == 2026


async def test_a_transfer_bound_is_overridable_per_call(monkeypatch):
    """The attachment tarball needs a larger bound than a dump; the protocol
    carries it rather than each destination guessing from the name."""
    seen: list[float] = []
    ssh = backup_ship.SshDestination(SSH_CFG)

    async def _run(argv, *, timeout, on_chunk=None):
        seen.append(timeout)
        return b""

    monkeypatch.setattr(ssh, "_run", _run)
    async with ssh._scratch() as (_, base):
        await ssh._remote_names(base, DUMPS, timeout=4242)
    assert 4242 in seen


def test_the_dump_helpers_survive_as_aliases():
    assert backup_ship._is_snapshot(DUMP_NEW)
    assert not backup_ship._is_snapshot(TAR_NEW)
    assert backup_ship._stamp_of(DUMP_NEW).year == 2026
```

Add `import os` to the file's imports if it is not already there.

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/`:

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py
```

Expected: FAIL — `list_snapshots() takes 1 positional argument but 2 were given`.

`SSH_CFG` already exists in that file (the ssh destination's own fixture); if it
is named differently there, use that name.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/backup_ship.py`, add to the imports:

```python
from app.services.attachment_archive import DUMPS, Family
```

Replace the bodies of the two helpers, keeping both names:

```python
def _is_snapshot(name: str) -> bool:
    """This producer's dumps, and only them.

    Kept as a module function because it reads at every call site as "is this
    ours". The classification itself lives on `Family`, where the attachments
    family shares it -- and where the two prefixes, one a strict extension of
    the other, are separated in one place instead of at every listing.
    """
    return DUMPS.matches(name)


def _stamp_of(name: str) -> datetime:
    """The stamp a dump's name carries. `tests/test_backups_inventory.py`
    imports this, so it stays put rather than moving onto `Family`."""
    return DUMPS.stamp_datetime(name)
```

Change four of the `Destination` protocol's declarations. The two transfer
verbs gain an optional bound, because the attachment tarball is a different
artefact size from a dump and one constant cannot serve both:

```python
    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None: ...

    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str: ...

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]: ...

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]: ...
```

`LocalDestination` and `S3Destination` accept `timeout` and ignore it — a local
copy has no transfer to bound, and boto3 carries its own client timeouts:

```python
    async def ship(self, local_path: Path, *, timeout: float | None = None) -> None:
```

```python
    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str:
```

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

`LocalDestination`:

```python
    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        out = []
        for path in self.directory.iterdir():
            if not path.is_file() or not family.matches(path.name):
                continue
            stat = path.stat()
            out.append(
                SnapshotInfo(
                    name=path.name,
                    size=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                )
            )
        return sorted(out, key=lambda s: s.name)

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        entries = [
            (p.name, p.stat().st_mtime)
            for p in self.directory.iterdir()
            if p.is_file() and family.matches(p.name)
        ]
        deleted = _survivors_and_deletions(entries, keep)
        for name in deleted:
            (self.directory / name).unlink(missing_ok=True)
        return deleted
```

`SshDestination` — `_remote_names` takes the family, and both callers pass it:

```python
    async def _remote_names(
        self, base: list[str], family: Family, *, timeout: float | None = None
    ) -> list[str]:
        out = await self._run(
            ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
             f"ls -1 -- {shlex.quote(self._remote_dir())}"],
            timeout=timeout or READ_BACK_TIMEOUT_SECONDS,
        )
        return [
            line
            for line in out.decode("utf-8", "replace").splitlines()
            if family.matches(line.strip())
        ]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        """Names only. `ls -1` carries no size and no mtime, and parsing
        `ls -l` across remote locales is a worse answer than reporting what
        is actually known -- the stamp in the name is the ordering key."""
        async with self._scratch() as (_, base):
            names = await self._remote_names(base, family)
        return [
            SnapshotInfo(name=n, size=0, modified_at=family.stamp_datetime(n))
            for n in sorted(names)
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        remote_dir = self._remote_dir()
        async with self._scratch() as (_, base):
            names = await self._remote_names(base, family)
            # Ordered by the stamp in the name, which sorts lexically because
            # it is zero-padded and big-endian. A remote mtime would need an
            # `ls -l` parse across an unknown locale.
            doomed = sorted(names, reverse=True)[keep:]
            for name in doomed:
                await self._run(
                    ["ssh", "-p", str(self.ssh.port), *base, self._target(), "--",
                     f"rm -f -- {shlex.quote(remote_dir + '/' + name)}"],
                    timeout=READ_BACK_TIMEOUT_SECONDS,
                )
        return doomed
```

`S3Destination` — `_list_all` takes the family:

```python
    def _list_all(self, client, family: Family) -> list[tuple[str, int]]:
        """Every page. Pruning off a truncated first page would compute the
        newest `keep` from an arbitrary slice and delete everything real."""
        out: list[tuple[str, int]] = []
        token = None
        while True:
            kwargs = {"Bucket": self.s3.bucket, "Prefix": self.s3.prefix}
            if token:
                kwargs["ContinuationToken"] = token
            page = client.list_objects_v2(**kwargs)
            for obj in page.get("Contents", []):
                name = obj["Key"][len(self.s3.prefix):]
                if family.matches(name):
                    out.append((name, obj.get("Size", 0)))
            if not page.get("IsTruncated"):
                return out
            token = page["NextContinuationToken"]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        client = self._factory()
        entries = await asyncio.to_thread(self._list_all, client, family)
        return [
            SnapshotInfo(name=n, size=size, modified_at=family.stamp_datetime(n))
            for n, size in sorted(entries)
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        client = self._factory()
        entries = await asyncio.to_thread(self._list_all, client, family)
        # The stamp sorts lexically, so key order is snapshot order -- no
        # LastModified parse, and no dependence on what the service reports.
        doomed = sorted((n for n, _ in entries), reverse=True)[keep:]
        for name in doomed:
            await asyncio.to_thread(
                client.delete_object, Bucket=self.s3.bucket, Key=self._key(name)
            )
        return doomed
```

`WorkerDestination` — `_listing` takes the family:

```python
    async def _listing(self, family: Family) -> list[dict]:
        async with self._factory() as client:
            response = await client.get("/snapshots", headers=self._headers())
        self._raise_for(response, "listing")
        # The receiver already excludes `.part` files and foreign prefixes, so
        # this filter is the belt: two independent refusals is what keeps an
        # in-flight upload out of a prune's deletion set.
        return [
            item
            for item in response.json().get("snapshots", [])
            if family.matches(item["name"])
        ]

    async def list_snapshots(self, family: Family = DUMPS) -> list[SnapshotInfo]:
        return [
            SnapshotInfo(
                name=item["name"],
                size=item.get("size", 0),
                modified_at=family.stamp_datetime(item["name"]),
            )
            for item in sorted(await self._listing(family), key=lambda i: i["name"])
        ]

    async def prune(self, keep: int, family: Family = DUMPS) -> list[str]:
        names = [item["name"] for item in await self._listing(family)]
        doomed = sorted(names, reverse=True)[keep:]
        async with self._factory() as client:
            for name in doomed:
                response = await client.delete(
                    f"/snapshots/{name}", headers=self._headers()
                )
                self._raise_for(response, "delete")
        return doomed
```

- [ ] **Step 4: Run the whole ship suite**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py tests/test_backups_inventory.py
```

Expected: all passed — the pre-existing tests prove the defaulted signatures kept every dump call site correct.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/backup_ship.py backend/tests/test_backup_ship.py
git commit -m "feat(backup): scope listings and prunes by family"
```

---

### Task 4: S3 streaming

**Files:**
- Modify: `backend/app/services/backup_ship.py` (`S3Destination._read_object`, `_hash_object`, `stream`, `read_back_sha256` at `:848-878`)
- Test: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: the family-taking destination surface from Task 3 (no signature change here).
- Produces: nothing new. This closes programme spec §3.7's requirement that no pull path materialise a whole object.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_backup_ship.py`:

```python
# ── Task 4: S3 never materialises an object ──────────────────────────


class _CountingBody:
    """A boto3 body that records how much each `read` asked for.

    The property is "no single read asks for the whole object": a destination
    that buffers a multi-gigabyte tarball OOM-kills a container capped at 1 GB,
    and a test that only compared the final bytes would pass either way.
    """

    def __init__(self, payload: bytes):
        self._buffer = io.BytesIO(payload)
        self.reads: list[int | None] = []
        self.closed = False

    def read(self, size=-1):
        self.reads.append(size)
        return self._buffer.read(size)

    def close(self):
        self.closed = True


class _StreamingFakeS3(_FakeS3):
    def __init__(self, objects=None):
        super().__init__(objects)
        self.bodies: list[_CountingBody] = []

    def get_object(self, Bucket, Key):  # noqa: N803
        body = _CountingBody(self.objects[Key])
        self.bodies.append(body)
        return {"Body": body}


async def test_s3_streams_in_bounded_chunks(tmp_path):
    key = "darkmem/darkmem-app-attachments-20260101-000000.tar.gz.age"
    payload = b"z" * (3 * backup_ship._S3_CHUNK + 7)
    fake = _StreamingFakeS3({key: payload})

    chunks = [
        chunk
        async for chunk in _s3(fake).stream(
            "darkmem-app-attachments-20260101-000000.tar.gz.age"
        )
    ]

    assert b"".join(chunks) == payload
    assert len(chunks) == 4
    assert fake.bodies[0].reads == [backup_ship._S3_CHUNK] * 5
    assert fake.bodies[0].closed


async def test_s3_read_back_hashes_without_buffering(tmp_path):
    key = "darkmem/darkmem-app-attachments-20260101-000000.tar.gz.age"
    payload = b"y" * (2 * backup_ship._S3_CHUNK)
    fake = _StreamingFakeS3({key: payload})

    digest = await _s3(fake).read_back_sha256(
        "darkmem-app-attachments-20260101-000000.tar.gz.age"
    )

    assert digest == hashlib.sha256(payload).hexdigest()
    assert all(size == backup_ship._S3_CHUNK for size in fake.bodies[0].reads)
```

Add `import hashlib` and `import io` to the file's imports if they are not already there.

- [ ] **Step 2: Run test to verify it fails**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py -k s3
```

Expected: FAIL — `AttributeError: module 'app.services.backup_ship' has no attribute '_S3_CHUNK'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/backup_ship.py`, beside `_CHUNK`, add:

```python
#: S3 reads in larger chunks than local I/O: each one crosses a thread
#: boundary, so 64 KiB would mean sixteen thousand hops per gigabyte.
_S3_CHUNK = 1 << 20
```

Replace `S3Destination._read_object`, `_hash_object`, `stream` and
`read_back_sha256` with:

```python
    def _open_object(self, client, key: str):
        return client.get_object(Bucket=self.s3.bucket, Key=key)["Body"]

    async def stream(self, name: str):
        """Chunked, never one `.read()`.

        An attachment tarball is the whole page-attachment volume, and this
        process runs under a 1 GB memory limit: materialising the object to
        verify or to pull it would be the largest allocation here by orders of
        magnitude. Each chunk crosses a thread boundary because boto3's body is
        synchronous.
        """
        client = self._factory()
        body = await asyncio.to_thread(self._open_object, client, self._key(name))
        try:
            while True:
                chunk = await asyncio.to_thread(body.read, _S3_CHUNK)
                if not chunk:
                    return
                yield chunk
        finally:
            await asyncio.to_thread(body.close)

    async def read_back_sha256(self, name: str, *, timeout: float | None = None) -> str:
        """Hash the object's own bytes, never its ETag.

        An ETag is a multipart-dependent digest of what the *service* thinks it
        stored; rule 2 asks what we can read back. Derived from `stream`, so a
        verify and a restore-time pull read the destination through one path.

        `timeout` is accepted and ignored, as Task 3 established for this kind:
        boto3 carries its own client timeouts, and dropping the parameter here
        would make an S3 destination raise `TypeError` the moment Task 6 passes
        the attachments bound.
        """
        return await _hash_stream(self, name)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/backup_ship.py backend/tests/test_backup_ship.py
git commit -m "fix(backup): stream s3 objects instead of buffering"
```

---
### Task 5: Retention config, the shared stamp and the time budget

**Files:**
- Modify: `backend/app/services/backup_config.py` (`DestinationConfig`, `_validate`)
- Modify: `backend/app/services/backup_ship.py` (`run_dump` at `:136-196`; the timeout constants at `:580-581`)
- Modify: `backend/app/main.py` (the `backup_ship` job registration, `max_run_seconds=7200`)
- Test: `backend/tests/test_backup_config.py`, `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `DestinationConfig.attachments_retention_keep`, `run_dump(stamp=...)`, `ATTACHMENTS_SHIP_TIMEOUT_SECONDS`, `ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS`, `BACKUP_SHIP_MAX_RUN_SECONDS` — see Contracts.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 2 - spec 0 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_backup_config.py`:

```python
# ── Task 5: the attachments family has its own retention ─────────────


async def test_attachments_retention_defaults_to_three(session):
    saved = await bc.save_destinations(session, {"destinations": [LOCAL]})
    assert saved[0].attachments_retention_keep == 3


async def test_attachments_retention_is_range_checked(session):
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session,
            {"destinations": [{**LOCAL, "attachments_retention_keep": 0}]},
        )
    with pytest.raises(bc.DestinationInvalid):
        await bc.save_destinations(
            session,
            {"destinations": [{**LOCAL, "attachments_retention_keep": 3651}]},
        )


async def test_attachments_retention_round_trips(session):
    await bc.save_destinations(
        session, {"destinations": [{**LOCAL, "attachments_retention_keep": 7}]}
    )
    loaded = await bc.load_destinations(session, masked=False)
    assert loaded[0].attachments_retention_keep == 7
```

Append to `backend/tests/test_backup_ship.py`:

```python
# ── Task 5: one stamp for both artefacts, and the run budget ─────────


async def test_run_dump_honours_a_caller_supplied_stamp(tmp_path, monkeypatch):
    await _dump_into(tmp_path, monkeypatch)
    out = await backup_ship.run_dump(stamp="20260920-043000")
    assert out.name == "darkmem-app-20260920-043000.sql.gz"


async def test_run_dump_still_mints_its_own_stamp(tmp_path, monkeypatch):
    await _dump_into(tmp_path, monkeypatch)
    out = await backup_ship.run_dump()
    assert backup_ship.DUMPS.stamp_of(out.name) is not None


def test_the_run_budget_covers_one_destination_end_to_end():
    """Both artefacts, both directions, for one destination. Three unreachable
    NASes can still exhaust the budget -- that is accepted -- but a single
    destination must never be cut off mid-verify, because a kill there leaves
    the state row unwritten and repeats the whole decision tomorrow."""
    one_destination = (
        backup_ship.SHIP_TIMEOUT_SECONDS
        + backup_ship.READ_BACK_TIMEOUT_SECONDS
        + backup_ship.ATTACHMENTS_SHIP_TIMEOUT_SECONDS
        + backup_ship.ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS
    )
    assert backup_ship.BACKUP_SHIP_MAX_RUN_SECONDS > one_destination


def test_main_registers_the_job_with_that_budget():
    """A text assertion on purpose: building the app to read one registration
    field would stand a database and a scheduler up for a constant."""
    source = (
        Path(backup_ship.__file__).resolve().parents[1] / "main.py"
    ).read_text()
    assert "max_run_seconds=BACKUP_SHIP_MAX_RUN_SECONDS" in source
```

Add `from pathlib import Path` to that file's imports if it is not already there.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_config.py tests/test_backup_ship.py
```

Expected: FAIL — `AttributeError: 'DestinationConfig' object has no attribute 'attachments_retention_keep'` and `run_dump() got an unexpected keyword argument 'stamp'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/backup_config.py`, add the field to `DestinationConfig` below `retention_keep`:

```python
    #: The attachment tarball family's own retention. Separate from
    #: `retention_keep` because the artefacts are orders of magnitude apart:
    #: fourteen whole-volume tarballs is a different disk commitment from
    #: fourteen dumps.
    attachments_retention_keep: int = 3
```

And in `_validate`, beside the existing range check:

```python
        if d.attachments_retention_keep < 1 or d.attachments_retention_keep > 3650:
            raise DestinationInvalid(
                f"{d.name}: attachments_retention_keep out of range"
            )
```

In `backend/app/services/backup_ship.py`, change `run_dump`'s signature and its
`out` line, leaving the rest of the body untouched:

```python
async def run_dump(*, dest_dir: Path | None = None, stamp: str | None = None) -> Path:
```

```python
    out = directory / f"{JOB_PREFIX}{stamp or _stamp()}.sql.gz"
```

Extend `run_dump`'s docstring with:

```
    `stamp` lets one run give the dump and its attachment tarball the same
    stamp, which is what makes the restore pairing rule's equality case work.
    Absent, it mints its own as before.
```

Beside `SHIP_TIMEOUT_SECONDS` / `READ_BACK_TIMEOUT_SECONDS`, add:

```python
#: The attachment tarball is the whole page-attachment volume, not a
#: compressed schema, so both directions get their own larger bound rather
#: than forcing one constant to serve two artefact sizes. Task 6 passes them
#: through the `timeout=` parameter Task 3 put on `ship` and
#: `read_back_sha256`; defining them without passing them would leave a
#: multi-gigabyte transfer cut off at the dump's 3600/900.
ATTACHMENTS_SHIP_TIMEOUT_SECONDS = 7200
ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS = 3600

#: The job's whole-run bound. One destination's worst case is now both
#: artefacts in both directions; a kill mid-verify leaves the attachments
#: state row unwritten and repeats the decision tomorrow, so the budget buys
#: room for the destination in flight rather than for every destination.
BACKUP_SHIP_MAX_RUN_SECONDS = 21600
```

In `backend/app/main.py`, extend the existing import and use the constant:

```python
    from app.services.backup_ship import BACKUP_SHIP_JOB_KEY, BACKUP_SHIP_MAX_RUN_SECONDS
```

```python
        max_run_seconds=BACKUP_SHIP_MAX_RUN_SECONDS,
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_config.py tests/test_backup_ship.py \
  tests/test_backups_inventory.py
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/backup_config.py backend/app/services/backup_ship.py \
  backend/app/main.py backend/tests/test_backup_config.py backend/tests/test_backup_ship.py
git commit -m "feat(backup): add attachment retention and run budget"
```

---

### Task 6: The ship decision and the attachments loop

**Files:**
- Modify: `backend/app/services/backup_ship.py` (`ship_all` at `:473-565`, plus module imports)
- Test: `backend/tests/test_backup_ship.py`

**Interfaces:**
- Consumes: Task 1's `manifest_hash` / `attachment_count`, Task 2's `ATTACHMENTS` / `build_archive` / `ArchiveState` / `load_state` / `save_state`, Task 3's family-taking `prune`, Task 5's `run_dump(stamp=...)` — see Contracts.
- Produces: `ship_all`'s `"attachments"` summary and the `"family"` / `"stamp"` journal payload keys Task 11 and Task 12 read — see Contracts.

**Implementer:** dr-superpowers:impl-opus-high
**Evaluation:** files 1 - spec 0 - coupling 2 - risk 3 = 6

Risk 3: this decides whether an off-host copy of every attachment exists. The
two failure directions are opposite and both silent — a gate that never fires
ships a multi-gigabyte tarball nightly, and a gate that always holds leaves a
destination with no restorable copy while the summary reads clean.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_backup_ship.py`, replace `_FakeDestination` wholesale.
It now ships two artefacts per run, so its read-back must hash *the artefact it
was asked about* — the shipped `_local` attribute one existing test sets from
outside (`:348`) cannot serve both, and leaving it unset raises `AttributeError`
on the first read-back:

```python
class _FakeDestination:
    """A destination whose every call is observable and whose read-back can lie.

    `ship` remembers each artefact by name so `read_back_sha256` can hash the
    one it is asked about: a run now ships a dump and a tarball, and one stored
    path would make the second read-back hash the first artefact.
    """

    def __init__(self, name, *, sha=None, fail_ship=False, retention_keep=14,
                 attachments_retention_keep=3, holds=()):
        self.name = name
        self.retention_keep = retention_keep
        self.attachments_retention_keep = attachments_retention_keep
        self._sha = sha
        self._fail_ship = fail_ship
        self._holds = list(holds)
        self._paths: dict[str, object] = {}
        self.shipped: list[str] = []
        self.pruned_with: list[int] = []
        self.pruned_families: list[tuple[int, str]] = []
        self.timeouts: list[float | None] = []

    async def ship(self, local_path, *, timeout=None):
        if self._fail_ship:
            raise RuntimeError("the NAS is unplugged")
        self.timeouts.append(timeout)
        self._paths[local_path.name] = local_path
        self.shipped.append(local_path.name)

    async def read_back_sha256(self, name, *, timeout=None):
        if self._sha is not None:
            return self._sha
        return await backup_ship.sha256_file(self._paths[name])

    async def list_snapshots(self, family=None):
        family = family or backup_ship.DUMPS
        return [
            backup_ship.SnapshotInfo(
                name=n, size=0, modified_at=family.stamp_datetime(n)
            )
            for n in self._holds
            if family.matches(n)
        ]

    async def prune(self, keep, family=None):
        family = family or backup_ship.DUMPS
        self.pruned_with.append(keep)
        self.pruned_families.append((keep, family.prefix))
        return []
```

The `dest._local = ...` assignment at `tests/test_backup_ship.py:348` becomes
dead once `read_back_sha256` reads `self._paths[name]`, and it is harmless.
Delete that one line; nothing else in that test changes.

**Five pre-existing `ship_all` assertions change, because a run now ships two
artefacts to each destination.** They are not optional: Step 4 expects the
whole file green.

- `:297` `assert len(rows) == 1` over `backup_shipped` in
  `test_ship_all_verifies_and_journals` → `assert len(rows) == 2`. That test
  does not patch `build_destination`, so it runs the real `LocalDestination`
  against `DUMP_DIR`, and with `_fake_archive` in place the tarball ships and
  journals too. `payload = rows[0]` and the three assertions under it are
  unchanged: `ORDER BY created_at, id` puts the dump row first.
- `:322` `assert len(rows) == 1` over `backup_verify_failed` → the liar fails
  the tarball too, so `assert len(rows) == 2`. `rows[0]` stays the dump row.
- `:327` `assert liar.pruned_with == [14]` → `assert liar.pruned_with == [14, 3]`;
  the attachments prune calls the same method with that family's own keep.
- `:967` `assert rows[-1]["got"] == "f" * 64` → the last row is now the
  attachments failure, which carries `error` and no `got`. Select by family:
  `assert [r for r in rows if r["family"] == "dump"][0]["got"] == "f" * 64`.
- `:960` `monkeypatch.setattr(liar, "read_back_sha256", lambda name: ...)` →
  `lambda name, timeout=None: ...`, or it raises `TypeError` on the tarball leg.

**And every pre-existing `ship_all` test must monkeypatch `build_archive`.**
Call `_fake_archive(monkeypatch)` in each of them. Without it those
tests run the real `tar` against `settings.attachments_dir`, so their outcome
depends on whether `backend/data/attachments` happens to exist on the host —
absent in a clean checkout, present after anyone has run the dev server.

Then append the decision tests:

```python
# ── Task 6: the build-and-ship decision ──────────────────────────────

ARCHIVE_STAMP = "20260101-000000"
ARCHIVE_NAME = f"darkmem-app-attachments-{ARCHIVE_STAMP}.tar.gz"


async def _journal_attachment(session, destination, stamp, event_type, payload):
    await session.execute(
        sa_text(
            "INSERT INTO events (event_type, object_type, source, payload) "
            "VALUES (:t, 'system', 'backup_ship', CAST(:p AS jsonb))"
        ),
        {"t": event_type, "p": json.dumps(payload)},
    )


async def _journal_attachment_failure(session, destination, stamp):
    await _journal_attachment(
        session, destination, stamp, "backup_verify_failed",
        {"destination": destination, "family": "attachments", "stamp": stamp,
         "error": "read-back mismatch"},
    )


async def _journal_attachment_success(session, destination, stamp):
    await _journal_attachment(
        session, destination, stamp, "backup_shipped",
        {"destination": destination, "family": "attachments", "stamp": stamp,
         "sha256": "ab"},
    )


def _fake_archive(monkeypatch) -> list[str]:
    """Stand in for the tar subprocess and record every stamp it was asked
    for -- the stamp is the property under test, not the bytes. It writes to
    the `dest_dir` it is handed, so it needs no directory of its own."""
    asked: list[str] = []

    async def _build(dest_dir, stamp, *, expect_rows):
        asked.append(stamp)
        out = Path(dest_dir) / f"darkmem-app-attachments-{stamp}.tar.gz"
        out.write_bytes(b"tarball")
        return out

    monkeypatch.setattr(backup_ship, "build_archive", _build)
    return asked


async def _one_destination(session, monkeypatch, tmp_path, fake):
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(session, {"destinations": [{**LOCAL, "name": fake.name}]})
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fake)


async def test_a_changed_manifest_builds_ships_and_records(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["attachments"]["built"] is True
    assert summary["attachments"]["shipped"] == 1
    assert len(asked) == 1
    rows = await _payloads(session, "backup_shipped")
    families = [r["family"] for r in rows]
    assert families == ["dump", "attachments"]
    assert rows[1]["stamp"] == asked[0]

    state = await backup_ship.load_state(session)
    assert state is not None and state.stamp == asked[0]


async def test_an_unchanged_manifest_with_a_verified_copy_ships_nothing(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)
    await backup_ship.ship_all(session_factory)
    stamp = asked[0]

    # The destination now holds it and the journal says it verified.
    fake._holds = [f"darkmem-app-attachments-{stamp}.tar.gz"]
    asked.clear()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == []
    assert summary["attachments"]["built"] is False
    assert summary["attachments"]["skipped"] == ["disk"]


async def test_a_destination_missing_the_copy_catches_up_at_the_same_stamp(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)
    await backup_ship.ship_all(session_factory)
    first = asked[0]
    asked.clear()

    # Listing is empty: the copy is gone. The manifest has not moved.
    summary = await backup_ship.ship_all(session_factory)

    assert asked == [first], "a catch-up must not mint a new stamp"
    assert summary["attachments"]["shipped"] == 1
    state = await backup_ship.load_state(session)
    assert state.stamp == first


async def test_a_listed_copy_that_failed_verification_is_shipped_again(
    session, session_factory, tmp_path, monkeypatch
):
    """The journal half of the decision, and the only test that reaches it.

    The state row must already say this manifest was handled, or `changed`
    would be True and the rebuild would happen for the wrong reason.
    """
    stamp = "20260101-000000"
    fake = _FakeDestination("disk", holds=[f"darkmem-app-attachments-{stamp}.tar.gz"])
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    manifest = await backup_ship.manifest_hash(session)
    await backup_ship.save_state(
        session, backup_ship.ArchiveState(stamp=stamp, manifest_hash=manifest)
    )
    await _journal_attachment_failure(session, "disk", stamp)
    await session.commit()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == [stamp], "a listed but unverified copy must be re-shipped"
    assert summary["attachments"]["skipped"] == []


async def test_a_listed_and_verified_copy_is_not_shipped_again(
    session, session_factory, tmp_path, monkeypatch
):
    """The same setup with a `backup_shipped` row: the pair of tests is what
    proves the journal, not the listing, is what decides."""
    stamp = "20260101-000000"
    fake = _FakeDestination("disk", holds=[f"darkmem-app-attachments-{stamp}.tar.gz"])
    await _one_destination(session, monkeypatch, tmp_path, fake)
    asked = _fake_archive(monkeypatch)

    manifest = await backup_ship.manifest_hash(session)
    await backup_ship.save_state(
        session, backup_ship.ArchiveState(stamp=stamp, manifest_hash=manifest)
    )
    await _journal_attachment_success(session, "disk", stamp)
    await session.commit()

    summary = await backup_ship.ship_all(session_factory)

    assert asked == []
    assert summary["attachments"]["skipped"] == ["disk"]


async def test_the_tarball_transfer_gets_the_larger_bound(
    session, session_factory, tmp_path, monkeypatch
):
    """Defining the constants without passing them would cut a multi-gigabyte
    transfer off at the dump's bound -- the failure the budget exists against."""
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)
    _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)

    assert fake.timeouts == [None, backup_ship.ATTACHMENTS_SHIP_TIMEOUT_SECONDS]


async def test_three_destinations_converge_on_one_stamp(
    session, session_factory, tmp_path, monkeypatch
):
    """The catch-up must terminate. If a destination that was behind made the
    run mint a fresh stamp, every *other* destination would then lack that one
    and ship again the night after, forever."""
    fakes = {n: _FakeDestination(n) for n in ("a", "b", "c")}
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {"destinations": [{**LOCAL, "name": n} for n in ("a", "b", "c")]},
    )
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fakes[cfg.name])
    asked = _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)
    stamp = asked[0]
    held = f"darkmem-app-attachments-{stamp}.tar.gz"

    # Two destinations kept it; the third lost it.
    fakes["a"]._holds = [held]
    fakes["b"]._holds = [held]
    asked.clear()
    summary = await backup_ship.ship_all(session_factory)
    assert asked == [stamp]
    assert sorted(summary["attachments"]["skipped"]) == ["a", "b"]

    # Now all three hold it: the third run ships nothing and builds nothing.
    fakes["c"]._holds = [held]
    asked.clear()
    summary = await backup_ship.ship_all(session_factory)
    assert asked == []
    assert sorted(summary["attachments"]["skipped"]) == ["a", "b", "c"]


async def test_the_attachments_prune_uses_its_own_family_and_keep(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk", attachments_retention_keep=3)
    await _dump_into(tmp_path, monkeypatch)
    await bc.save_destinations(
        session,
        {"destinations": [{**LOCAL, "name": "disk", "retention_keep": 14,
                           "attachments_retention_keep": 3}]},
    )
    monkeypatch.setattr(backup_ship, "build_destination", lambda cfg: fake)
    _fake_archive(monkeypatch)

    await backup_ship.ship_all(session_factory)

    assert (14, backup_ship.DUMPS.prefix) in fake.pruned_families
    assert (3, backup_ship.ATTACHMENTS.prefix) in fake.pruned_families


async def test_a_failed_tarball_leaves_the_dump_reported_as_shipped(
    session, session_factory, tmp_path, monkeypatch
):
    fake = _FakeDestination("disk")
    await _one_destination(session, monkeypatch, tmp_path, fake)

    async def _boom(dest_dir, stamp, *, expect_rows):
        raise backup_ship.ArchiveIncomplete("the volume is not mounted")

    monkeypatch.setattr(backup_ship, "build_archive", _boom)

    summary = await backup_ship.ship_all(session_factory)

    assert summary["shipped"] == 1
    assert summary["verify_failed"] == []
    assert summary["attachments"]["verify_failed"] == ["disk"]
    assert await backup_ship.load_state(session) is None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py \
  -k "changed_manifest or unchanged_manifest"
```

Expected: FAIL — `KeyError: 'attachments'` from `summary["attachments"]`.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/backup_ship.py`, extend the imports:

```python
from app.services.attachment_archive import (
    ATTACHMENTS,
    DUMPS,
    ArchiveIncomplete,
    ArchiveState,
    Family,
    build_archive,
    load_state,
    save_state,
)
from app.services.attachment_manifest import attachment_count, manifest_hash
```

Add the journal query and the `holds` helper above `ship_all`:

```python
#: The newest attachments-family outcome per destination. Read rather than
#: assumed: a copy that failed its read-back is still *listed*, and the dump
#: family only self-heals because a fresh dump arrives nightly -- a gate on
#: the manifest removes exactly that property.
_NEWEST_ATTACHMENT_OUTCOME = text(
    """
    SELECT DISTINCT ON (payload->>'destination')
           payload->>'destination' AS destination,
           event_type,
           payload
      FROM events
     WHERE event_type IN (:shipped, :failed)
       AND object_type = 'system'
       AND payload->>'family' = 'attachments'
     ORDER BY payload->>'destination', created_at DESC, id DESC
    """
)


async def _attachment_outcomes(session_factory) -> dict[str, tuple[str, str]]:
    async with session_factory() as session:
        rows = (
            await session.execute(
                _NEWEST_ATTACHMENT_OUTCOME,
                {"shipped": BACKUP_SHIPPED, "failed": BACKUP_VERIFY_FAILED},
            )
        ).mappings().all()
    return {
        row["destination"]: (row["event_type"], (row["payload"] or {}).get("stamp", ""))
        for row in rows
    }


async def _destination_holds(destination, stamp: str, outcome) -> bool:
    """Listed AND journalled as verified, both at this stamp."""
    listed = await destination.list_snapshots(ATTACHMENTS)
    if not any(ATTACHMENTS.stamp_of(s.name) == stamp for s in listed):
        return False
    if outcome is None:
        return False
    event_type, journalled = outcome
    return event_type == BACKUP_SHIPPED and journalled == stamp
```

Add `from sqlalchemy import text` to `backup_ship.py`'s imports if it is not
already there, and `import json` plus `from sqlalchemy import text as sa_text`
to the test file's if they are not.

Replace `ship_all` with:

```python
async def ship_all(session_factory) -> dict:
    """Dump once, tar the attachment set when it changed, then ship both to
    every enabled destination in sequence.

    A destination's failure is caught, journalled and folded into the summary;
    it never skips the destinations behind it. One unplugged NAS must not mean
    a night with no off-host copy anywhere. The two artefacts fail
    independently for the same reason: a tarball that could not be built must
    not retract a dump that landed.
    """
    async with session_factory() as session:
        configured = await load_destinations(session, masked=False)
    enabled = [c for c in configured if c.enabled]

    attachments: dict = {
        "stamp": None,
        "built": False,
        "shipped": 0,
        "skipped": [],
        "verify_failed": [],
        "pruned": {},
    }
    summary: dict = {
        "dump": None,
        "shipped": 0,
        "verify_failed": [],
        "pruned": {},
        "attachments": attachments,
    }
    if not enabled:
        # No dump at all: reading the whole database to produce a file nobody
        # asked for is real I/O against the live server.
        logger.info("backup_ship: no enabled destinations, nothing dumped")
        return summary

    async with session_factory() as session:
        manifest = await manifest_hash(session)
        expect_rows = await attachment_count(session)
        state = await load_state(session)
    changed = state is None or state.manifest_hash != manifest
    run_stamp = _stamp()
    # A catch-up reuses the recorded stamp. Minting a fresh one would leave
    # every *other* destination lacking it, so the next run would ship again,
    # and so on forever -- and the stamp is also the pairing key a restore
    # reads, so it must name when the content was captured.
    archive_stamp = run_stamp if changed else state.stamp
    attachments["stamp"] = archive_stamp
    outcomes = await _attachment_outcomes(session_factory)

    dump = await run_dump(stamp=run_stamp)
    artifacts = await _artifacts_for(dump, [c.age_recipient for c in enabled])
    keep_plaintext = any(c.age_recipient is None for c in enabled)
    summary["dump"] = dump.name

    archive: Path | None = None
    archive_artifacts: dict[str | None, Path] = {}
    archive_shipped = False

    try:
        for cfg in enabled:
            artifact = artifacts[cfg.age_recipient]
            started = time.monotonic()
            destination = None
            try:
                destination = build_destination(cfg)
                await destination.ship(artifact)
                expected = await sha256_file(artifact)
                got = await destination.read_back_sha256(artifact.name)
                if got != expected:
                    raise VerifyMismatch(expected=expected, got=got)
            except VerifyMismatch as mismatch:
                summary["verify_failed"].append(cfg.name)
                await _journal_verify_failed(
                    session_factory,
                    {
                        "destination": cfg.name,
                        "family": "dump",
                        "file": artifact.name,
                        "expected": mismatch.expected,
                        "got": mismatch.got,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - one destination, not the run
                logger.warning("backup_ship: %s failed: %s", cfg.name, exc)
                summary["verify_failed"].append(cfg.name)
                await _journal_verify_failed(
                    session_factory,
                    {
                        "destination": cfg.name,
                        "family": "dump",
                        "file": artifact.name,
                        "error": str(exc),
                    },
                )
            else:
                summary["shipped"] += 1
                await _journal_shipped(
                    session_factory,
                    {
                        "destination": cfg.name,
                        "family": "dump",
                        "file": artifact.name,
                        "bytes": artifact.stat().st_size,
                        "sha256": expected,
                        "elapsed_seconds": round(time.monotonic() - started, 3),
                    },
                )

            # Retention runs whatever this snapshot did: the failure is about
            # tonight's upload, not about the copies already on the destination.
            # A destination that could not be built at all has nothing to prune.
            if destination is None:
                attachments["verify_failed"].append(cfg.name)
                continue
            try:
                summary["pruned"][cfg.name] = await destination.prune(
                    cfg.retention_keep, DUMPS
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("backup_ship: %s prune failed: %s", cfg.name, exc)
                summary["pruned"][cfg.name] = {"error": str(exc)}

            try:
                needs = changed or not await _destination_holds(
                    destination, archive_stamp, outcomes.get(cfg.name)
                )
            except Exception as exc:  # noqa: BLE001 - an unlistable destination
                logger.warning(
                    "backup_ship: %s attachment listing failed: %s", cfg.name, exc
                )
                needs = True

            if needs:
                tarball: Path | None = None
                attachment_started = time.monotonic()
                try:
                    if archive is None:
                        archive = await build_archive(
                            dump.parent, archive_stamp, expect_rows=expect_rows
                        )
                        attachments["built"] = True
                        archive_artifacts = await _artifacts_for(
                            archive, [c.age_recipient for c in enabled]
                        )
                    tarball = archive_artifacts[cfg.age_recipient]
                    await destination.ship(
                        tarball, timeout=ATTACHMENTS_SHIP_TIMEOUT_SECONDS
                    )
                    expected = await sha256_file(tarball)
                    got = await destination.read_back_sha256(
                        tarball.name, timeout=ATTACHMENTS_READ_BACK_TIMEOUT_SECONDS
                    )
                    if got != expected:
                        raise VerifyMismatch(expected=expected, got=got)
                except VerifyMismatch as mismatch:
                    attachments["verify_failed"].append(cfg.name)
                    await _journal_verify_failed(
                        session_factory,
                        {
                            "destination": cfg.name,
                            "family": "attachments",
                            "stamp": archive_stamp,
                            "file": tarball.name if tarball else None,
                            "expected": mismatch.expected,
                            "got": mismatch.got,
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "backup_ship: %s attachments failed: %s", cfg.name, exc
                    )
                    attachments["verify_failed"].append(cfg.name)
                    await _journal_verify_failed(
                        session_factory,
                        {
                            "destination": cfg.name,
                            "family": "attachments",
                            "stamp": archive_stamp,
                            "file": tarball.name if tarball else None,
                            "error": str(exc),
                        },
                    )
                else:
                    archive_shipped = True
                    attachments["shipped"] += 1
                    await _journal_shipped(
                        session_factory,
                        {
                            "destination": cfg.name,
                            "family": "attachments",
                            "stamp": archive_stamp,
                            "file": tarball.name,
                            "bytes": tarball.stat().st_size,
                            "sha256": expected,
                            "elapsed_seconds": round(
                                time.monotonic() - attachment_started, 3
                            ),
                        },
                    )
            else:
                attachments["skipped"].append(cfg.name)

            try:
                attachments["pruned"][cfg.name] = await destination.prune(
                    cfg.attachments_retention_keep, ATTACHMENTS
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "backup_ship: %s attachment prune failed: %s", cfg.name, exc
                )
                attachments["pruned"][cfg.name] = {"error": str(exc)}
    finally:
        scratch = dump.parent / _SCRATCH
        if scratch.exists():
            await asyncio.to_thread(shutil.rmtree, scratch, True)
        if not keep_plaintext:
            # Every destination demanded encryption; an unencrypted twin must
            # not outlive the run on local disk.
            dump.unlink(missing_ok=True)
            if archive is not None:
                archive.unlink(missing_ok=True)

    if archive_shipped:
        async with session_factory() as session:
            await save_state(
                session, ArchiveState(stamp=archive_stamp, manifest_hash=manifest)
            )

    return summary
```

The imports above already bind `ATTACHMENTS`, `DUMPS`, `ArchiveIncomplete`,
`ArchiveState`, `load_state`, `save_state` and `manifest_hash` as module
attributes of `backup_ship`, which is how the tests reach them. The module has
no `__all__`; do not add one.

- [ ] **Step 4: Run test to verify it passes**

```bash
TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_ship.py tests/test_backups_inventory.py \
  tests/test_events.py
```

Expected: all passed. `test_events.py` matters here: it scans `record_event`
call sites, and the two journal helpers must still resolve their event type at
the call site.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/backup_ship.py backend/tests/test_backup_ship.py
git commit -m "feat(backup): ship the attachment set off-host"
```

---
### Task 7: The `backup.sh` tarball stage

**Files:**
- Modify: `scripts/backup.sh` (append a stage after the existing retention block)
- Test: `backend/tests/test_backup_script.py`

**Interfaces:**
- Consumes: Task 1's `MANIFEST_SQL` and `COUNT_SQL` — the shell carries the same literals, and a test pins the two spellings together.
- Produces: `darkmem-attachments-<stamp>.tar.gz` and its `.manifest` sidecar — see Contracts.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

Risk 3: this stage prunes files in the directory that holds the only local
copy of the database, and its silent-failure mode — an empty volume archived
under the canonical name — makes every later night skip.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_backup_script.py`, make three edits before adding
anything.

**1. The existing exact-directory assertion** in
`test_a_successful_dump_lands_under_the_retention_name` (`:94`), which the
tarball and its sidecar now violate:

```python
    assert list(dest.iterdir()) == [dump]
```

becomes

```python
    assert _dumps(dest) == [dump]
```

**2. `_run_backup` must never reach the host's real `docker`.** It sets only
`COMPOSE_CMD` today (`:63-73`), so after this task every pre-existing test would
run `docker run -v darkmem-prod_attachment_data:/src:ro` against the live
production volume on this host, and would go red on a host with no docker at
all. Give it a stub and a throwaway volume name:

```python
def _run_backup(dest: Path, compose: Path, keep: str | None = None):
    env = {
        **os.environ,
        "COMPOSE_CMD": str(compose),
        # Never the host's docker: the default ATTACHMENT_VOLUME is the live
        # production volume, and `docker run -v NAME` would reach it for real.
        "DOCKER_CMD": str(_docker_stub(compose.parent, _volume(compose.parent))),
        "ATTACHMENT_VOLUME": "test_attachment_data",
        "DARKMEM_IMAGE": "darkraise/darkmem:test",
    }
    if keep is not None:
        env["BACKUP_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
```

**3. `_good_compose` answers every invocation with the dump body**, which would
make the manifest a multi-line SQL script. Define it in terms of the
argv-dispatching stub below:

```python
def _good_compose(tmp_path: Path) -> Path:
    return _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1)
```

`_failing_compose` and `_truncated_compose` need **no** change: both fail the
dump, and the attachment stage never runs after a failed dump.

Then append:

```python
# ── Task 7: the attachment tarball stage ─────────────────────────────

from app.services.attachment_manifest import COUNT_SQL, MANIFEST_SQL  # noqa: E402

TAR_GLOB = "darkmem-attachments-*.tar.gz"
MANIFEST_A = "a" * 64
MANIFEST_B = "b" * 64


def _tars(dest: Path) -> list[Path]:
    return sorted(dest.glob(TAR_GLOB))


def _attachment_compose(tmp_path: Path, *, manifest: str, rows: int) -> Path:
    """A compose stub that tells the three queries apart.

    The shipped stub answers every invocation with the dump body, which would
    make the "manifest" a multi-line SQL script and the gate meaningless.
    """
    body = (
        'for a in "$@"; do\n'
        '  case "$a" in\n'
        f"    *'count(*)'*) echo '{rows}'; exit 0 ;;\n"
        f"    *string_agg*) echo '{manifest}'; exit 0 ;;\n"
        "  esac\n"
        "done\n"
        f"cat <<'SQL'\n{DUMP_BODY}{DUMP_TAIL}SQL\n"
    )
    return _stub(tmp_path, "compose-attach.sh", body)


def _docker_stub(tmp_path: Path, volume_dir: Path | None) -> Path:
    """Stands in for `docker`. `volume inspect` fails when the fixture
    directory is absent, which is how a missing volume is simulated."""
    missing = "exit 1" if volume_dir is None else "exit 0"
    src = str(volume_dir) if volume_dir else "/nonexistent"
    body = (
        'case "$1" in\n'
        f"  volume) {missing} ;;\n"
        "  run)\n"
        f"    exec tar -czvf - -C '{src}' --exclude='*.part' "
        "--exclude='./.staging' --ignore-failed-read "
        "--warning=no-file-changed .\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n"
    )
    return _stub(tmp_path, "docker-stub.sh", body)


def _volume(tmp_path: Path, *, files: int = 1) -> Path:
    # exist_ok: `_run_backup` builds this on every call, and
    # `test_retention_never_deletes_a_real_dump_to_keep_a_failure_artefact`
    # runs twice against one tmp_path.
    store = tmp_path / "volume"
    (store / "ab").mkdir(parents=True, exist_ok=True)
    for index in range(files):
        (store / "ab" / f"file{index}").write_bytes(b"payload")
    return store


def _run_with_attachments(dest, compose, docker, *, keep=None, env=None):
    merged = {
        **os.environ,
        "COMPOSE_CMD": str(compose),
        "DOCKER_CMD": str(docker),
        "ATTACHMENT_VOLUME": "test_attachment_data",
        "DARKMEM_IMAGE": "darkraise/darkmem:test",
        **(env or {}),
    }
    if keep is not None:
        merged["BACKUP_ATTACHMENTS_KEEP"] = keep
    return subprocess.run(
        ["bash", str(BACKUP), str(dest)],
        env=merged, capture_output=True, text=True, timeout=180,
    )


def test_the_shell_carries_the_same_manifest_sql_as_the_module():
    """Two producers, one definition. A drift here is a manifest that never
    matches, which silently re-tars the whole volume every night."""
    script = BACKUP.read_text()
    assert " ".join(MANIFEST_SQL.split()) in " ".join(script.split())
    assert " ".join(COUNT_SQL.split()) in " ".join(script.split())


def test_a_changed_manifest_writes_a_tarball_and_a_sidecar(dest, tmp_path):
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, _volume(tmp_path)),
    )
    assert result.returncode == 0, result.stderr

    (tarball,) = _tars(dest)
    assert (dest / f"{tarball.name}.manifest").read_text().strip() == MANIFEST_A
    assert len(_dumps(dest)) == 1
    assert not list(dest.glob("*.part"))


def test_an_unchanged_manifest_writes_no_second_tarball(dest, tmp_path):
    compose = _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1)
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    assert _run_with_attachments(dest, compose, docker).returncode == 0
    time.sleep(1.1)
    assert _run_with_attachments(dest, compose, docker).returncode == 0

    assert len(_tars(dest)) == 1
    assert len(_dumps(dest)) == 2


def test_a_moved_manifest_writes_a_second_tarball(dest, tmp_path):
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    assert _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1), docker
    ).returncode == 0
    time.sleep(1.1)
    assert _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_B, rows=1), docker
    ).returncode == 0

    assert len(_tars(dest)) == 2


def test_an_empty_volume_against_rows_fails_and_keeps_the_dump(dest, tmp_path):
    empty = tmp_path / "empty-volume"
    empty.mkdir()
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=4),
        _docker_stub(tmp_path, empty),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1, "the dump must survive an attachment failure"


def test_a_missing_volume_fails_and_keeps_the_dump(dest, tmp_path):
    result = _run_with_attachments(
        dest,
        _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1),
        _docker_stub(tmp_path, None),
    )

    assert result.returncode != 0
    assert _tars(dest) == []
    assert len(_dumps(dest)) == 1


def test_a_file_changed_under_tar_is_not_a_failure(dest, tmp_path):
    """tar exits 1 for "file changed as we read it", the expected outcome
    against a live volume the cleanup job may be unlinking from. Under
    `set -euo pipefail` an unhandled 1 would fail the backup nightly."""
    volume = _volume(tmp_path)
    docker = _stub(
        tmp_path,
        "docker-changed.sh",
        'case "$1" in\n'
        "  volume) exit 0 ;;\n"
        "  run)\n"
        f"    tar -czvf - -C '{volume}' .\n"
        "    exit 1\n"
        "    ;;\n"
        "esac\n"
        "exit 0\n",
    )

    result = _run_with_attachments(
        dest, _attachment_compose(tmp_path, manifest=MANIFEST_A, rows=1), docker
    )

    assert result.returncode == 0, result.stderr
    assert len(_tars(dest)) == 1


def test_keep_zero_disables_the_tarball_prune(dest, tmp_path):
    """Same convention as the dump prune's KEEP=0, for a one-off manual run."""
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    for manifest in (MANIFEST_A, MANIFEST_B, "c" * 64):
        assert _run_with_attachments(
            dest,
            _attachment_compose(tmp_path, manifest=manifest, rows=1),
            docker,
            keep="0",
        ).returncode == 0
        time.sleep(1.1)

    assert len(_tars(dest)) == 3


def test_tarball_retention_prunes_sidecars_and_spares_dumps(dest, tmp_path):
    docker = _docker_stub(tmp_path, _volume(tmp_path))
    for manifest in (MANIFEST_A, MANIFEST_B, "c" * 64):
        assert _run_with_attachments(
            dest,
            _attachment_compose(tmp_path, manifest=manifest, rows=1),
            docker,
            keep="2",
        ).returncode == 0
        time.sleep(1.1)

    assert len(_tars(dest)) == 2
    assert len(list(dest.glob("*.manifest"))) == 2
    assert len(_dumps(dest)) == 3
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && .venv/bin/python -m pytest -q tests/test_backup_script.py
```

Expected: FAIL — the SQL-parity test finds no `string_agg` in the script, and no tarball is written.

- [ ] **Step 3: Write the implementation**

Append to `scripts/backup.sh`, after the final `echo "Copy this file to
off-host storage."`:

```bash
# ── Attachments ───────────────────────────────────────────────────────
#
# pg_dump alone leaves out every attachment, so the volume is backed up as a
# second artefact family -- a whole-set tarball, written only when the set
# changed, so an unchanged multi-gigabyte volume is not copied nightly.
#
# The dump above is already on disk and already pruned, and nothing here may
# unwind it. The stage runs in a subshell with its own errexit (an `if !`
# guard around a plain function would disable errexit inside it) and reports
# through its exit status, which is read at the very end.
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

    # Directories end in '/' in tar's listing; everything else is a member.
    MEMBERS="$(grep -c -v '/$' "$TAR_LIST" || true)"
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

if ! attachment_stage; then
    echo "Attachment backup FAILED. The database dump above is intact." >&2
    exit 1
fi
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && .venv/bin/python -m pytest -q tests/test_backup_script.py
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add scripts/backup.sh backend/tests/test_backup_script.py
git commit -m "feat(backup): tar the attachment volume nightly"
```

---

### Task 8: The worker surface: receiver pattern and attachment mount

**Files:**
- Modify: `backend/app/worker_receiver.py` (`SNAPSHOT_NAME` at `:38`)
- Modify: `docker-compose.worker.yml` (service `darkmem`: `environment`, `volumes`)
- Test: `backend/tests/test_worker_receiver.py`, `backend/tests/test_deployment_artifact.py`

**Interfaces:**
- Consumes: the artefact names Task 6 ships and Task 7 writes — see Contracts.
- Produces: `ATTACHMENTS_DIR` on the worker, pointing at `current` — Task 9 maintains that symlink.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 2 - spec 0 - coupling 0 - risk 1 = 3

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_worker_receiver.py`:

```python
# ── Attachment tarballs are a second family, not a looser pattern ────

ATTACHMENT_NAMES = [
    "darkmem-app-attachments-20260101-000000.tar.gz",
    "darkmem-app-attachments-20260101-000000.tar.gz.age",
]

# `darkmem-app-attachments-<stamp>.sql.gz` is deliberately NOT here: the dump
# alternative's `[A-Za-z0-9._-]+` matches `attachments-<stamp>`, so the receiver
# accepts it. Nothing produces that name, and accepting it costs nothing --
# tightening the stamp shape to refuse it would also refuse a dump an operator
# renamed by hand, which is the case this pattern is lenient for.
REFUSED_NAMES = [
    "darkmem-app-attachments-20260101-000000.tar.gz.part",
    "darkmem-app-20260101-000000.tar.gz",
    "../etc/passwd",
    "sub/dir.tar.gz",
    "darkmem-attachments-20260101-000000.tar.gz",
]


@pytest.mark.parametrize("name", ATTACHMENT_NAMES)
def test_the_receiver_accepts_an_attachment_tarball(name):
    assert worker_receiver.SNAPSHOT_NAME.match(name)


@pytest.mark.parametrize("name", REFUSED_NAMES)
def test_the_receiver_still_refuses_everything_else(name):
    assert not worker_receiver.SNAPSHOT_NAME.match(name)


def test_the_receiver_still_accepts_a_dump():
    assert worker_receiver.SNAPSHOT_NAME.match(
        "darkmem-app-20260101-000000.sql.gz.age"
    )
```

Append to `backend/tests/test_deployment_artifact.py`:

```python
# ── The worker serves attachments from a restored generation ─────────


def test_the_worker_mounts_an_attachment_store_read_only():
    service = _compose(WORKER_COMPOSE)["services"]["darkmem"]
    mounts = [v for v in service["volumes"] if "attachment-store" in v]
    assert len(mounts) == 1, service["volumes"]
    assert mounts[0].endswith(":/app/data/attachment-store:ro"), mounts[0]


def test_the_worker_points_attachments_dir_at_the_current_generation():
    service = _compose(WORKER_COMPOSE)["services"]["darkmem"]
    assert (
        "ATTACHMENTS_DIR=/app/data/attachment-store/current" in service["environment"]
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_worker_receiver.py tests/test_deployment_artifact.py
```

Expected: FAIL on the tarball names and on both compose assertions.

- [ ] **Step 3: Write the implementation**

In `backend/app/worker_receiver.py`, replace `SNAPSHOT_NAME`:

```python
#: Exactly the two artefact families increment 6 produces, each anchored. Two
#: alternatives rather than one loosened pattern: a name that cannot contain a
#: separator cannot traverse whatever else it contains, and refusing every
#: other shape is what keeps this from becoming a general-purpose file drop.
SNAPSHOT_NAME = re.compile(
    r"^darkmem-app-[A-Za-z0-9._-]+\.sql\.gz(\.age)?$"
    r"|^darkmem-app-attachments-[A-Za-z0-9._-]+\.tar\.gz(\.age)?$"
)
```

In `docker-compose.worker.yml`, under service `darkmem`, add to `environment`:

```yaml
      # The generation the restore loop last swapped in. A relative symlink,
      # because the host and container paths differ.
      - ATTACHMENTS_DIR=/app/data/attachment-store/current
```

and to `volumes`:

```yaml
      # Read-only: the app serves attachments and never writes one here. The
      # host-side restore loop is the writer, which is why this is a bind mount
      # rather than a named volume. Create it before first boot:
      #   sudo install -d -o "$APP_UID" -g "$APP_UID" -m 0750 /srv/darkmem-attachments
      - ${DARKMEM_ATTACHMENT_DIR:-/srv/darkmem-attachments}:/app/data/attachment-store:ro
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_worker_receiver.py tests/test_deployment_artifact.py
```

Expected: all passed — including the pre-existing worker-count and
`--no-proxy-headers` scans, which are parametrised over all three compose files.

- [ ] **Step 5: Commit**

```bash
git add backend/app/worker_receiver.py docker-compose.worker.yml \
  backend/tests/test_worker_receiver.py backend/tests/test_deployment_artifact.py
git commit -m "feat(worker): accept and serve attachment tarballs"
```

---
### Task 9: The worker restore cycle

**Files:**
- Modify: `scripts/worker/restore-cycle.sh`
- Test: `backend/tests/test_deployment_artifact.py` (extends the existing `_run_cycle` harness)

**Interfaces:**
- Consumes: the artefact names and stamps Task 6 ships and Task 8's mount — see Contracts.
- Produces: the `gen-<stamp>` / `current` layout the worker's `ATTACHMENTS_DIR` reads.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

Risk 3: this script drops and renames the database the viewer is serving, and
the new code runs beside that window. A failure between the rename and the
symlink swap leaves restored rows pointing at the previous generation's files.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_deployment_artifact.py`, extend the age stub so it can
write to stdout (the unpack pipes rather than using `-o`):

```python
_AGE_STUB = """#!/usr/bin/env bash
# Stand-in for `age -d -i IDENTITY [-o OUT] IN`: copies IN to OUT, or to
# stdout when no -o is given, which is how the attachment unpack reads it.
out=""; last=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -d|-i) shift; [ "$1" != "" ] && [ "${1#-}" = "$1" ] && shift ;;
    *) last="$1"; shift ;;
  esac
done
if [ -n "$out" ]; then cp "$last" "$out"; else cat "$last"; fi
"""
```

Add the attachment fixtures and point the harness at a store. `_run_cycle`
changes in exactly three places — its signature, a loop after `dumps.mkdir`,
and one entry in `env.update`. Leave every other line of it as it is:

```python
def _run_cycle(
    tmp_path: Path, *, snapshot: str | None, complete: bool = True,
    migrate_ok: bool = True, attachments: tuple[tuple[str, str], ...] = (),
) -> tuple[subprocess.CompletedProcess, list[list[str]], Path]:
    dumps = tmp_path / "dumps"
    dumps.mkdir(exist_ok=True)
    for stamp, marker in attachments:
        _write_tarball(tmp_path, dumps, stamp, marker)
    if snapshot:
        ...unchanged...
```

and, inside the existing `env.update(...)` call, one more keyword:

```python
        ATTACHMENT_STORE=str(tmp_path / "attachments"),
```

and the fixture writer beside it:

```python
def _write_tarball(tmp_path: Path, dumps: Path, stamp: str, marker: str) -> None:
    """A real gzipped tar whose one member names the generation, so a test can
    read back *which* set was unpacked rather than only that something was."""
    source = tmp_path / f"src-{stamp}"
    (source / "ab").mkdir(parents=True, exist_ok=True)
    (source / "ab" / "marker").write_text(marker)
    target = dumps / f"darkmem-app-attachments-{stamp}.tar.gz.age"
    with tarfile.open(target, "w:gz") as archive:
        archive.add(source, arcname=".")
```

Add `import tarfile` to the file's imports. Then append the tests:

```python
DUMP_0102 = "darkmem-app-20260102-000000.sql.gz.age"


def _store(tmp_path: Path) -> Path:
    return tmp_path / "attachments"


def test_the_cycle_unpacks_the_tarball_paired_with_the_dump(tmp_path):
    result, records, _ = _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "older-set"),
            ("20260103-000000", "newer-than-the-dump"),
        ),
    )
    assert result.returncode == 0, result.stderr

    store = _store(tmp_path)
    assert os.readlink(store / "current") == "gen-20260101-000000"
    assert (store / "current" / "ab" / "marker").read_text() == "older-set"


def test_a_missing_tarball_still_restores_the_database(tmp_path):
    result, records, state = _run_cycle(tmp_path, snapshot=SNAPSHOT)

    assert result.returncode == 0, result.stderr
    assert state.read_text().strip() == SNAPSHOT
    assert not (_store(tmp_path) / "current").exists()
    assert _index_of(records, lambda f: "ALTER" in " ".join(f)) >= 0


def test_the_attachments_only_path_leaves_the_database_alone(tmp_path):
    _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )
    # The database is current; only a newer attachment set arrived.
    result, records, _ = _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "first"),
            ("20260102-000000", "second"),
        ),
    )

    assert result.returncode == 0, result.stderr
    assert os.readlink(_store(tmp_path) / "current") == "gen-20260102-000000"
    assert not any("stop" in " ".join(fields) for fields in records)
    assert not any("ALTER" in " ".join(fields) for fields in records)


def test_the_cycle_removes_the_generations_it_replaced(tmp_path):
    _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )
    _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "first"),
            ("20260102-000000", "second"),
        ),
    )

    generations = sorted(p.name for p in _store(tmp_path).glob("gen-*"))
    assert generations == ["gen-20260102-000000"]


def test_a_leftover_current_tmp_does_not_break_the_swap(tmp_path):
    """A cycle killed between `ln -s` and `mv -T` leaves current.tmp behind,
    and the next `ln -s` would fail under errexit -- inside the window where
    the database has already been renamed."""
    store = _store(tmp_path)
    store.mkdir(parents=True)
    (store / "current.tmp").symlink_to("gen-does-not-exist")

    result, _, _ = _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )

    assert result.returncode == 0, result.stderr
    assert os.readlink(store / "current") == "gen-20260101-000000"


def test_both_halves_current_is_a_no_op(tmp_path):
    args = dict(snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),))
    _run_cycle(tmp_path, **args)
    result, records, _ = _run_cycle(tmp_path, **args)

    assert result.returncode == 0, result.stderr
    assert records == []
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_deployment_artifact.py -k cycle
```

Expected: FAIL — no `current` symlink is ever created.

- [ ] **Step 3: Write the implementation**

In `scripts/worker/restore-cycle.sh`, add to the configuration block:

```bash
ATTACHMENT_STORE="${ATTACHMENT_STORE:-/srv/darkmem-attachments}"
```

Add three helpers below `psql_owner()`:

```bash
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
```

Replace section 1's "already serving" block (from `if [ "$NEWEST" = "$SERVING" ]`
through its `fi`) with the pairing and the two-halves predicate:

```bash
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
    echo "Now serving $NEWEST and ${WANT_GEN:-no attachment generation}."
    exit 0
fi

echo "Restoring $NEWEST${PAIRED:+ with $PAIRED}"
```

Delete the old `echo "Restoring $NEWEST"` line that followed the block.

At the end of section 5, after `STAGE="side_granted"`, add:

```bash
# Unpacked while the viewer still serves the previous generation: a failure
# here costs nothing, and the swap below is then a symlink move.
unpack_generation
```

In section 6, between the `ALTER DATABASE ... RENAME` and `$COMPOSE start`:

```bash
swap_generation
```

and after `STAGE="swapped"`:

```bash
prune_generations
```

Extend the `app_stopped` branch of `cleanup()` with the symlink step, so an
operator finishing by hand does not restart the app on the previous generation:

```bash
            if [ -n "${WANT_GEN:-}" ]; then
                echo "  ln -s $WANT_GEN $ATTACHMENT_STORE/current.tmp && mv -T $ATTACHMENT_STORE/current.tmp $ATTACHMENT_STORE/current" >&2
            fi
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_deployment_artifact.py
```

Expected: all passed, including the pre-existing restore-cycle ordering tests.

- [ ] **Step 5: Commit**

```bash
git add scripts/worker/restore-cycle.sh backend/tests/test_deployment_artifact.py
git commit -m "feat(worker): restore attachments in generations"
```

---

### Task 10: Pulling the other half

**Files:**
- Modify: `backend/app/services/backup_pull.py` (`pull` at `:61-108`, `_main` at `:110-131`)
- Modify: `scripts/restore.sh` (after the `--from` pull block at `:48-67`)
- Create: `backend/tests/test_backup_pull.py`

**Interfaces:**
- Consumes: Task 3's family-taking `list_snapshots`, Task 2's `ATTACHMENTS` / `DUMPS` — see Contracts.
- Produces: `pull(..., family=...)` and the two CLI flags — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_backup_pull.py`:

```python
"""Fetching a snapshot back off a destination, in both families (spec §5.2).

The pairing rule is the load-bearing one: a restore that takes the *newest*
tarball rather than the newest at or before its dump serves files the dump's
own rows never referenced.
"""
from __future__ import annotations

import hashlib

import pytest

from app.services import backup_pull
from app.services.attachment_archive import ATTACHMENTS


class _Holding:
    """A destination whose contents are a dict. `read_back_sha256` derives
    from the same bytes `stream` serves, as every real kind does."""

    name = "nas"
    retention_keep = 14
    attachments_retention_keep = 3

    def __init__(self, objects: dict[str, bytes]):
        self.objects = objects

    async def list_snapshots(self, family=None):
        family = family or backup_pull.DUMPS
        return [
            backup_pull.SnapshotInfo(
                name=n, size=len(b), modified_at=family.stamp_datetime(n)
            )
            for n, b in sorted(self.objects.items())
            if family.matches(n)
        ]

    async def stream(self, name: str):
        yield self.objects[name]

    async def read_back_sha256(self, name: str) -> str:
        return hashlib.sha256(self.objects[name]).hexdigest()


def _holding(objects: dict[str, bytes]) -> _Holding:
    return _Holding(objects)

DUMP_0102 = "darkmem-app-20260102-000000.sql.gz.age"
TAR_0101 = "darkmem-app-attachments-20260101-000000.tar.gz.age"
TAR_0103 = "darkmem-app-attachments-20260103-000000.tar.gz.age"


async def test_pull_defaults_to_the_dump_family(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"tar"})
    out = await backup_pull.pull(destination, name=None, out_dir=tmp_path)
    assert out.name == DUMP_0102


async def test_pull_can_take_the_attachment_family(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"tar"})
    out = await backup_pull.pull(
        destination, name=None, out_dir=tmp_path, family=ATTACHMENTS
    )
    assert out.name == TAR_0103


async def test_paired_with_picks_the_newest_at_or_before_the_dump(tmp_path):
    destination = _holding(
        {DUMP_0102: b"dump", TAR_0101: b"older", TAR_0103: b"newer"}
    )
    chosen = await backup_pull.paired_name(destination, DUMP_0102)
    assert chosen == TAR_0101


async def test_paired_with_raises_when_nothing_pairs(tmp_path):
    destination = _holding({DUMP_0102: b"dump", TAR_0103: b"newer"})
    with pytest.raises(backup_pull.SnapshotNotFound):
        await backup_pull.paired_name(destination, DUMP_0102)
```

`backup_pull` must expose `DUMPS` and `SnapshotInfo` as module attributes for
that stub. Step 3's import line binds `DUMPS`, and `SnapshotInfo` comes with
`from app.services.backup_ship import SnapshotInfo, build_destination` — widen
the existing `build_destination` import to include it.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_pull.py
```

Expected: FAIL — `pull() got an unexpected keyword argument 'family'`.

Widen the pre-existing `_PullSource` in `tests/test_backup_ship.py:990-1010`
at the same time: its `list_snapshots(self)` takes no family, so the five
existing pull tests would raise `TypeError` the moment `pull` passes one.

```python
    async def list_snapshots(self, family=None):
        family = family or backup_ship.DUMPS
        return [
            backup_ship.SnapshotInfo(
                name=n, size=len(b), modified_at=family.stamp_datetime(n)
            )
            for n, b in sorted(self._files.items())
            if family.matches(n)
        ]
```

- [ ] **Step 3: Write the implementation**

In `backend/app/services/backup_pull.py`, add the import and two changes:

```python
from app.services.attachment_archive import ATTACHMENTS, DUMPS, Family
```

```python
async def paired_name(destination, dump_name: str) -> str:
    """The attachment tarball that goes with `dump_name`.

    The newest set captured at or before the dump. Correct because an unchanged
    set writes no tarball, so the newest at or before a dump is what was live
    when it was taken. The stamp is zero-padded and big-endian, so this is a
    lexical comparison and no mtime is trusted.
    """
    stamp = DUMPS.stamp_of(dump_name)
    if stamp is None:
        raise SnapshotNotFound(f"{dump_name!r} is not a dump this job produced")
    candidates = [
        s.name
        for s in await destination.list_snapshots(ATTACHMENTS)
        if (ATTACHMENTS.stamp_of(s.name) or "") <= stamp
    ]
    if not candidates:
        raise SnapshotNotFound(
            f"{destination.name} holds no attachment tarball at or before "
            f"{stamp}; restoring this dump serves rows whose files are gone"
        )
    return max(candidates)


async def pull(
    destination, *, name: str | None, out_dir: Path, family: Family = DUMPS
) -> Path:
```

Inside `pull`, change the listing call and both error messages to use the
family:

```python
    snapshots = await destination.list_snapshots(family)
    if not snapshots:
        raise SnapshotNotFound(f"{destination.name} holds no {family.prefix}* artefact")
```

In `_main`, add the two flags and route them:

```python
    parser.add_argument(
        "--family", choices=("dump", "attachments"), default="dump",
        help="which artefact family to fetch",
    )
    group.add_argument(
        "--paired-with",
        help="the dump whose attachment tarball to fetch (implies --family attachments)",
    )
```

```python
    destination = await _destination_for(args.destination)
    if args.paired_with:
        path = await pull(
            destination,
            name=await paired_name(destination, args.paired_with),
            out_dir=Path(args.out),
            family=ATTACHMENTS,
        )
    else:
        family = ATTACHMENTS if args.family == "attachments" else DUMPS
        path = await pull(
            destination,
            name=None if args.latest else args.name,
            out_dir=Path(args.out),
            family=family,
        )
```

In `scripts/restore.sh`, after `echo "Pulled $BACKUP_FILE"`, add:

```bash
    # The dump is half a backup. Naming the exact command here rather than in
    # the runbook alone, because this is where the operator already is.
    echo
    echo "This restores the database only. For its attachments, run:"
    echo "  $COMPOSE exec -T $APP_SERVICE python -m app.services.backup_pull \\"
    echo "      --destination $FROM --paired-with $(basename "$CONTAINER_PATH") --out /dumps"
    echo "  then unpack it (docs/runbook-deployment.md, Attachments), and run"
    echo "  $COMPOSE exec -T $APP_SERVICE python -m app.services.attachment_verify"
    echo
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backup_pull.py tests/test_backup_ship.py
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/backup_pull.py scripts/restore.sh backend/tests/test_backup_pull.py
git commit -m "feat(backup): pull the paired attachment tarball"
```

---
### Task 11: The inventory route

**Files:**
- Modify: `backend/app/api/routes/backups.py` (`DestinationInventory` at `:47-62`, `_LAST_OUTCOMES` at `:65-78`, `_last_outcomes` at `:76-110`, `backup_inventory` at `:113-150`)
- Test: `backend/tests/test_backups_inventory.py`

**Interfaces:**
- Consumes: Task 3's family-taking `list_snapshots`, Task 5's `attachments_retention_keep`, Task 6's `"family"` payload key — see Contracts.
- Produces: the three response fields Task 12 types — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-high
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 1 = 3

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_backups_inventory.py`:

```python
# ── Both families, and an outcome per family ─────────────────────────

TAR = "darkmem-app-attachments-20260101-000000.tar.gz.age"
DUMP = "darkmem-app-20260101-000000.sql.gz.age"


async def _journal(session, event_type, payload):
    await session.execute(
        sa_text(
            "INSERT INTO events (event_type, object_type, source, payload) "
            "VALUES (:t, 'system', 'backup_ship', CAST(:p AS jsonb))"
        ),
        {"t": event_type, "p": json.dumps(payload)},
    )


async def test_the_inventory_lists_both_families(session, client, auth_headers, monkeypatch):
    await bc.save_destinations(session, {"destinations": [LOCAL]})
    monkeypatch.setattr(
        "app.api.routes.backups.build_destination",
        lambda cfg: _Listing("disk", [DUMP, TAR]),
    )

    body = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()
    row = body["destinations"][0]

    assert [s["name"] for s in row["snapshots"]] == [DUMP]
    assert [s["name"] for s in row["attachment_snapshots"]] == [TAR]
    assert row["attachments_retention_keep"] == 3


async def test_a_tarball_outcome_does_not_mask_the_dump_outcome(
    session, client, auth_headers, monkeypatch
):
    """One DISTINCT ON per destination would let the attachment row, written
    second, overwrite the dump's -- and the dump's outcome is the one an
    operator reads before restoring."""
    await bc.save_destinations(session, {"destinations": [LOCAL]})
    monkeypatch.setattr(
        "app.api.routes.backups.build_destination",
        lambda cfg: _Listing("disk", [DUMP, TAR]),
    )
    await _journal(session, "backup_shipped", {"destination": "disk", "family": "dump", "sha256": "ab"})
    await _journal(
        session,
        "backup_verify_failed",
        {"destination": "disk", "family": "attachments", "error": "truncated"},
    )
    await session.commit()

    row = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()["destinations"][0]

    assert row["last_outcome"]["event_type"] == "backup_shipped"
    assert row["last_attachment_outcome"]["event_type"] == "backup_verify_failed"
    assert row["last_attachment_outcome"]["error"] == "truncated"


async def test_a_pre_family_row_still_reads_as_a_dump(
    session, client, auth_headers, monkeypatch
):
    await bc.save_destinations(session, {"destinations": [LOCAL]})
    monkeypatch.setattr(
        "app.api.routes.backups.build_destination", lambda cfg: _Listing("disk", [DUMP])
    )
    await _journal(session, "backup_shipped", {"destination": "disk", "sha256": "ab"})
    await session.commit()

    row = (
        await client.get("/api/v1/backups/inventory", headers=auth_headers)
    ).json()["destinations"][0]

    assert row["last_outcome"]["sha256"] == "ab"
    assert row["last_attachment_outcome"] is None
```

Two edits to the existing file go with these tests.

`_Listing` (`:39-48`) and `_Unreachable` (`:50-56`) both declare
`list_snapshots(self)`; widen both, or the route's `DUMPS` argument turns
`_Unreachable`'s intended "unplugged" message into a `TypeError` and
`test_one_unreachable_destination_does_not_blank_the_inventory` fails:

`_Listing` stores `self._names`, a list of **strings**, and builds its
`SnapshotInfo` objects on the way out. Note this leaves `_stamp_of` unused on
that file's import line (`:19`) — drop it from the import, keeping
`SnapshotInfo`. The alias itself stays in `backup_ship` regardless: Task 3's
Contracts entry keeps it because removing a public name costs more than a
one-line forward, not only because this file imported it.

```python
    async def list_snapshots(self, family=None):
        family = family or DUMPS
        return [
            SnapshotInfo(name=n, size=100, modified_at=family.stamp_datetime(n))
            for n in self._names
            if family.matches(n)
        ]
```

`_Unreachable` gets **only** the parameter — its body stays
`raise RuntimeError("the NAS is unplugged")`, which is the whole point of the
unreachable test:

```python
    async def list_snapshots(self, family=None):
        raise RuntimeError("the NAS is unplugged")
```

and every new request needs the `auth_headers` fixture the existing tests use
(`:76-77`) — the route is behind `require_auth`, so an unauthenticated call
returns 401 and `.json()["destinations"]` raises `KeyError: 'destinations'`:

```python
async def test_the_inventory_lists_both_families(session, client, auth_headers, monkeypatch):
    ...
    body = (await client.get("/api/v1/backups/inventory", headers=auth_headers)).json()
```

Apply the same two changes to the other two new tests. Add `import json` and
`from app.services.attachment_archive import ATTACHMENTS, DUMPS` to the imports.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backups_inventory.py
```

Expected: FAIL — `KeyError: 'attachment_snapshots'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/api/routes/backups.py`, add the import:

```python
from app.services.attachment_archive import ATTACHMENTS, DUMPS
```

Add the three fields to `DestinationInventory`, below `last_outcome`:

```python
    attachments_retention_keep: int
    attachment_snapshots: list[SnapshotRow]
    #: Its own field rather than folded into `last_outcome`: the two artefacts
    #: fail independently, and an operator choosing a dump needs to know
    #: whether the set that pairs with it verified.
    last_attachment_outcome: OutcomeRow | None
```

Key the outcome query on both columns:

```python
_LAST_OUTCOMES = text(
    """
    SELECT DISTINCT ON (payload->>'destination', coalesce(payload->>'family', 'dump'))
           payload->>'destination' AS destination,
           coalesce(payload->>'family', 'dump') AS family,
           event_type,
           created_at,
           payload
      FROM events
     WHERE event_type IN (:shipped, :failed)
       AND object_type = 'system'
     ORDER BY payload->>'destination',
              coalesce(payload->>'family', 'dump'),
              created_at DESC,
              id DESC
    """
)
```

Change `_last_outcomes`'s return type and its one assignment:

```python
async def _last_outcomes(session: AsyncSession) -> dict[tuple[str, str], OutcomeRow]:
```

```python
        out[(row["destination"], row["family"])] = OutcomeRow.model_validate(
```

In `backup_inventory`, list both families and pass all three fields:

```python
        snapshots: list[SnapshotRow] = []
        attachment_snapshots: list[SnapshotRow] = []
        error: str | None = None
        try:
            destination = build_destination(cfg)
            snapshots = [
                SnapshotRow(name=s.name, size=s.size, modified_at=s.modified_at)
                for s in await destination.list_snapshots(DUMPS)
            ]
            attachment_snapshots = [
                SnapshotRow(name=s.name, size=s.size, modified_at=s.modified_at)
                for s in await destination.list_snapshots(ATTACHMENTS)
            ]
        except Exception as exc:  # noqa: BLE001 - one destination, not the page
            error = str(exc)
```

and in the `DestinationInventory(...)` construction:

```python
                retention_keep=cfg.retention_keep,
                attachments_retention_keep=cfg.attachments_retention_keep,
                snapshots=snapshots,
                attachment_snapshots=attachment_snapshots,
                last_outcome=outcomes.get((cfg.name, "dump")),
                last_attachment_outcome=outcomes.get((cfg.name, "attachments")),
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_backups_inventory.py tests/test_api/test_rest_conformance.py
```

Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/backups.py backend/tests/test_backups_inventory.py
git commit -m "feat(backup): serve both families on the inventory"
```

---

### Task 12: Inventory types and the outcome binding

**Files:**
- Modify: `frontend/src/hooks/api/use-backups-api.ts` (`BackupDestination` at `:42-55`, `DestinationInventory` at `:102-113`)
- Modify: `frontend/src/features/settings/use-backups-tab-binding.ts` (`recentOutcomes` at `:64-87`)
- Test: `frontend/src/features/settings/__tests__/backups.test.tsx`

**Interfaces:**
- Consumes: Task 11's three response fields and Task 6's `"family"` payload key — see Contracts.
- Produces: `outcomeKey` and the typed fields Task 13 renders — see Contracts.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 2 = 4

Risk 2: `recentOutcomes` is read by every destination row, and the failure is
silent — the wrong badge on a backup nobody checks until they need it.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/features/settings/__tests__/backups.test.tsx`:

```tsx
import { renderHook, waitFor as waitForHook } from "@testing-library/react"

import { outcomeKey, useBackupsTabBinding } from "../use-backups-tab-binding"

const SHIPPED_DUMP = {
  id: 2,
  created_at: "2026-09-01T04:30:00Z",
  event_type: "backup_shipped",
  object_type: "system",
  object_id: null,
  project: null,
  actor: null,
  api_key_id: null,
  source: "backup_ship",
  payload: { destination: "disk", family: "dump", sha256: "a".repeat(64) },
}

const FAILED_TARBALL = {
  ...SHIPPED_DUMP,
  id: 3,
  // One second later, in the same run: a map keyed on destination alone would
  // let this overwrite the dump's verdict, which is the one an operator reads
  // before restoring.
  created_at: "2026-09-01T04:30:01Z",
  event_type: "backup_verify_failed",
  payload: { destination: "disk", family: "attachments", error: "truncated" },
}

describe("outcome keying", () => {
  it("keeps the dump and attachment outcomes apart", async () => {
    routes({
      "/events?event_type=backup_shipped&limit=50": {
        items: [SHIPPED_DUMP],
        total: 1,
      },
      "/events?event_type=backup_verify_failed&limit=50": {
        items: [FAILED_TARBALL],
        total: 1,
      },
    })

    const { result } = renderHook(() => useBackupsTabBinding(), { wrapper })

    await waitForHook(() =>
      expect(result.current.recentOutcomes.size).toBe(2),
    )
    expect(
      result.current.recentOutcomes.get(outcomeKey("disk", "dump"))?.event_type,
    ).toBe("backup_shipped")
    expect(
      result.current.recentOutcomes.get(outcomeKey("disk", "attachments"))?.error,
    ).toBe("truncated")
  })
})
```

A hook test rather than a render assertion, because Task 12 deliberately leaves
`backups-tab.tsx` rendering only the dump line — Task 13 adds the second one.
`routes` and `wrapper` are the file's own helpers (`:55-72`, `:23-28`); if
`recentOutcomes` is not on the binding's returned object, assert through
whatever field carries it.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm test -- backups
```

Expected: FAIL — `recentOutcomes.size` is 1, because the attachment row
overwrote the dump row under a destination-only key.

- [ ] **Step 3: Write the implementation**

In `frontend/src/hooks/api/use-backups-api.ts`, add to `BackupDestination`:

```ts
  attachments_retention_keep: number
```

and to `DestinationInventory`:

```ts
  attachments_retention_keep: number
  attachment_snapshots: InventorySnapshot[]
  /** The attachment tarball's own last outcome. Separate because the two
   *  artefacts ship and fail independently. */
  last_attachment_outcome: InventoryOutcome | null
```

In `frontend/src/features/settings/use-backups-tab-binding.ts`, add the family
to the outcome type and key the map on both:

```ts
export interface BackupOutcome {
  destination: string
  family: "dump" | "attachments"
  event_type: "backup_shipped" | "backup_verify_failed"
  at: string
  file: string | null
  sha256: string | null
  error: string | null
}

/** The map key. A destination now has two independent outcomes per run, and
 *  the attachment row is journalled second -- keying on the destination alone
 *  would let it overwrite the dump's. */
export function outcomeKey(destination: string, family: string): string {
  return `${destination}\u0000${family}`
}
```

and inside `recentOutcomes`:

```ts
    const newest = new Map<string, BackupOutcome>()
    for (const row of rows) {
      const payload = row.payload as Record<string, unknown>
      const destination = String(payload.destination ?? "")
      if (!destination) continue
      const family = payload.family === "attachments" ? "attachments" : "dump"
      const key = outcomeKey(destination, family)
      const previous = newest.get(key)
      if (previous && previous.at >= row.created_at) continue
      newest.set(key, {
        destination,
        family,
        event_type: row.event_type as BackupOutcome["event_type"],
        at: row.created_at,
        file: (payload.file as string) ?? null,
        sha256: (payload.sha256 as string) ?? null,
        error:
          (payload.error as string) ??
          (payload.got
            ? `read-back mismatch: expected ${payload.expected}, got ${payload.got}`
            : null),
      })
    }
```

- [ ] **Step 4: Run the test and the typecheck**

```bash
cd frontend && npm run typecheck && npm test -- backups
```

Expected: the typecheck fails first, naming every call site of
`recentOutcomes.get(...)` in `backups-tab.tsx`. Pass the dump key there —
`recentOutcomes.get(outcomeKey(destination.name, "dump")) ?? null` — so the tab
keeps its current behaviour; Task 13 adds the second line.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/api/use-backups-api.ts \
  frontend/src/features/settings/use-backups-tab-binding.ts \
  frontend/src/features/settings/components/backups-tab.tsx \
  frontend/src/features/settings/__tests__/backups.test.tsx
git commit -m "fix(ui): key backup outcomes by artefact family"
```

---
### Task 13: The Backups tab

**Files:**
- Modify: `frontend/src/features/settings/components/backups-tab.tsx` (`InventorySection` at `:208-270`, `DestinationRow` at `:286-321`, `DestinationForm` at `:368-400`)
- Test: `frontend/src/features/settings/__tests__/backups.test.tsx`

**Interfaces:**
- Consumes: Task 12's `outcomeKey`, `attachments_retention_keep`, `attachment_snapshots`, `last_attachment_outcome` — see Contracts.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-opus-low
**Evaluation:** files 1 - spec 1 - coupling 1 - risk 1 = 4

- [ ] **Step 1: Write the failing test**

Three edits to the existing file come first, or pre-existing tests break:

1. **The `LOCAL` and `NAS` fixtures (`:29-50`) gain
   `attachments_retention_keep: 3`**, or the new form input renders the string
   `"undefined"`.
2. **Every inventory fixture in `routes({...})` gains
   `attachments_retention_keep: 3`, `attachment_snapshots: []` and
   `last_attachment_outcome: null`**, or `InventorySection` reads `.length` of
   `undefined` and the render throws.
3. **`findByLabelText(/keep/i)` (`:149`) becomes
   `findByLabelText(/snapshots to keep/i)`**, because the new field's label also
   contains "keep" and the query would match two elements and throw.

Then append, in the file's own `routes()` + `fireEvent` idiom:

```tsx
const INVENTORY_ROW = {
  name: "disk",
  kind: "local" as const,
  enabled: true,
  retention_keep: 14,
  attachments_retention_keep: 3,
  snapshots: [
    {
      name: "darkmem-app-20260101-000000.sql.gz",
      size: 10,
      modified_at: "2026-01-01T00:00:00Z",
    },
  ],
  attachment_snapshots: [],
  last_outcome: null,
  last_attachment_outcome: null,
  error: null,
}

describe("the attachment family on the tab", () => {
  it("lists attachment tarballs beside the dumps", async () => {
    routes({
      "/backups/inventory": {
        destinations: [
          {
            ...INVENTORY_ROW,
            attachment_snapshots: [
              {
                name: "darkmem-app-attachments-20260101-000000.tar.gz",
                size: 20,
                modified_at: "2026-01-01T00:00:00Z",
              },
            ],
          },
        ],
      },
    })
    render(<BackupsTab />, { wrapper })

    expect(
      await screen.findByText("darkmem-app-attachments-20260101-000000.tar.gz"),
    ).toBeInTheDocument()
  })

  it("says when a destination holds dumps but no tarball", async () => {
    routes({ "/backups/inventory": { destinations: [INVENTORY_ROW] } })
    render(<BackupsTab />, { wrapper })

    expect(
      await screen.findByText(/no attachment tarballs yet/i),
    ).toBeInTheDocument()
  })

  it("edits the attachment retention", async () => {
    const fetchMock = routes()
    render(<BackupsTab />, { wrapper })

    fireEvent.click(await screen.findByRole("button", { name: /edit disk/i }))
    fireEvent.change(
      await screen.findByLabelText(/attachment tarballs to keep/i),
      { target: { value: "5" } },
    )
    fireEvent.click(screen.getByRole("button", { name: /^save$/i }))

    await waitFor(() => {
      const put = fetchMock.mock.calls.find(
        ([, init]) => (init as RequestInit | undefined)?.method === "PUT",
      )
      expect(put).toBeDefined()
      const body = JSON.parse((put![1] as RequestInit).body as string)
      const disk = body.destinations.find(
        (d: { name: string }) => d.name === "disk",
      )
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

- [ ] **Step 3: Write the implementation**

In `InventorySection`, below the existing dump list and above the restore
command, add the tarball list and a second outcome badge. Replace the
`row.last_outcome ? (...) : null` badge block with a pair:

```tsx
            <OutcomeBadge outcome={row.last_outcome} label="database" />
            <OutcomeBadge outcome={row.last_attachment_outcome} label="attachments" />
```

and add the component beside `InventorySection`:

```tsx
/** One family's verdict. Two badges rather than one, because the dump and the
 *  attachment tarball ship and fail independently and an operator choosing a
 *  snapshot needs both answers. */
function OutcomeBadge({
  outcome,
  label,
}: {
  outcome: InventoryOutcome | null
  label: string
}) {
  if (!outcome) return null
  const verified = outcome.event_type === "backup_shipped"
  return (
    <Badge variant="outline" size="sm" className={verified ? "" : "border-dashed"}>
      {label}: {verified ? "verified" : "not restorable"}
    </Badge>
  )
}
```

Below the existing snapshot `<ul>`, add:

```tsx
          {row.error ? null : row.attachment_snapshots.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              no attachment tarballs yet
            </p>
          ) : (
            <ul className="text-muted-foreground space-y-0.5 text-sm">
              {[...row.attachment_snapshots]
                .sort((a, b) => b.name.localeCompare(a.name))
                .map((snapshot) => (
                  <li key={snapshot.name} className="flex flex-wrap gap-2">
                    <span className="font-mono">{snapshot.name}</span>
                    <span>{formatBytes(snapshot.size)}</span>
                    <span>{new Date(snapshot.modified_at).toLocaleString()}</span>
                  </li>
                ))}
            </ul>
          )}
```

Import `InventoryOutcome` alongside the existing type imports.

In `DestinationRow`, render the second outcome line beside the first:

```tsx
      <OutcomeLine outcome={outcome} />
      <OutcomeLine outcome={attachmentOutcome} />
```

adding `attachmentOutcome: BackupOutcome | null` to its props and passing
`recentOutcomes.get(outcomeKey(destination.name, "attachments")) ?? null` at the
call site.

In `DestinationForm`, below the existing "Snapshots to keep" field:

```tsx
      <div className="flex flex-col gap-1">
        <Label
          htmlFor="backup-attachment-keep"
          className="text-muted-foreground text-sm"
        >
          Attachment tarballs to keep
        </Label>
        <Input
          id="backup-attachment-keep"
          inputMode="numeric"
          value={String(draft.attachments_retention_keep)}
          onChange={(e) =>
            setDraft({
              ...draft,
              attachments_retention_keep: Number(e.target.value) || 0,
            })
          }
        />
      </div>
```

- [ ] **Step 4: Run the suite, the typecheck and the build**

```bash
cd frontend && npm run typecheck && npm test -- backups && npm run build
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/settings/components/backups-tab.tsx \
  frontend/src/features/settings/__tests__/backups.test.tsx
git commit -m "feat(ui): show attachment tarballs on the backups tab"
```

---

### Task 14: The row-less sweep guards

**Files:**
- Modify: `backend/app/services/page_attachment_cleanup.py` (`CleanupReport` at `:90-102`, the config schema at `:41-54`, `run_cleanup` at `:219-263`, the runner at `:266-283`)
- Test: `backend/tests/test_page_attachment_cleanup.py`

**Interfaces:**
- Consumes: Task 1's `attachment_count` — see Contracts.
- Produces: `rowless_bulk_limit` and `CleanupReport.rowless_skipped` — see Contracts.

**Implementer:** dr-superpowers:impl-opus-medium
**Evaluation:** files 1 - spec 0 - coupling 1 - risk 3 = 5

Risk 3: this arm deletes files that have no other copy. It is also the arm that
wipes a restored attachment volume within eighty minutes when the database it
boots against is empty, which is the whole reason for the change.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_page_attachment_cleanup.py`:

```python
# ── The row-less arm refuses a bulk mismatch ─────────────────────────


def _stage_rowless(count: int) -> None:
    """Files old enough for the arm, with no row anywhere. Written through
    `attachment_path` so the shard layout matches what `_scan` walks."""
    for _ in range(count):
        path = attachment_path(uuid4())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"orphan")
        _age(path, 7200)


async def test_an_empty_table_with_files_present_removes_nothing(
    session_factory, root
):
    """The parked scenario: an app booted against a freshly recreated database
    while ATTACHMENTS_DIR points at the real volume. A count threshold alone
    would still wipe a corpus smaller than the limit."""
    now = time.time()
    _stage_rowless(3)

    report = await run_cleanup(
        session_factory, grace_hours=168, staging_max_age_hours=6, now=now
    )

    assert report.rowless_files_removed == 0
    assert report.rowless_skipped == 3
    assert len(list(root.rglob("*"))) >= 3


async def test_a_count_past_the_limit_removes_nothing(
    session, session_factory, root
):
    now = time.time()
    await _attachment(session, age_hours=1)  # the table is not empty
    await session.commit()
    _stage_rowless(4)

    report = await run_cleanup(
        session_factory, grace_hours=168, staging_max_age_hours=6,
        rowless_bulk_limit=3, now=now,
    )

    assert report.rowless_files_removed == 0
    assert report.rowless_skipped == 4


async def test_at_the_limit_the_arm_still_collects(
    session, session_factory, root
):
    now = time.time()
    await _attachment(session, age_hours=1)
    await session.commit()
    _stage_rowless(3)

    report = await run_cleanup(
        session_factory, grace_hours=168, staging_max_age_hours=6,
        rowless_bulk_limit=3, now=now,
    )

    assert report.rowless_files_removed == 3
    assert report.rowless_skipped == 0


async def test_the_other_arms_run_even_when_the_rowless_arm_refuses(
    session_factory, root
):
    now = time.time()
    _stage_rowless(2)
    stale_part = root / "ab"
    stale_part.mkdir(parents=True, exist_ok=True)
    part = stale_part / "deadbeef.part"
    part.write_bytes(b"x")
    os.utime(part, (now - 7200, now - 7200))
    staging = root / STAGING_DIRNAME / "job"
    staging.mkdir(parents=True)
    os.utime(staging, (now - 10 * 3600, now - 10 * 3600))

    report = await run_cleanup(
        session_factory, grace_hours=168, staging_max_age_hours=6, now=now
    )

    assert report.rowless_skipped == 2
    assert report.part_files_removed == 1
    assert report.staging_dirs_removed == 1
```

The `root` fixture (`tests/test_page_attachment_cleanup.py:24-27`), `_age`
(`:30-32`) and `_attachment` (`:44-55`) already exist in that file: `root`
points `settings.attachments_dir` at `tmp_path`, and `_attachment` writes both
a row and its file, which is what makes the table non-empty in the two tests
that need it. Add `STAGING_DIRNAME` to the
`from app.services.page_attachments import ...` line.

**Two pre-existing tests run against an empty `page_attachments` while expecting
the row-less arm to act**, so the new empty-table guard turns them red. Both
need one row seeded first — `await _attachment(session, age_hours=1)` then
`await session.commit()`, which makes the table non-empty without giving either
test a second row-less file:

- `test_old_rowless_files_and_parts_go_young_ones_stay` (`:125-140`), which
  asserts `rowless_files_removed == 1`. It takes `session_factory, root`; add
  the `session` fixture to its arguments.
- `test_a_file_that_cannot_be_removed_does_not_stop_the_sweep` (`:160-191`),
  which asserts `files_failed == 1` from the refused unlink. The same edit.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_page_attachment_cleanup.py
```

Expected: FAIL — `run_cleanup() got an unexpected keyword argument 'rowless_bulk_limit'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/services/page_attachment_cleanup.py`, add the import and the
default:

```python
from app.services.attachment_manifest import attachment_count
```

```python
ROWLESS_BULK_LIMIT_DEFAULT = 100
```

Add the config field:

```python
    FieldDescriptor(
        key="rowless_bulk_limit", label="Row-less file limit",
        default=ROWLESS_BULK_LIMIT_DEFAULT, min=1, max=100000,
        help="Above this many files with no row, the sweep refuses rather "
             "than collecting -- the signature of a restored volume against "
             "an unrestored database, not of a crash.",
    ),
```

Add the counter to `CleanupReport` and to `total()`:

```python
    rowless_skipped: int = 0
```

Change `run_cleanup`'s signature and the row-less arm:

```python
async def run_cleanup(
    session_factory,
    *,
    grace_hours: int,
    staging_max_age_hours: int,
    rowless_bulk_limit: int = ROWLESS_BULK_LIMIT_DEFAULT,
    now: float | None = None,
) -> CleanupReport:
```

```python
    root = attachments_root()
    files, parts = await asyncio.to_thread(_scan, root, now)
    if files:
        known: set[UUID] = set()
        async with session_factory() as session:
            total_rows = await attachment_count(session)
            for start in range(0, len(files), _ID_BATCH):
                batch = [attachment_id for attachment_id, _ in files[start:start + _ID_BATCH]]
                known.update(
                    row[0] for row in (await session.execute(_KNOWN_IDS, {"ids": batch})).all()
                )
        rowless = [path for attachment_id, path in files if attachment_id not in known]
        # Two guards, because neither closes the hazard alone. The empty-table
        # one is the parked scenario's own signature -- an app booted against a
        # freshly recreated database with the real volume mounted -- and a
        # count threshold would still wipe a corpus smaller than the limit. The
        # count one catches a wrong ATTACHMENTS_DIR on a populated instance.
        # A large row-less set is not proof of a mistake: an import that fails
        # between moving its staged files and committing leaves hundreds at
        # once, which is why this routes to attachment_verify rather than
        # telling the operator to raise the number.
        if rowless and (total_rows == 0 or len(rowless) > rowless_bulk_limit):
            report.rowless_skipped = len(rowless)
            logger.error(
                "page_attachment_cleanup: refusing to remove %s row-less files "
                "(%s). Check whether this instance is serving a restored "
                "attachment volume against an unrestored database, whether "
                "ATTACHMENTS_DIR is right, or whether an import failed before "
                "committing; `python -m app.services.attachment_verify` tells "
                "them apart.",
                len(rowless),
                "page_attachments is empty"
                if total_rows == 0
                else f"limit {rowless_bulk_limit}",
            )
        else:
            _log_removed("removing row-less files", rowless)
            report.rowless_files_removed, failed = await asyncio.to_thread(_unlink, rowless)
            report.files_failed += failed
```

In `make_page_attachment_cleanup_runner`, read and forward the new field:

```python
        limit = ROWLESS_BULK_LIMIT_DEFAULT
```

```python
            limit = int(cfg.config.get("rowless_bulk_limit", ROWLESS_BULK_LIMIT_DEFAULT))
```

```python
        report = await run_cleanup(
            session_factory,
            grace_hours=grace,
            staging_max_age_hours=staging,
            rowless_bulk_limit=limit,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_page_attachment_cleanup.py \
  tests/test_code_deriver.py
```

Expected: all passed. The second path is the job-roster guard, which derives
the roster from `app/main.py`'s AST; this task's new `FieldDescriptor` must not
disturb it.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/page_attachment_cleanup.py \
  backend/tests/test_page_attachment_cleanup.py
git commit -m "fix(attachments): refuse a bulk row-less sweep"
```

---

### Task 15: Post-restore verification

**Files:**
- Create: `backend/app/services/attachment_verify.py`
- Test: `backend/tests/test_attachment_verify.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `VerifyReport`, `verify`, and the `python -m app.services.attachment_verify` exit codes — see Contracts.

**Implementer:** dr-superpowers:impl-sonnet-low
**Evaluation:** files 1 - spec 0 - coupling 0 - risk 0 = 1

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_attachment_verify.py`:

```python
"""Does every row have its file, and every file its row (spec §10)."""
from __future__ import annotations

import os
from uuid import uuid4

from sqlalchemy import text as sa_text

from app.services.attachment_verify import verify


async def _row(session, attachment_id) -> None:
    await session.execute(
        sa_text(
            "INSERT INTO page_attachments "
            "(id, project, filename, content_type, size_bytes, sha256) "
            "VALUES (CAST(:id AS uuid), 'default', 'f.png', 'image/png', 1, 'ab')"
        ),
        {"id": str(attachment_id)},
    )


def _file(root, attachment_id) -> None:
    shard = root / str(attachment_id)[:2]
    shard.mkdir(parents=True, exist_ok=True)
    (shard / str(attachment_id)).write_bytes(b"payload")


async def test_a_matched_pair_verifies(session, root):
    attachment_id = uuid4()
    await _row(session, attachment_id)
    _file(root, attachment_id)

    report = await verify(session)

    assert report.ok()
    assert report.missing_files == []
    assert report.rowless_files == []


async def test_a_row_without_a_file_is_reported(session, root):
    attachment_id = uuid4()
    await _row(session, attachment_id)

    report = await verify(session)

    assert not report.ok()
    assert report.missing_files == [str(attachment_id)]


async def test_a_file_without_a_row_is_reported(session, root):
    attachment_id = uuid4()
    _file(root, attachment_id)

    report = await verify(session)

    assert not report.ok()
    assert report.rowless_files == [str(attachment_id)]


async def test_an_in_flight_part_is_not_a_rowless_file(session, root):
    shard = root / "ab"
    shard.mkdir(parents=True)
    (shard / "deadbeef.part").write_bytes(b"x")

    report = await verify(session)

    assert report.ok()
```

That file needs its own root fixture — a test module cannot reach another's.
Add it at the top:

```python
import pytest

from app.config import settings


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path))
    return tmp_path
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_attachment_verify.py
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.attachment_verify'`.

- [ ] **Step 3: Write the implementation**

Create `backend/app/services/attachment_verify.py`:

```python
"""Does every row have its file, and every file its row (spec §10).

Run after any restore. A dump newer than its paired tarball, a tarball that
paired with nothing, and a worker cycle killed between the database rename and
the symlink swap all leave rows whose files are absent, and nothing else
reports that.

Read-only on purpose: it opens no write transaction and unlinks nothing. The
repair for a missing file is another restore, never a delete, and the repair
for a row-less file is the cleanup job -- which has its own refusal for exactly
the bulk case this reports.

    docker compose exec darkmem python -m app.services.attachment_verify
"""
from __future__ import annotations

import asyncio
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app.services.page_attachments import attachment_path, attachments_root

_ROWS = text("SELECT id FROM page_attachments ORDER BY created_at, id")
_SHARD = re.compile(r"[0-9a-f]{2}")
#: Enough to act on. A restore that went wrong is wrong in bulk, and printing
#: ten thousand ids helps nobody read the count above them.
_SAMPLE = 20


@dataclass(frozen=True)
class VerifyReport:
    missing_files: list[str]
    rowless_files: list[str]

    def ok(self) -> bool:
        return not self.missing_files and not self.rowless_files


def _missing(ids: list[str]) -> list[str]:
    return [i for i in ids if not attachment_path(UUID(i)).is_file()]


def _on_disk(root: Path) -> set[str]:
    """Every file named like an attachment id. A `.part` is an in-flight
    upload and a dot-directory is staging; neither is a row's file."""
    found: set[str] = set()
    if not root.is_dir():
        return found
    for shard in root.iterdir():
        if not (shard.is_dir() and _SHARD.fullmatch(shard.name)):
            continue
        for entry in shard.iterdir():
            if not entry.is_file() or entry.name.endswith(".part"):
                continue
            try:
                attachment_id = UUID(entry.name)
            except ValueError:
                continue
            if str(attachment_id) == entry.name:
                found.add(entry.name)
    return found


async def verify(session) -> VerifyReport:
    ids = [str(row[0]) for row in (await session.execute(_ROWS)).all()]
    missing = await asyncio.to_thread(_missing, ids)
    on_disk = await asyncio.to_thread(_on_disk, attachments_root())
    return VerifyReport(
        missing_files=missing,
        rowless_files=sorted(on_disk - set(ids)),
    )


def _print(title: str, items: list[str]) -> None:
    print(f"{title}: {len(items)}")
    for item in items[:_SAMPLE]:
        print(f"  {item}")
    if len(items) > _SAMPLE:
        print(f"  ... and {len(items) - _SAMPLE} more")


async def _main() -> int:
    from app.database import async_session_factory

    async with async_session_factory() as session:
        report = await verify(session)
    _print("rows whose file is missing", report.missing_files)
    _print("files with no row", report.rowless_files)
    return 0 if report.ok() else 1


if __name__ == "__main__":  # pragma: no cover - shell entry point
    sys.exit(asyncio.run(_main()))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_attachment_verify.py
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/attachment_verify.py backend/tests/test_attachment_verify.py
git commit -m "feat(attachments): report rows and files that disagree"
```

---

### Task 16: Documentation

**Files:**
- Modify: `docs/runbook-deployment.md`
- Modify: `docs/runbook-backup-worker.md`
- Modify: `CLAUDE.md` (the Backups bullet under Commands)

**Interfaces:**
- Consumes: every earlier task's artefact names, environment variables and commands — see Contracts.
- Produces: nothing.

**Implementer:** dr-superpowers:impl-sonnet-medium
**Evaluation:** files 1 - spec 1 - coupling 0 - risk 0 = 2

- [ ] **Step 1: Add the restore procedure to `docs/runbook-deployment.md`**

In the restore section, after the dump restore steps:

```markdown
### Attachments

A dump carries no attachment bytes. Restore the paired tarball too:

1. Find the newest `darkmem-attachments-<stamp>.tar.gz` whose `<stamp>` is at
   or before the dump's. That is the set that was live when the dump was
   taken — correct precisely because an unchanged set writes no tarball.
   Off-host, `python -m app.services.backup_pull --destination <name>
   --paired-with <dump name> --out /dumps` applies the same rule.
2. Unpack it over the attachment volume. That volume is a named Docker volume,
   so the unpack goes through the image rather than a host path — the same
   shape `backup.sh` uses to write it:

   ```bash
   docker run --rm --entrypoint tar \
     -v darkmem-prod_attachment_data:/dst \
     -v /root/darkmem-backups:/src:ro \
     darkraise/darkmem:latest -xzf /src/darkmem-attachments-<stamp>.tar.gz -C /dst
   ```

3. Then `docker compose exec darkmem python -m app.services.attachment_verify`.
   It exits non-zero when any row's file is missing.

Three limits, none of them repairable after the fact:

- The host floor keeps 14 dumps and 3 tarballs, so an old dump may pair with
  no surviving tarball. Restoring it serves rows whose files are gone.
- A cleanup that deletes a row between the dump and the tar leaves that dump
  one row without a file.
- A night whose tarball failed on every destination does not advance the
  ship job's state, so the next night rebuilds under a newer stamp and the
  failed night's dump pairs with an older set than it should.

`page_attachment_cleanup` refuses to collect row-less files when
`page_attachments` is empty or when there are more than `rowless_bulk_limit`
(100) of them, so an app booted against a recreated database will not wipe a
restored volume. It logs an error rather than a warning when it refuses.
```

- [ ] **Step 2: Add the worker layout to `docs/runbook-backup-worker.md`**

```markdown
## Attachments

Create the store before first boot, owned by the image's uid, beside the dump
directory:

```bash
APP_UID=$(docker run --rm darkraise/darkmem:latest id -u)
sudo install -d -o "$APP_UID" -g "$APP_UID" -m 0750 /srv/darkmem-attachments
```

`restore-cycle.sh` unpacks each restored set into `gen-<stamp>/` and points the
relative `current` symlink at it in the same step as the database rename. The
app mounts the store read-only and reads `ATTACHMENTS_DIR=.../current`; the
host-side loop is the only writer, which is why this is a bind mount and not a
named volume.

- Before the first restore there is no `current`. The boot check warns and the
  viewer starts.
- A dump with no tarball at or before its stamp restores the database and keeps
  the current generation, with a warning.
- When only the attachment half is behind — the ship order is dump then
  tarball, so this happens whenever a cycle fires between the two uploads — the
  script takes the attachments-only path: unpack, swap, prune, no side database
  and no downtime.
- `RECEIVER_MAX_BYTES` (10 GB) now bounds the attachment tarball as well as the
  dump. Raise it before the set approaches it.
```

- [ ] **Step 3: Update the Backups bullet in `CLAUDE.md`**

Extend the existing `**Backups (homelab, T1.54)**` bullet with:

```markdown
  **Attachments are a second artefact family on both producers.** A manifest
  hash over `(id, sha256)`, computed by Postgres so the shell and the app
  cannot drift, decides whether the set changed; when it did, each producer
  writes one whole-set tarball beside its dump under the same stamp —
  `darkmem-attachments-<stamp>.tar.gz` with a `.manifest` sidecar for
  `backup.sh` (`BACKUP_ATTACHMENTS_KEEP`, default 3), and
  `darkmem-app-attachments-<stamp>.tar.gz[.age]` for `backup_ship` (per
  destination `attachments_retention_keep`, default 3). **`_is_snapshot` is
  never widened** — the families are separated by `Family.matches` and every
  prune takes one, because tarballs sort after dumps by name and a shared
  predicate would let a retention pass delete the dumps. A restore pairs a
  dump with the newest tarball whose stamp is ≤ its own, which is correct
  because an unchanged set writes no tarball. On the backup worker the
  tarball unpacks into `gen-<stamp>/` under a read-only bind mount and a
  relative `current` symlink swaps beside the database rename;
  `restore-cycle.sh`'s no-op predicate covers **both** halves, so a tarball
  that arrives after its dump is not stranded.
  `python -m app.services.attachment_verify` reports rows without files after
  any restore.
```

- [ ] **Step 4: Verify the docs match the code**

```bash
cd backend && TEST_DATABASE_URL=postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test_2 \
  .venv/bin/python -m pytest -q tests/test_deployment_artifact.py tests/test_backup_script.py
```

Expected: all passed. Then re-read each command quoted above against the file
it names — every environment variable (`ATTACHMENT_VOLUME`, `DOCKER_CMD`,
`BACKUP_ATTACHMENTS_KEEP`, `ATTACHMENT_STORE`, `DARKMEM_ATTACHMENT_DIR`,
`ATTACHMENTS_DIR`) must appear with the same default the code gives it.

- [ ] **Step 5: Commit**

```bash
git add docs/runbook-deployment.md docs/runbook-backup-worker.md CLAUDE.md
git commit -m "docs(backup): record the attachment family"
```
