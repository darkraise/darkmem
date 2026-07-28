"""The Tier-C re-extraction backfill: drain, preserve, verify.

T1.51 moved the carried set onto the baseline and wrote the eleven-column
snapshot. This module drives every carried memory through the target
``ProcessingPipeline`` so the derived state doc 19 §4 requires is rebuilt, puts
back the carried columns Phase-5 savepoint A overwrites on its way past, and
diffs the result against that snapshot.

The diff is the only control that can see this task's real failure. Row counts
match, the ``pipeline_failures`` residue is empty and the extraction bench holds
tolerance — all three stay green while ``updated_at``, ``importance`` and the
four enrichment columns are destroyed, because the bench scores ``gold.json``
and not the carried corpus.

Usage, from ``backend/``::

    .venv/bin/python scripts/cutover/backfill.py \
        --target-dsn postgresql://user:pw@host:5433/target \
        --snapshot /var/tmp/cutover/cutover-snapshot-<stamp>.jsonl \
        --report-dir /var/tmp/cutover \
        --max-failures 0 \
        --target-is-quiesced
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

if __package__ in (None, ""):  # direct `python scripts/cutover/backfill.py`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "cutover"

from . import spec  # noqa: E402
from .__main__ import _json_default, _stamp, _write_json  # noqa: E402
from .db import CutoverError, normalise_dsn  # noqa: E402

# Not `job:cutover_backfill`: that prefix is JobRegistry's reserved keyspace and
# `load_config` parses any row under it as a JobConfig. The backfill is a
# one-time operator-run CLI, not a registered job.
CONFIG_KEY = "cutover:backfill"

PIPELINE_NAME = "memory_ingest"

APPLICATION_NAME = "darkmem-cutover-backfill"

TOUCH_TRIGGER = "memories_touch_updated_at"

DEFAULT_BATCH_SIZE = 20

# Problem lists are truncated so an abort names the first offenders rather than
# printing the whole corpus.
MAX_REPORTED = 20

ENRICHMENT_COLUMNS: tuple[str, ...] = (
    "classified_type",
    "summary",
    "emotions",
    "flags",
)

LINEAGE_COLUMNS: tuple[str, ...] = ("status", "superseded_by")

# SQLAlchemy's JSON type defaults to ``none_as_null=False``, so savepoint A's
# ``mem_record.emotions = ... or None`` writes jsonb 'null' rather than SQL NULL.
# Both read back as Python None through the ORM, which is why the two are
# indistinguishable from the application side and have to be collapsed here:
# without this a COALESCE refill never fires and the diff never sees the loss.
JSONB_COLUMNS: tuple[str, ...] = ("emotions", "flags")


class BackfillError(CutoverError):
    """A refusal or an abort. Always names what went wrong and which rows."""


# ---------------------------------------------------------------------------
# The snapshot
# ---------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _encode(value: object) -> str:
    """One representation for both sides of every comparison.

    ``confidence`` is ``real``: a stored 0.9 loads back as 0.8999999761581421,
    so a tolerance argument about float equality is unavoidable unless both
    sides are compared in the encoding the snapshot was written in.
    """
    return json.dumps(value, default=_json_default)


def _normalise(column: str, value: object) -> object:
    if column in JSONB_COLUMNS and value == "null":
        return None
    return value


@dataclass(frozen=True)
class Snapshot:
    path: Path
    sha256: str
    rows: dict[str, dict]

    @property
    def ids(self) -> set[str]:
        return set(self.rows)

    def encoded(self) -> dict[str, dict[str, str]]:
        return {
            mid: {c: _encode(_normalise(c, row[c])) for c in spec.SNAPSHOT_COLUMNS}
            for mid, row in self.rows.items()
        }


def load_snapshot(path: Path) -> Snapshot:
    if not path.is_file():
        raise BackfillError(f"snapshot file does not exist: {path}")
    rows: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise BackfillError(f"{path}:{number} is not JSON: {error}") from error
            missing = [c for c in spec.SNAPSHOT_COLUMNS if c not in row]
            if missing:
                raise BackfillError(
                    f"{path}:{number} is not a cutover snapshot row; missing "
                    + ", ".join(missing)
                )
            mid = str(row["id"])
            if mid in rows:
                raise BackfillError(f"{path}:{number} repeats memory id {mid}")
            rows[mid] = row
    if not rows:
        raise BackfillError(f"snapshot is empty: {path}")
    return Snapshot(path=path.resolve(), sha256=sha256_of(path), rows=rows)


LIVE_SELECT = text(
    """
    SELECT id::text            AS id,
           memory_type,
           importance,
           confidence,
           updated_at,
           status::text        AS status,
           superseded_by::text AS superseded_by,
           classified_type,
           summary,
           emotions::text      AS emotions,
           flags::text         AS flags
    FROM memories
    ORDER BY id
    """
)


async def read_live_rows(session: AsyncSession) -> dict[str, dict[str, str]]:
    """The eleven columns in the snapshot's own representation.

    ``jsonb`` is read through ``::text`` because ``write_snapshot`` runs on a
    connection with no json codec and therefore records the raw jsonb output
    text; a decoded Python list would not compare equal to it.
    """
    result = await session.execute(LIVE_SELECT)
    return {
        row["id"]: {c: _encode(_normalise(c, row[c])) for c in spec.SNAPSHOT_COLUMNS}
        for row in result.mappings()
    }


def _difference_report(
    snapshot: Snapshot, live: dict[str, dict[str, str]]
) -> list[str]:
    problems: list[str] = []
    encoded = snapshot.encoded()
    for mid in sorted(encoded):
        snap_row = encoded[mid]
        live_row = live.get(mid)
        if live_row is None:
            continue
        for column in spec.SNAPSHOT_COLUMNS:
            if snap_row[column] != live_row[column]:
                problems.append(
                    f"{mid}.{column}: snapshot={snap_row[column]} "
                    f"target={live_row[column]}"
                )
            if len(problems) >= MAX_REPORTED:
                return problems
    return problems


def _id_set_problems(snapshot: Snapshot, live_ids: set[str]) -> list[str]:
    problems: list[str] = []
    missing = sorted(snapshot.ids - live_ids)
    extra = sorted(live_ids - snapshot.ids)
    if missing:
        problems.append(
            f"{len(missing)} snapshot id(s) have no live memories row: "
            + ", ".join(missing[:MAX_REPORTED])
        )
    if extra:
        problems.append(
            f"{len(extra)} live memories row(s) are absent from the snapshot: "
            + ", ".join(extra[:MAX_REPORTED])
        )
    return problems


async def assert_snapshot_is_this_load(
    session: AsyncSession, snapshot: Snapshot
) -> None:
    """The virgin-run cover: all eleven columns, not the id set.

    Two loads of the same dump carry identical ids by construction while their
    ``importance``, ``status`` and ``updated_at`` have drifted, so an id check
    adopts a rehearsal snapshot without complaint and the diff then certifies
    the wrong values forever — control and corrective action read the same file,
    so a wrong file makes them agree. T1.51's own reset guard pairs its id check
    with an ``updated_at`` high-water check for exactly this reason
    (``transform.py`` ``reset_dump_membership``).
    """
    live = await read_live_rows(session)
    problems = _id_set_problems(snapshot, set(live))
    problems.extend(_difference_report(snapshot, live))
    if problems:
        raise BackfillError(
            f"{snapshot.path} is not this target's load snapshot:\n  "
            + "\n  ".join(problems)
        )


async def assert_snapshot_id_set(
    session: AsyncSession, snapshot: Snapshot, pass_number: int
) -> None:
    """The per-pass quiescence detector.

    A connection pre-flight cannot prove absence — an idle-reaped pool shows
    zero — and only this sees an insert or a TTL delete arriving after a clean
    start.
    """
    live_ids = set(
        (await session.execute(text("SELECT id::text FROM memories"))).scalars().all()
    )
    problems = _id_set_problems(snapshot, live_ids)
    if problems:
        raise BackfillError(
            f"the target's memories changed under the drain (pass {pass_number}); "
            "it is not quiesced:\n  " + "\n  ".join(problems)
        )


# ---------------------------------------------------------------------------
# Quiescence
# ---------------------------------------------------------------------------


FOREIGN_CONNECTIONS_SQL = text(
    """
    SELECT pid,
           COALESCE(NULLIF(application_name, ''), '(unnamed)') AS application_name,
           COALESCE(client_addr::text, 'local')                AS client_addr,
           COALESCE(state, '(none)')                           AS state
    FROM pg_stat_activity
    WHERE datname = current_database()
      AND pid <> pg_backend_pid()
      -- Background workers carry our datname too: an autovacuum worker shows up
      -- unnamed and active, and reporting it would make the pre-flight fire on
      -- a genuinely quiesced target. A guard that cries wolf gets widened, and
      -- a widened guard is the one that then misses the real writer.
      AND backend_type = 'client backend'
      AND application_name <> ALL (CAST(:ignore AS text[]))
    ORDER BY pid
    """
)


async def foreign_connections(
    session: AsyncSession, *, own_application_names: tuple[str, ...]
) -> list[dict]:
    result = await session.execute(
        FOREIGN_CONNECTIONS_SQL, {"ignore": list(own_application_names)}
    )
    return [dict(row) for row in result.mappings()]


async def assert_no_foreign_connections(
    session: AsyncSession, *, own_application_names: tuple[str, ...]
) -> None:
    rows = await foreign_connections(session, own_application_names=own_application_names)
    if rows:
        described = ", ".join(
            f"pid={r['pid']} application_name={r['application_name']} "
            f"client={r['client_addr']} state={r['state']}"
            for r in rows[:MAX_REPORTED]
        )
        raise BackfillError(
            f"{len(rows)} other connection(s) hold the target database; it is "
            f"not quiesced: {described}"
        )


# ---------------------------------------------------------------------------
# The residue predicate — the resume state
# ---------------------------------------------------------------------------


async def resolve_fingerprint(session: AsyncSession) -> str | None:
    """The one partition the residue query may name.

    None is the legitimate cold start (nothing has embedded yet). Two live rows
    is an embedder rotation mid-drain, and a residue spanning partitions has no
    defined meaning.
    """
    rows = (
        await session.execute(
            text(
                "SELECT fingerprint FROM embedders WHERE retired_at IS NULL "
                "ORDER BY fingerprint"
            )
        )
    ).scalars().all()
    if len(rows) > 1:
        raise BackfillError(
            "the embedders registry holds more than one non-retired fingerprint "
            f"({', '.join(rows)}); a residue count spanning partitions has no "
            "defined meaning"
        )
    return rows[0] if rows else None


async def outstanding(session: AsyncSession, fingerprint: str | None) -> list[uuid.UUID]:
    """Everything not yet backfilled, computed from the database every pass.

    A cursor is a second source of truth about what is done, and a cursor that
    disagrees with the database is exactly the "reported complete while partial"
    failure this task exists to prevent. There is deliberately no
    ``is_archived`` filter: an archived row excluded from the batch but not from
    this predicate would be outstanding forever.
    """
    if fingerprint is None:
        rows = (
            await session.execute(text("SELECT id FROM memories ORDER BY id"))
        ).scalars().all()
        return list(rows)

    from app.services.embedder_registry import child_table

    table = child_table("memory_embeddings", fingerprint)
    rows = (
        await session.execute(
            text(
                f"""
                SELECT m.id FROM memories m
                WHERE NOT EXISTS (
                          SELECT 1 FROM {table} e WHERE e.memory_id = m.id
                      )
                   OR EXISTS (
                          SELECT 1 FROM pipeline_failures f
                          WHERE f.entity_type = 'memory'
                            AND f.entity_id = m.id
                            AND f.pipeline_name = :pipeline
                            AND f.resolved_at IS NULL
                      )
                ORDER BY m.id
                """
            ),
            {"pipeline": PIPELINE_NAME},
        )
    ).scalars().all()
    return list(rows)


# ---------------------------------------------------------------------------
# The entry builder
# ---------------------------------------------------------------------------


async def build_entries(session: AsyncSession, ids: list[uuid.UUID]) -> list[dict]:
    """``process_batch`` entries for the carried rows, carrying memory_type.

    Passing the carried type makes ``normalize_memory_type(memory_type or
    extracted_type)`` an identity for any in-vocabulary value, which is how
    ``memory_type`` is preserved. Archived rows are included, diverging from
    ``AnalyticsService.reprocess_all``: an interactive reprocess should not
    spend model budget on hidden rows, but a cutover must leave the target
    complete because there is no second pass after the freeze.
    """
    from app.models.memory import Memory

    result = await session.execute(
        select(Memory).options(selectinload(Memory.tags)).where(Memory.id.in_(ids))
    )
    by_id = {m.id: m for m in result.scalars().all()}
    entries = []
    for mid in ids:
        memory = by_id.get(mid)
        if memory is None:
            continue
        entries.append(
            {
                "memory_id": memory.id,
                "content": memory.content,
                "source": memory.source,
                "tags": [t.name for t in memory.tags],
                "memory_type": memory.memory_type,
                "created_at": memory.created_at.isoformat() if memory.created_at else "",
            }
        )
    return entries


# ---------------------------------------------------------------------------
# The restore — one statement, two scopes
# ---------------------------------------------------------------------------


RESTORE_SQL = text(
    f"""
    UPDATE memories m SET
        importance      = CAST(s.importance AS double precision),
        classified_type = COALESCE(m.classified_type, s.classified_type),
        summary         = COALESCE(m.summary, s.summary),
        emotions        = CASE
            WHEN m.emotions IS NULL OR jsonb_typeof(m.emotions) = 'null'
            THEN CAST(s.emotions AS jsonb) ELSE m.emotions
        END,
        flags           = CASE
            WHEN m.flags IS NULL OR jsonb_typeof(m.flags) = 'null'
            THEN CAST(s.flags AS jsonb) ELSE m.flags
        END,
        updated_at      = CASE
            WHEN m.status::text        IS NOT DISTINCT FROM s.status
             AND m.superseded_by::text IS NOT DISTINCT FROM s.superseded_by
            THEN CAST(s.updated_at AS timestamptz)
            ELSE m.updated_at
        END
    FROM unnest(
        CAST(:ids AS uuid[]),
        CAST(:importance AS text[]),
        CAST(:classified_type AS text[]),
        CAST(:summary AS text[]),
        CAST(:emotions AS text[]),
        CAST(:flags AS text[]),
        CAST(:updated_at AS text[]),
        CAST(:status AS text[]),
        CAST(:superseded_by AS text[])
    ) AS s(id, importance, classified_type, summary, emotions, flags,
           updated_at, status, superseded_by)
    WHERE m.id = s.id
    """
)


def _restore_params(snapshot: Snapshot, ids: list[str]) -> dict:
    columns = (
        "importance",
        "classified_type",
        "summary",
        "emotions",
        "flags",
        "updated_at",
        "status",
        "superseded_by",
    )
    params: dict[str, list] = {"ids": list(ids)}
    for column in columns:
        params[column] = [
            None if snapshot.rows[mid][column] is None else str(snapshot.rows[mid][column])
            for mid in ids
        ]
    return params


async def restore_carried_columns(
    factory: async_sessionmaker, snapshot: Snapshot, scope: list[uuid.UUID] | None = None
) -> int:
    """Put the carried columns back over what savepoint A wrote.

    One function, two scopes — a batch's ids for resumability, the whole carried
    set once the drain reaches fixpoint. A second statement for the sweep is
    what let the lineage carve-out exist on one scope and not the other, and a
    same-batch supersession victim then ended superseded while claiming its
    carried ``updated_at`` with every check green, because that failure's
    signature is a *zero* delta.

    The statement runs after ``process_batch`` has committed, so between the two
    the rows hold a wall-clock ``updated_at``. That window is bounded by one
    batch and closed by the next resume: the residue predicate re-drains
    anything not both embedded and failure-free, and re-running this over an
    already-restored batch writes the same values.

    ``importance`` is written unconditionally because the carried value is user
    intent and the extractor's is not; the four enrichment columns are refilled
    only where the rebuild left nothing, which is "accept the overwrite, refuse
    the null"; ``status`` and ``superseded_by`` are read for the carve-out and
    for the report and never written.
    """
    ids = [str(m) for m in (scope if scope is not None else snapshot.ids)]
    ids = [mid for mid in ids if mid in snapshot.rows]
    if not ids:
        return 0
    params = _restore_params(snapshot, ids)
    async with factory() as session:
        async with session.begin():
            # Named form, never `session_replication_role = replica`: that also
            # disables the FTS trigger and every FK constraint trigger on the
            # table, and it needs a privilege table ownership does not imply.
            # The disable is transactional, so a crash inside this window cannot
            # leave the trigger off.
            await session.execute(
                text(f"ALTER TABLE memories DISABLE TRIGGER {TOUCH_TRIGGER}")
            )
            result = await session.execute(RESTORE_SQL, params)
            await session.execute(
                text(f"ALTER TABLE memories ENABLE TRIGGER {TOUCH_TRIGGER}")
            )
    return result.rowcount or 0


# ---------------------------------------------------------------------------
# Durable state
# ---------------------------------------------------------------------------


async def read_state(session: AsyncSession) -> dict | None:
    from app.models.config import Config

    return await session.scalar(select(Config.value).where(Config.key == CONFIG_KEY))


async def write_state(factory: async_sessionmaker, payload: dict) -> None:
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    "INSERT INTO config (key, value) "
                    "VALUES (:key, CAST(:value AS jsonb)) "
                    "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
                ),
                {"key": CONFIG_KEY, "value": json.dumps(payload, default=_json_default)},
            )


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@dataclass
class VerificationReport:
    counts: dict = field(default_factory=dict)
    failures: dict = field(default_factory=dict)
    diff: dict = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {
            "counts": self.counts,
            "failures": self.failures,
            "diff": self.diff,
            "problems": self.problems,
            "ok": self.ok,
        }


COUNTS_SQL = text(
    """
    SELECT count(*)::bigint                                                   AS memories,
           count(*) FILTER (WHERE origin_key IS NOT NULL)::bigint             AS origin_key_not_null,
           count(*) FILTER (WHERE search_vector IS NULL)::bigint              AS search_vector_null,
           count(*) FILTER (WHERE status = 'superseded'
                              AND superseded_by IS NULL)::bigint              AS superseded_without_pointer,
           count(*) FILTER (WHERE technologies <> '{}'::text[])::bigint       AS technologies_not_empty,
           count(*) FILTER (WHERE is_archived)::bigint                        AS archived
    FROM memories
    """
)


async def _leg_one(session: AsyncSession) -> tuple[dict, list[str]]:
    row = dict((await session.execute(COUNTS_SQL)).mappings().one())
    for table in ("tags", "memory_tags", "conversations", "messages"):
        row[table] = await session.scalar(text(f"SELECT count(*)::bigint FROM {table}"))
    problems = []
    if row["origin_key_not_null"]:
        problems.append(
            f"{row['origin_key_not_null']} memories gained an origin_key; the "
            "backfill must not manufacture capture-session identity"
        )
    if row["search_vector_null"]:
        problems.append(f"{row['search_vector_null']} memories have a NULL search_vector")
    if row["superseded_without_pointer"]:
        problems.append(
            f"{row['superseded_without_pointer']} memories are superseded with no pointer"
        )
    return row, problems


async def _leg_two(session: AsyncSession, max_failures: int) -> tuple[dict, list[str]]:
    rows = (
        await session.execute(
            text(
                "SELECT entity_id::text AS memory_id, failed_step, error_message, "
                "attempts FROM pipeline_failures "
                "WHERE pipeline_name = :pipeline AND resolved_at IS NULL "
                "ORDER BY failed_step, entity_id"
            ),
            {"pipeline": PIPELINE_NAME},
        )
    ).mappings().all()
    by_step: dict[str, list[dict]] = {}
    for row in rows:
        by_step.setdefault(row["failed_step"], []).append(dict(row))
    report = {"total": len(rows), "by_step": by_step, "max_failures": max_failures}
    problems = []
    if len(rows) > max_failures:
        problems.append(
            f"{len(rows)} unresolved {PIPELINE_NAME} failures exceed "
            f"--max-failures={max_failures}"
        )
    return report, problems


def classify_diff(
    snapshot: Snapshot, live: dict[str, dict[str, str]]
) -> tuple[dict, list[str]]:
    """Six buckets. An unclassified state is undefined, not passing."""
    encoded = snapshot.encoded()
    violations: list[dict] = []
    expected: dict[str, int] = {}
    new_derivation: list[dict] = []
    frozen_lineage: list[str] = []
    memory_type_gained = 0

    missing = sorted(snapshot.ids - set(live))
    unsnapshotted = sorted(set(live) - snapshot.ids)

    def violation(mid: str, column: str, snap: str, target: str) -> None:
        violations.append(
            {"memory_id": mid, "column": column, "snapshot": snap, "target": target}
        )

    for mid in sorted(encoded):
        if mid not in live:
            continue
        snap_row, live_row = encoded[mid], live[mid]
        lineage_moved = any(
            snap_row[c] != live_row[c] for c in LINEAGE_COLUMNS
        )
        if lineage_moved:
            entry = {"memory_id": mid}
            for column in (*LINEAGE_COLUMNS, "updated_at"):
                entry[column] = {
                    "snapshot": snap_row[column],
                    "target": live_row[column],
                }
            new_derivation.append(entry)
            # The zero-delta failure: a supersession victim whose updated_at was
            # restored claims it was last touched before it vanished from the
            # active view. Detected as an unexpected *equality*, which is why a
            # violation list of columns-that-must-not-change cannot see it.
            if snap_row["updated_at"] == live_row["updated_at"]:
                frozen_lineage.append(mid)
        elif snap_row["updated_at"] != live_row["updated_at"]:
            violation(mid, "updated_at", snap_row["updated_at"], live_row["updated_at"])

        if snap_row["importance"] != live_row["importance"]:
            violation(mid, "importance", snap_row["importance"], live_row["importance"])

        if snap_row["memory_type"] != live_row["memory_type"]:
            if snap_row["memory_type"] == _encode(None):
                memory_type_gained += 1
                expected["memory_type"] = expected.get("memory_type", 0) + 1
            else:
                violation(
                    mid, "memory_type", snap_row["memory_type"], live_row["memory_type"]
                )

        if snap_row["confidence"] != live_row["confidence"]:
            expected["confidence"] = expected.get("confidence", 0) + 1

        for column in ENRICHMENT_COLUMNS:
            if snap_row[column] == live_row[column]:
                continue
            # Compared in the normalised encoding, so a carried jsonb 'null' is
            # not mistaken for a value that a rebuild then destroyed.
            if snap_row[column] != _encode(None) and live_row[column] == _encode(None):
                violation(mid, column, snap_row[column], live_row[column])
            else:
                expected[column] = expected.get(column, 0) + 1

    diff = {
        "snapshot_path": str(snapshot.path),
        "snapshot_sha256": snapshot.sha256,
        "snapshot_rows": len(snapshot.rows),
        "live_rows": len(live),
        "violation": violations,
        "expected_rederivation": expected,
        "new_derivation": new_derivation,
        "frozen_lineage": frozen_lineage,
        "missing": missing,
        "unsnapshotted": unsnapshotted,
        "memory_type_gained": memory_type_gained,
    }

    problems: list[str] = []
    if violations:
        named = ", ".join(
            f"{v['memory_id']}.{v['column']}" for v in violations[:MAX_REPORTED]
        )
        problems.append(f"{len(violations)} carried-column violation(s): {named}")
    if frozen_lineage:
        problems.append(
            f"{len(frozen_lineage)} row(s) moved status/superseded_by while keeping "
            f"the carried updated_at: {', '.join(frozen_lineage[:MAX_REPORTED])}"
        )
    if missing:
        problems.append(
            f"{len(missing)} snapshot id(s) have no live row: "
            + ", ".join(missing[:MAX_REPORTED])
        )
    if unsnapshotted:
        problems.append(
            f"{len(unsnapshotted)} live row(s) are absent from the snapshot: "
            + ", ".join(unsnapshotted[:MAX_REPORTED])
        )
    return diff, problems


async def verify_backfill(
    session: AsyncSession, snapshot: Snapshot, max_failures: int
) -> VerificationReport:
    report = VerificationReport()
    report.counts, problems = await _leg_one(session)
    report.problems.extend(problems)

    report.failures, problems = await _leg_two(session, max_failures)
    report.problems.extend(problems)

    live = await read_live_rows(session)
    report.diff, problems = classify_diff(snapshot, live)
    report.problems.extend(problems)
    return report


# ---------------------------------------------------------------------------
# The drain
# ---------------------------------------------------------------------------


@dataclass
class BackfillResult:
    run_id: str
    started_at: str
    snapshot_path: str
    snapshot_sha256: str
    virgin: bool
    passes: int = 0
    batches: int = 0
    drained: int = 0
    archived_drained: int = 0
    outstanding: list[str] = field(default_factory=list)
    stuck: list[str] = field(default_factory=list)
    status: str = "INCOMPLETE"
    finished_at: str | None = None
    error: str | None = None
    verification: dict | None = None

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "snapshot_path": self.snapshot_path,
            "snapshot_sha256": self.snapshot_sha256,
            "virgin": self.virgin,
            "passes": self.passes,
            "batches": self.batches,
            "drained": self.drained,
            "archived_drained": self.archived_drained,
            "outstanding": self.outstanding,
            "stuck": self.stuck,
            "status": self.status,
            "error": self.error,
            "verification": self.verification,
        }


def _chunks(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


async def run_backfill(
    factory: async_sessionmaker,
    pipeline,
    snapshot: Snapshot,
    *,
    max_failures: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
    check_connections: bool = True,
    own_application_names: tuple[str, ...] = (APPLICATION_NAME,),
) -> BackfillResult:
    async with factory() as session:
        state = await read_state(session)
    virgin = state is None

    result = BackfillResult(
        run_id=str(uuid.uuid4()),
        started_at=datetime.now(UTC).isoformat(),
        snapshot_path=str(snapshot.path),
        snapshot_sha256=snapshot.sha256,
        virgin=virgin,
    )

    async with factory() as session:
        if check_connections:
            await assert_no_foreign_connections(
                session, own_application_names=own_application_names
            )
        if virgin:
            await assert_snapshot_is_this_load(session, snapshot)
        else:
            recorded = (state or {}).get("snapshot_sha256")
            if recorded != snapshot.sha256:
                raise BackfillError(
                    f"{snapshot.path} (sha256 {snapshot.sha256}) is not the file "
                    f"this drain adopted (sha256 {recorded}); the virgin-run "
                    "full-value assertion cannot be repeated on a resume, so "
                    "the digest is the only thing binding a later pass to it"
                )

    await write_state(factory, result.to_dict())

    try:
        await _drain(factory, pipeline, snapshot, result, batch_size=batch_size)
        await restore_carried_columns(factory, snapshot)
    except Exception as error:
        result.error = f"{type(error).__name__}: {error}"
        raise
    finally:
        # Every exit path, the exception path included: "reported complete after
        # a crash" is the shape of the failure this whole task exists to stop.
        try:
            async with factory() as session:
                fingerprint = await resolve_fingerprint(session)
                residue = await outstanding(session, fingerprint)
            result.outstanding = [str(m) for m in residue]
            result.status = "COMPLETE" if not residue else "INCOMPLETE"
        except Exception as probe_error:  # pragma: no cover - defensive
            result.status = "INCOMPLETE"
            result.error = result.error or f"residue probe failed: {probe_error}"
        result.finished_at = datetime.now(UTC).isoformat()
        await write_state(factory, result.to_dict())

    async with factory() as session:
        verification = await verify_backfill(session, snapshot, max_failures)
    result.verification = verification.to_dict()
    await write_state(factory, result.to_dict())
    return result


async def _drain(
    factory: async_sessionmaker,
    pipeline,
    snapshot: Snapshot,
    result: BackfillResult,
    *,
    batch_size: int,
) -> None:
    previous_residue: int | None = None
    while True:
        result.passes += 1
        async with factory() as session:
            # Per pass, never once at start-up: a mid-drain embedder rotation
            # would otherwise leave the residue query reading a partition
            # nothing is written to any more, and report COMPLETE against it.
            fingerprint = await resolve_fingerprint(session)
            await assert_snapshot_id_set(session, snapshot, result.passes)
            residue = await outstanding(session, fingerprint)

        if not residue:
            return
        if previous_residue is not None and len(residue) >= previous_residue:
            result.stuck = [str(m) for m in residue]
            return
        previous_residue = len(residue)

        for batch in _chunks(residue, batch_size):
            async with factory() as session:
                entries = await build_entries(session, batch)
                archived = await session.scalar(
                    text(
                        "SELECT count(*) FROM memories "
                        "WHERE id = ANY(CAST(:ids AS uuid[])) AND is_archived"
                    ),
                    {"ids": [str(m) for m in batch]},
                )
            if not entries:
                continue
            await pipeline.process_batch(entries)
            await restore_carried_columns(factory, snapshot, batch)
            result.batches += 1
            result.drained += len(entries)
            result.archived_drained += int(archived or 0)
            await write_state(factory, result.to_dict())


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cutover-backfill",
        description="Drive the carried set through the target pipeline and "
        "diff the result against the load snapshot.",
    )
    parser.add_argument("--target-dsn", required=True)
    parser.add_argument(
        "--snapshot",
        required=True,
        type=Path,
        help="the cutover-snapshot-<stamp>.jsonl written by this target's load; "
        "never globbed, never defaulted",
    )
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument(
        "--max-failures",
        required=True,
        type=int,
        help="the unresolved pipeline_failures residue the operator accepts",
    )
    parser.add_argument(
        "--target-is-quiesced",
        required=True,
        action="store_true",
        help="assert no API process, MCP door or job loop writes the target for "
        "the whole drain",
    )
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--verify-only", action="store_true")
    return parser


async def _build_pipeline(factory: async_sessionmaker):
    from app.api.websocket import event_manager
    from app.services.config import get_llm_config
    from app.services.embedder_registry import (
        EmbedderInfo,
        embedder_registry,
        parse_fingerprint,
    )
    from app.services.llm import LLMOrchestrator
    from app.services.pipeline import ProcessingPipeline

    async with factory() as session:
        llm_config = await get_llm_config(session)
    llm = LLMOrchestrator(llm_config)

    async with factory() as session:
        await embedder_registry.warm_cache_from_db(session)
    async with factory() as session:
        await embedder_registry.reconcile(session)

    fingerprint = llm.llm_fingerprint()
    model_id, dims = parse_fingerprint(fingerprint)
    async with factory() as session:
        await embedder_registry.register(
            session,
            EmbedderInfo(
                fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"
            ),
        )
    return ProcessingPipeline(llm, factory, broadcast=event_manager.broadcast)


async def _resolve_batch_size(factory: async_sessionmaker, requested: int | None) -> int:
    if requested is not None:
        return requested
    from app.services.feature_flags import get_feature_flags_dict

    async with factory() as session:
        flags = await get_feature_flags_dict(session)
    return int(flags.get("embedding_batch_size", DEFAULT_BATCH_SIZE))


def _print_summary(result: BackfillResult) -> None:
    verification = result.verification or {}
    diff = verification.get("diff", {})
    print(f"backfill {result.status} ({len(result.outstanding)} outstanding)")
    print(
        f"  passes={result.passes} batches={result.batches} drained={result.drained} "
        f"archived_drained={result.archived_drained}"
    )
    if result.stuck:
        print(f"  stuck: {', '.join(result.stuck[:MAX_REPORTED])}")
    if diff:
        print(
            "  diff: violation={} frozen_lineage={} missing={} unsnapshotted={} "
            "new_derivation={} memory_type_gained={}".format(
                len(diff.get("violation", [])),
                len(diff.get("frozen_lineage", [])),
                len(diff.get("missing", [])),
                len(diff.get("unsnapshotted", [])),
                len(diff.get("new_derivation", [])),
                diff.get("memory_type_gained", 0),
            )
        )
        print(f"  expected re-derivation: {diff.get('expected_rederivation', {})}")
        print(
            "  NOTE: there is no F1 number against the carried corpus — the "
            "homelab data carries no gold annotations."
        )
    for problem in verification.get("problems", []):
        print(f"  PROBLEM: {problem}")


async def _amain(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    snapshot = load_snapshot(args.snapshot)
    report_dir: Path = args.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = _stamp()

    dsn = normalise_dsn(args.target_dsn).replace(
        "postgresql://", "postgresql+asyncpg://", 1
    )
    engine = create_async_engine(
        dsn,
        connect_args={"server_settings": {"application_name": APPLICATION_NAME}},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        if args.verify_only:
            async with factory() as session:
                report = await verify_backfill(session, snapshot, args.max_failures)
            _write_json(
                report_dir / f"cutover-backfill-diff-{stamp}.json", report.to_dict()
            )
            for problem in report.problems:
                print(f"  PROBLEM: {problem}")
            print("verify-only complete" if report.ok else "verify-only FAILED")
            return 0 if report.ok else 1

        pipeline = await _build_pipeline(factory)
        batch_size = await _resolve_batch_size(factory, args.batch_size)
        result = await run_backfill(
            factory,
            pipeline,
            snapshot,
            max_failures=args.max_failures,
            batch_size=batch_size,
        )
        _write_json(report_dir / f"cutover-backfill-{stamp}.json", result.to_dict())
        _write_json(
            report_dir / f"cutover-backfill-diff-{stamp}.json",
            (result.verification or {}),
        )
        _print_summary(result)
        print(f"reports in {report_dir} — user data, never commit them")
        verification_ok = bool((result.verification or {}).get("ok"))
        return 0 if result.status == "COMPLETE" and verification_ok else 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    try:
        return asyncio.run(_amain(argv))
    except CutoverError as error:
        print(f"BACKFILL ABORTED\n{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
