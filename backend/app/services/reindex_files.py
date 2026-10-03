"""What a caller's file list means (spec §3.1, §6.2).

Two pure decisions, kept together because they are two halves of one question
and neither touches the database or git:

- ``canonicalise_paths`` runs at the door. It pins every entry to the one
  spelling ``_list_all_files`` produces, because ``code_files`` has no
  uniqueness on ``(repo_id, file_path)`` and phase 03 looks its row up by exact
  string match -- a second spelling inserts a duplicate row and duplicate
  symbols for one on-disk file, and search returns both forever.
- ``classify_union_files`` runs inside the claimed pipeline run, after the
  pull, and sorts the canonical names into the four buckets the caller is
  answered with.

Import ``classify_union_files`` lazily from ``code_pipeline``: this module
imports ``code_pipeline`` -- directly, and again through ``code_reconcile`` --
so a module-level import back would close the cycle.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from app.services.code_pipeline import is_discoverable_path
from app.services.code_reconcile import _file_hash

# Bounds the caller's list, not the repository walk canonicalisation performs.
MAX_UNION_FILES = 1000


@dataclass(frozen=True)
class UnionBuckets:
    """Every named file lands in exactly one bucket, and all four are reported.

    ``skipped_unindexable`` exists so a caller that names a file the system can
    never index hears about it; silence is the outcome this reporting is for.
    """

    accepted: list[str] = field(default_factory=list)
    skipped_unchanged: list[str] = field(default_factory=list)
    skipped_missing: list[str] = field(default_factory=list)
    skipped_unindexable: list[str] = field(default_factory=list)


def canonicalise_paths(
    work_dir: Path, names: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Return ``(canonical, invalid)``.

    ``canonical`` is deduplicated and order-preserving, each entry spelled the
    way ``_list_all_files`` spells it. ``invalid`` carries the caller's own
    spellings for entries that resolve outside the working directory -- caller
    error, which hard-refuses the request rather than being skipped.

    A path inside the tree that is not on disk stays in ``canonical``: a clone's
    tree is stale, so the most ordinary push names a file it does not have yet,
    and refusing there would reject exactly the push this door exists to
    announce. The classifier soft-skips it.
    """
    root = work_dir.resolve()
    canonical: list[str] = []
    invalid: list[str] = []
    seen: set[str] = set()

    for raw in names:
        try:
            resolved = (root / raw).resolve()
            relative = resolved.relative_to(root)
        except (ValueError, OSError):
            invalid.append(raw)
            continue
        if not relative.parts:
            invalid.append(raw)
            continue
        spelled = relative.as_posix()
        if spelled not in seen:
            seen.add(spelled)
            canonical.append(spelled)

    return canonical, invalid


def classify_union_files(
    work_dir: Path,
    names: Iterable[str],
    indexed_hashes: Mapping[str, str | None],
) -> UnionBuckets:
    """Sort canonical names into the four buckets.

    Branch order is load-bearing. ``_file_hash`` returns ``None`` for a missing
    file *and* for an unindexable one -- ``not path.is_file()`` is the first
    thing it tests -- so the presence test must come first or every absent file
    is swallowed by the unindexable branch and the never-delete reporting never
    fires.

    Discoverability is tested ahead of both, because it is a property of the
    path rather than of the disk: a path ``_list_all_files`` never surfaces is
    one the system can never index, present or not.
    """
    buckets = UnionBuckets()

    for name in names:
        path = work_dir / name
        if not is_discoverable_path(name):
            buckets.skipped_unindexable.append(name)
            continue
        try:
            path = path.resolve()
            path.relative_to(work_dir.resolve())
        except (ValueError, OSError, RuntimeError):
            buckets.skipped_unindexable.append(name)
            continue
        if not path.is_file():
            buckets.skipped_missing.append(name)
            continue
        live = _file_hash(path)
        if live is None:
            buckets.skipped_unindexable.append(name)
            continue
        if live == indexed_hashes.get(name):
            buckets.skipped_unchanged.append(name)
            continue
        buckets.accepted.append(name)

    return buckets
