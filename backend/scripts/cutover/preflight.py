"""The pre-flight: thirteen read-only assertions that name their offending rows.

Postgres names one row and aborts everything, which is a bad debugging
experience over a production dump. Every check here runs before any write, and
none of them repairs anything.
"""
from __future__ import annotations

import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import asyncpg

from . import spec
from .db import CutoverError

BACKEND_DIR = Path(__file__).resolve().parents[2]

MAX_REPORTED_ROWS = 50
MAX_LINEAGE_DEPTH = 128


@dataclass
class Check:
    name: str
    passed: bool
    detail: dict = field(default_factory=dict)


@dataclass
class PreflightReport:
    checks: list[Check] = field(default_factory=list)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed]

    @property
    def passed(self) -> bool:
        return not self.failures

    def add(self, name: str, passed: bool, **detail) -> Check:
        check = Check(name=name, passed=passed, detail=detail)
        self.checks.append(check)
        return check

    def to_dict(self) -> dict:
        return {"passed": self.passed, "checks": [asdict(c) for c in self.checks]}

    def raise_if_failed(self) -> None:
        if self.passed:
            return
        lines = [f"  - {c.name}: {c.detail}" for c in self.failures]
        raise CutoverError("pre-flight failed:\n" + "\n".join(lines))


def memory_types() -> frozenset[str]:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    from app.taxonomy import MEMORY_TYPES

    return frozenset(MEMORY_TYPES)


