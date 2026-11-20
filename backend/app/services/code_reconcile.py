"""T1.40 — working-tree drift detection for already-indexed repos (doc 10 §3).

A repo's on-disk working tree can diverge from the graph it was indexed from
without any git commit ever happening: a `local_path` repo with no fetchable
`origin` remote is edited directly (``RepoManager.pull_repo`` leaves such a
tree untouched rather than resetting it), or something outside the sync loop
writes straight into a clone directory. `CodePipeline.run`'s own short-circuit
only compares `last_indexed_commit` to `HEAD`, so a change that never moves
`HEAD` is invisible to it and would otherwise sit stale forever.

This module hashes the tree independently of `HEAD` and reports the files
whose content disagrees with what `CodeFile.content_hash` says was indexed.
The caller (`job_runners.make_repo_sync_runner`, since the per-repo indexing
modes epic folded this scan into the one recurring loop rather than a
standalone job) feeds the result into `CodePipeline.run(..., forced_files=...)`,
which runs it through the exact same incremental path (dependent-caller
retrace, index-debt folding) a real git diff would. It only runs for a repo
whose operator opted into `index_uncommitted`, not unconditionally for every
indexed repo the way the retired standalone job did.

Hashing walks the same file set `CodePipeline` would (`_list_all_files`) and
reuses its per-file hash (sha256 of the UTF-8-decoded content, replacing
undecodable bytes) so a match here is guaranteed to also match phase 03's own
comparison — there is only one definition of "changed" between the two. The
walk runs in a worker thread, and a file whose `(mtime, size)` matches the
previous scan reuses that scan's hash instead of being read again.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code import CodeFile, Repository
from app.services.code_pipeline import MAX_FILE_SIZE, _list_all_files, read_source_text

logger = logging.getLogger(__name__)

# The previous scan's `(mtime_ns, size, hash)` per file, per repository.
# In-process, which the single worker makes sufficient; a restart costs one
# full hash of each tree.
_STAT_CACHE: dict[UUID, dict[str, tuple[int, int, str | None]]] = {}

# A file written within this many seconds of the scan may still change
# without moving its mtime, so its stamp is not trusted on the next scan.
_RACY_WINDOW_NS = 2_000_000_000


def _file_hash(path: Path) -> str | None:
    """The same hash `CodePipeline._parse_one` would compute for this path, or
    None if the pipeline would skip it too (too large, unreadable, gone).

    Returning None here — rather than a sentinel that would read as "changed"
    — matters: a file the pipeline skips never gets a `CodeFile.content_hash`
    written for it, so treating an unhashable file as a mismatch would flag it
    as drift on every single reconcile tick forever, with no run ever able to
    resolve it.
    """
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_SIZE:
            return None
    except OSError:
        return None
    content = read_source_text(path)
    if content is None:
        return None
    return hashlib.sha256(content.encode()).hexdigest()


def _scan_tree(
    work_dir: Path, previous: dict[str, tuple[int, int, str | None]],
) -> tuple[list[str], dict[str, str], dict[str, tuple[int, int, str | None]]]:
    """List the tree and hash each file whose stat moved since ``previous``.

    Returns the live file list, the hash of every hashable file, and the
    stamps to keep for the next scan.
    """
    live_files = _list_all_files(work_dir)
    trusted_before = time.time_ns() - _RACY_WINDOW_NS
    hashes: dict[str, str] = {}
    stamps: dict[str, tuple[int, int, str | None]] = {}
    for fp in live_files:
        path = work_dir / fp
        try:
            stat = path.stat()
        except OSError:
            continue
        prior = previous.get(fp)
        if prior is not None and prior[0] == stat.st_mtime_ns and prior[1] == stat.st_size:
            digest = prior[2]
        else:
            digest = _file_hash(path)
        if stat.st_mtime_ns < trusted_before:
            stamps[fp] = (stat.st_mtime_ns, stat.st_size, digest)
        if digest is not None:
            hashes[fp] = digest
    return live_files, hashes, stamps


async def compute_working_tree_drift(
    session: AsyncSession, repo: Repository, work_dir: Path,
) -> tuple[list[str], list[str]]:
    """Compare the live working tree against this repo's indexed `CodeFile` rows.

    Returns `(changed, deleted)`:
    - `changed` is every on-disk path whose live hash disagrees with the
      indexed `content_hash` — including a path with no `CodeFile` row at all,
      which is content the graph has never seen (added without a commit).
    - `deleted` is every indexed path no longer present on disk.

    An empty result for both means the tree is exactly what the graph was
    built from; the caller must treat that as no work at all, not merely
    "nothing changed but still call the pipeline" — that box is what keeps a
    healthy repo's reconcile tick free.
    """
    rows = (await session.execute(
        select(CodeFile.file_path, CodeFile.content_hash)
        .where(CodeFile.repo_id == repo.id)
    )).all()
    indexed = dict(rows)

    previous = _STAT_CACHE.get(repo.id, {})
    live_files, hashes, stamps = await asyncio.get_running_loop().run_in_executor(
        None, _scan_tree, work_dir, previous,
    )
    _STAT_CACHE[repo.id] = stamps
    changed = [
        fp for fp in live_files
        if fp in hashes and indexed.get(fp) != hashes[fp]
    ]

    live_set = set(live_files)
    deleted = [fp for fp in indexed if fp not in live_set]
    return changed, deleted