def baseline_revision() -> str:
    """The sole revision id in migrations/versions, asserted to be sole.

    The freeze has not happened, so the target's chain is exactly one revision.
    Reading it here rather than hardcoding it means a regenerated baseline
    cannot silently disagree with the transform.
    """
    versions = BACKEND_DIR / "migrations" / "versions"
    found: list[tuple[str, str | None]] = []
    for path in sorted(versions.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        revision = re.search(r"^revision:\s*str\s*=\s*['\"]([^'\"]+)['\"]", text, re.M)
        down = re.search(r"^down_revision[^=]*=\s*(.+?)\s*$", text, re.M)
        if revision is None:
            continue
        found.append((revision.group(1), down.group(1) if down else None))
    if len(found) != 1:
        raise CutoverError(
            f"expected exactly one alembic revision under {versions}, found "
            f"{len(found)}: {[r for r, _ in found]}"
        )
    revision, down_revision = found[0]
    if down_revision is not None and "None" not in down_revision:
        raise CutoverError(
            f"the sole revision {revision!r} has down_revision {down_revision!r}"
        )
    return revision


async def _relations(conn: asyncpg.Connection) -> set[str]:
    rows = await conn.fetch(
        "SELECT c.relname FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')"
    )
    return {r["relname"] for r in rows}


async def _count(conn: asyncpg.Connection, table: str) -> int:
    return await conn.fetchval(f'SELECT count(*) FROM "{table}"')


async def check_source_revision(source: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertion 1 — the ``classified_type`` name-reuse trap.

    A ``classified_type`` column with regex-classifier semantics existed on the
    source until revision 0006 dropped it. Against 0005 or earlier both columns
    exist and a transform that selected by position would pick the wrong one
    with no error.
    """
    rows = await source.fetch("SELECT version_num FROM alembic_version")
    versions = sorted(r["version_num"] for r in rows)
    report.add(
        "source_revision_is_0006",
        versions == [spec.SOURCE_REVISION],
        expected=spec.SOURCE_REVISION,
        found=versions,
    )


async def check_source_table_set(source: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertion 2 — subset-plus-pattern, never set equality.

    A.1 was extracted from a freshly migrated database with zero registered
    fingerprints, so set equality would false-abort on every genuine source.
    """
    present = await _relations(source)
    missing = sorted(set(spec.SOURCE_TABLES_A1) - present)
    extra = sorted(present - set(spec.SOURCE_TABLES_A1))
    foreign = sorted(
        name
        for name in extra
        if not any(name.startswith(p) for p in spec.SOURCE_CHILD_TABLE_PREFIXES)
    )
    report.add(
        "source_table_set",
        not missing and not foreign,
        missing=missing,
        foreign=foreign,
        child_tables=[n for n in extra if n not in foreign],
    )


async def check_target_carried_empty(target: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertion 3 — re-runnable from empty, not idempotent against any state."""
    non_empty = {}
    for table in spec.CARRIED:
        count = await _count(target, table.name)
        if count:
            non_empty[table.name] = count
    report.add("target_carried_tables_empty", not non_empty, non_empty=non_empty)


async def check_reset_derivations_absent(
    target: asyncpg.Connection, report: PreflightReport
) -> None:
    """The cheap half of the --reset guard, run before the run pays for staging.

    Seven refusal triggers. Six base tables carry an ON DELETE CASCADE FK into
    memories(id), so deleting a memory silently deletes their rows too; the
    seventh is the per-fingerprint memory-vector partition family, whose cascade
    comes from the table template rather than the baseline. entities and
    entity_relations reference memories through an array rather than an FK, so
    they are not cascaded — they are left dangling instead, which is a different
    failure shape and just as real.
    """
    present = await _relations(target)
    populated: dict[str, int] = {}
    for table in spec.RESET_REFUSAL_TABLES:
        if table not in present:
            continue
        count = await _count(target, table)
        if count:
            populated[table] = count
    partitions = sorted(
        name for name in present if name.startswith(spec.RESET_REFUSAL_TABLE_PREFIX)
    )
    for name in partitions:
        count = await _count(target, name)
        if count:
            populated[name] = count
    report_only: dict[str, int] = {}
    for table in spec.RESET_REPORT_ONLY_TABLES:
        if table in present:
            report_only[table] = await _count(target, table)
    report.add(
        "reset_derivations_absent",
        not populated,
        populated=populated,
        report_only=report_only,
    )


async def check_target_revision(target: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertion 4 — the target is the baseline, and the chain is still one."""
    expected = baseline_revision()
    rows = await target.fetch("SELECT version_num FROM alembic_version")
    versions = sorted(r["version_num"] for r in rows)
    report.add(
        "target_revision_is_baseline",
        versions == [expected],
        expected=expected,
        found=versions,
    )


async def check_lineage(source: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertions 5-7 — the three lineage shapes that cannot load."""
    pointerless = await source.fetch(
        "SELECT id FROM memories WHERE status = 'superseded' AND superseded_by IS NULL "
        f"LIMIT {MAX_REPORTED_ROWS}"
    )
    report.add(
        "source_superseded_rows_have_pointer",
        not pointerless,
        offending_ids=[str(r["id"]) for r in pointerless],
    )

    dangling = await source.fetch(
        "SELECT m.id, m.superseded_by FROM memories m "
        "LEFT JOIN memories p ON p.id = m.superseded_by "
        "WHERE m.superseded_by IS NOT NULL AND p.id IS NULL "
        f"LIMIT {MAX_REPORTED_ROWS}"
    )
    report.add(
        "source_superseded_by_resolves",
        not dangling,
        offending=[
            {"id": str(r["id"]), "superseded_by": str(r["superseded_by"])} for r in dangling
        ],
    )

    cycles = await source.fetch(
        """
        WITH RECURSIVE chain(root, node, path, cycle) AS (
            SELECT id, superseded_by, ARRAY[id], false
              FROM memories
             WHERE superseded_by IS NOT NULL
            UNION ALL
            SELECT c.root, m.superseded_by, c.path || m.id, m.id = ANY(c.path)
              FROM chain c
              JOIN memories m ON m.id = c.node
             WHERE NOT c.cycle
               AND m.superseded_by IS NOT NULL
               AND array_length(c.path, 1) < $1
        )
        SELECT DISTINCT root FROM chain WHERE cycle LIMIT $2
        """,
        MAX_LINEAGE_DEPTH,
        MAX_REPORTED_ROWS,
    )
    report.add(
        "source_superseded_by_acyclic",
        not cycles,
        offending_ids=[str(r["root"]) for r in cycles],
    )


async def check_source_empty_tables(
    source: asyncpg.Connection, report: PreflightReport
) -> None:
    """Assertions 8-9 — a non-zero count means an assumption is wrong."""
    for table in spec.SOURCE_MUST_BE_EMPTY:
        count = await _count(source, table)
        report.add(f"source_{table}_is_empty", count == 0, count=count)


async def check_memory_type_vocabulary(
    source: asyncpg.Connection, report: PreflightReport
) -> None:
    """Assertion 10 — carry verbatim, report, never rewrite.

    MEMORY_TYPES changed under this column and the target has no CHECK, so a
    stale value lands silently. Rewriting it would map an out-of-vocabulary
    value onto ``fact`` and invent a classification for every untyped row, which
    is exactly the harm this task exists to prevent.
    """
    rows = await source.fetch(
        "SELECT memory_type, count(*) AS n FROM memories GROUP BY memory_type ORDER BY 1"
    )
    known = memory_types()
    histogram = {
        ("NULL" if r["memory_type"] is None else r["memory_type"]): r["n"] for r in rows
    }
    out_of_vocabulary = {
        r["memory_type"]: r["n"]
        for r in rows
        if r["memory_type"] is not None and r["memory_type"] not in known
    }
    report.add(
        "source_memory_type_in_vocabulary",
        not out_of_vocabulary,
        histogram=histogram,
        out_of_vocabulary=out_of_vocabulary,
        vocabulary=sorted(known),
    )


async def check_source_orphans(source: asyncpg.Connection, report: PreflightReport) -> None:
    """Assertion 11 — every child reference resolves within the source."""
    orphan_memory_tags = await source.fetch(
        "SELECT mt.memory_id, mt.tag_id FROM memory_tags mt "
        "LEFT JOIN memories m ON m.id = mt.memory_id "
        "LEFT JOIN tags t ON t.id = mt.tag_id "
        "WHERE m.id IS NULL OR t.id IS NULL "
        f"LIMIT {MAX_REPORTED_ROWS}"
    )
    report.add(
        "source_memory_tags_resolve",
        not orphan_memory_tags,
        offending=[
            {"memory_id": str(r["memory_id"]), "tag_id": r["tag_id"]}
            for r in orphan_memory_tags
        ],
    )

    orphan_messages = await source.fetch(
        "SELECT ms.id, ms.conversation_id FROM messages ms "
        "LEFT JOIN conversations c ON c.id = ms.conversation_id "
        "WHERE c.id IS NULL "
        f"LIMIT {MAX_REPORTED_ROWS}"
    )
    report.add(
        "source_messages_resolve",
        not orphan_messages,
        offending=[
            {"id": str(r["id"]), "conversation_id": str(r["conversation_id"])}
            for r in orphan_messages
        ],
    )


async def check_carried_row_counts(
    source: asyncpg.Connection, report: PreflightReport
) -> None:
    """Assertion 12 — the run's expected totals."""
    counts = {table.name: await _count(source, table.name) for table in spec.CARRIED}
    report.add("source_carried_row_counts", True, counts=counts)


async def emit_repository_inventory(
    source: asyncpg.Connection, report: PreflightReport
) -> None:
    """Assertion 13 — an emission, not an assertion.

    repositories is not carried, so the operator re-declares it by hand against
    a database that is about to be replaced. has_auth_token turns that into a
    checklist. The token itself lives in a config row keyed by auth_token_ref,
    and the ref is the pointer to it, so neither goes into a report the operator
    saves to a file.
    """
    columns = ", ".join(spec.REPOSITORY_INVENTORY_COLUMNS)
    rows = await source.fetch(
        f"SELECT {columns}, (auth_token_ref IS NOT NULL) AS has_auth_token "
        "FROM repositories ORDER BY name"
    )
    report.add(
        "source_repository_inventory",
        True,
        repositories=[dict(r) for r in rows],
    )


async def run_preflight(
    source: asyncpg.Connection,
    target: asyncpg.Connection,
    *,
    reset: bool = False,
) -> PreflightReport:
    report = PreflightReport()
    await check_source_revision(source, report)
    await check_source_table_set(source, report)
    if reset:
        await check_reset_derivations_absent(target, report)
    else:
        await check_target_carried_empty(target, report)
    await check_target_revision(target, report)
    await check_lineage(source, report)
    await check_source_empty_tables(source, report)
    await check_memory_type_vocabulary(source, report)
    await check_source_orphans(source, report)
    await check_carried_row_counts(source, report)
    await emit_repository_inventory(source, report)
    return report
