"""Coverage of the Tier-C re-extraction backfill (T1.52).

The drainer's whole reason to exist is a failure that leaves every other check
green: Phase-5 savepoint A overwrites the carried columns while row counts
match, ``pipeline_failures`` stays empty and the extraction bench holds
tolerance. So these tests are written to fail when a guard is removed, and the
two mutation proofs at the bottom disable the restore and the lineage carve-out
on purpose and assert the diff turns red.

Two rules from the plan's ruling 7 are load-bearing here:

* the eleven columns are listed **literally** in this module and never imported
  from ``spec.SNAPSHOT_COLUMNS`` — a test that imports the constant it defends
  passes for every value of that constant;
* the snapshot every assertion compares against is produced by T1.51's own
  ``write_snapshot`` **before** the drain, never by the backfill, so the diff
  cannot be structurally incapable of reporting a violation.

Everything runs against a private ``<base>_bfill`` database derived from
``TEST_DATABASE_URL`` — never the real ``darkmem``, and never the shared
unnumbered ones. That privacy is what lets the connection pre-flight be
exercised honestly instead of stubbed.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from cutover import backfill  # noqa: E402
from cutover import db as cutover_db  # noqa: E402
from cutover.__main__ import write_snapshot  # noqa: E402

from app.services.embedder_registry import child_table, embedder_registry  # noqa: E402
from app.services.pipeline import ProcessingPipeline, _flag_cache_reset  # noqa: E402
from tests.test_pipeline_phase1 import FakeEmbedder  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parents[1]

TEST_DSN = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://darkmem:darkmem@localhost:5433/darkmem_test",
)
BASE = cutover_db.dsn_identity(TEST_DSN)
BFILL_DB = f"{BASE.database}_bfill"


def _dsn_for(database: str) -> str:
    _, _, rest = cutover_db.normalise_dsn(TEST_DSN).partition("://")
    authority = rest.split("/", 1)[0]
    return f"postgresql://{authority}/{database}"


BFILL_DSN = _dsn_for(BFILL_DB)
BFILL_ASYNC_DSN = BFILL_DSN.replace("postgresql://", "postgresql+asyncpg://", 1)
ADMIN_DSN = _dsn_for("postgres")

# Listed literally, never imported from spec.SNAPSHOT_COLUMNS. This is the whole
# control: if the snapshot ever stops carrying one of these, the assertion below
# must fail rather than quietly narrowing with it.
ELEVEN_COLUMNS = (
    "id",
    "memory_type",
    "importance",
    "confidence",
    "updated_at",
    "status",
    "superseded_by",
    "classified_type",
    "summary",
    "emotions",
    "flags",
)

CARRIED_UPDATED_AT = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

WIPE = (
    "memory_tags",
    "memory_crossrefs",
    "entity_relations",
    "entities",
    "pipeline_failures",
    "messages",
    "conversations",
    "memories",
    "tags",
    "config",
    "embedders",
)


async def _admin_execute(statement: str) -> None:
    conn = await asyncpg.connect(ADMIN_DSN)
    try:
        await conn.execute(statement)
    finally:
        await conn.close()


async def _drop_database(name: str) -> None:
    await _admin_execute(
        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
        f"WHERE datname = '{name}' AND pid <> pg_backend_pid()"
    )
    await _admin_execute(f'DROP DATABASE IF EXISTS "{name}"')


def _alembic_upgrade(dsn: str) -> None:
    env = {**os.environ, "DATABASE_URL": dsn.replace("postgresql://", "postgresql+asyncpg://")}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic upgrade head failed for {dsn}:\n{result.stdout}\n{result.stderr}"
        )


@pytest_asyncio.fixture(scope="session")
async def backfill_database():
    await _drop_database(BFILL_DB)
    await _admin_execute(f'CREATE DATABASE "{BFILL_DB}"')
    _alembic_upgrade(BFILL_DSN)
    yield
    await _drop_database(BFILL_DB)


class FakeClassifier:
    """The two-call path, so the classification result is under test control.

    Returning ``pipeline.classification`` here instead would make the pipeline
    fold classification into the extraction call, and the empty-result case this
    module has to reproduce would be unreachable.
    """

    def __init__(self, results):
        self.results = results

    async def classify(self, content, areas, prompt, mode="simple"):
        result = self.results(content) if callable(self.results) else self.results
        return dict(result) if result is not None else None


EMPTY_EXTRACTION = {"entities": [], "relationships": [], "memory_type": "fact"}
FULL_CLASSIFICATION = {
    "hall": "decision",
    "summary": "a rebuilt summary",
    "emotions": ["calm"],
    "flags": ["rebuilt"],
}
EMPTY_CLASSIFICATION = {"hall": "", "summary": "", "emotions": [], "flags": []}


def _as_jsonb(value, fallback) -> str:
    """A str is already jsonb text and is inserted verbatim.

    ``json.dumps`` round-tripping it would round a numeric past a double's
    precision, which is the very thing the round-trip test below exists to
    disprove.
    """
    if value is None:
        return json.dumps(fallback)
    return value if isinstance(value, str) else json.dumps(value)


@dataclass
class Bed:
    engine: object
    factory: async_sessionmaker
    pipe: ProcessingPipeline
    fingerprint: str
    report_dir: Path
    extractions: dict = field(default_factory=dict)
    default_extraction: dict = field(default_factory=lambda: dict(EMPTY_EXTRACTION))
    classification: object = field(default_factory=lambda: dict(FULL_CLASSIFICATION))
    extraction_errors: set = field(default_factory=set)

    async def seed(
        self,
        content: str,
        *,
        memory_id: uuid.UUID | None = None,
        memory_type: str | None = "decision",
        importance: float = 0.42,
        confidence: float = 0.9,
        classified_type: str | None = "carried-type",
        summary: str | None = "carried summary",
        emotions: list | str | None = None,
        flags: list | str | None = None,
        is_archived: bool = False,
        created_at: datetime | None = None,
        updated_at: datetime = CARRIED_UPDATED_AT,
        technologies: list[str] | None = None,
        status: str = "active",
    ) -> uuid.UUID:
        memory_id = memory_id or uuid.uuid4()
        async with self.factory() as session:
            async with session.begin():
                await session.execute(
                    text(
                        """
                        INSERT INTO memories (
                            id, content, source, memory_type, importance, metadata,
                            created_at, updated_at, is_archived, classified_type,
                            summary, emotions, flags, project, status, confidence,
                            technologies
                        ) VALUES (
                            CAST(:id AS uuid), :content, 'api', :memory_type,
                            :importance, CAST('{}' AS jsonb), CAST(:created_at AS timestamptz),
                            CAST(:updated_at AS timestamptz), :is_archived, :classified_type,
                            :summary, CAST(:emotions AS jsonb), CAST(:flags AS jsonb),
                            'default', CAST(:status AS memory_status), :confidence,
                            CAST(:technologies AS text[])
                        )
                        """
                    ),
                    {
                        "id": str(memory_id),
                        "content": content,
                        "memory_type": memory_type,
                        "importance": importance,
                        "created_at": created_at or datetime.now(timezone.utc),
                        "updated_at": updated_at,
                        "is_archived": is_archived,
                        "classified_type": classified_type,
                        "summary": summary,
                        "emotions": _as_jsonb(emotions, ["carried"]),
                        "flags": _as_jsonb(flags, ["verified-carry"]),
                        "status": status,
                        "confidence": confidence,
                        "technologies": technologies or [],
                    },
                )
        return memory_id

    async def snapshot(self, name: str = "cutover-snapshot-test.jsonl") -> backfill.Snapshot:
        path = self.report_dir / name
        conn = await asyncpg.connect(BFILL_DSN)
        try:
            await write_snapshot(conn, path)
        finally:
            await conn.close()
        return backfill.load_snapshot(path)

    async def row(self, memory_id: uuid.UUID) -> dict:
        async with self.factory() as session:
            result = await session.execute(
                text(
                    "SELECT id::text AS id, memory_type, importance, confidence, "
                    "updated_at, status::text AS status, "
                    "superseded_by::text AS superseded_by, classified_type, summary, "
                    "emotions::text AS emotions, flags::text AS flags, "
                    "technologies, origin_key "
                    "FROM memories WHERE id = CAST(:id AS uuid)"
                ),
                {"id": str(memory_id)},
            )
            return dict(result.mappings().one())

    async def scalar(self, sql: str, **params):
        async with self.factory() as session:
            return await session.scalar(text(sql), params)


@pytest_asyncio.fixture
async def bed(backfill_database, tmp_path, request):
    engine = create_async_engine(
        BFILL_ASYNC_DSN,
        connect_args={"server_settings": {"application_name": backfill.APPLICATION_NAME}},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    fingerprint = f"bfill-{abs(hash(request.node.name)) % 10**8}|4"
    async with factory() as session:
        async with session.begin():
            partitions = (
                await session.execute(
                    text(
                        "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                        "AND (tablename LIKE 'memory_embeddings\\_\\_%' "
                        "  OR tablename LIKE 'entity_embeddings\\_\\_%' "
                        "  OR tablename LIKE 'entity_embedding_cache\\_\\_%' "
                        "  OR tablename LIKE 'code_chunk_embeddings\\_\\_%')"
                    )
                )
            ).scalars().all()
            for table in partitions:
                await session.execute(text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
            await session.execute(
                text("TRUNCATE " + ", ".join(WIPE) + " RESTART IDENTITY CASCADE")
            )
    embedder_registry._known.clear()
    _flag_cache_reset()

    from app.services.events import reconcile_event_partitions

    async with factory() as session:
        await reconcile_event_partitions(session)
        await session.commit()

    the_bed = Bed(
        engine=engine,
        factory=factory,
        pipe=ProcessingPipeline(FakeEmbedder([fingerprint]), factory),
        fingerprint=fingerprint,
        report_dir=tmp_path,
    )

    async def _extract(content, system_prompt=None, **kwargs):
        if content in the_bed.extraction_errors:
            raise RuntimeError("extraction unavailable")
        return dict(the_bed.extractions.get(content, the_bed.default_extraction))

    async def _resolve():
        return FakeClassifier(the_bed.classification)

    the_bed.pipe.extraction.extract = _extract  # type: ignore[method-assign]
    the_bed.pipe._resolve_classifier = _resolve  # type: ignore[method-assign]

    yield the_bed

    embedder_registry._known.clear()
    _flag_cache_reset()
    await engine.dispose()


async def _drain(bed: Bed, snapshot: backfill.Snapshot, **kwargs):
    return await backfill.run_backfill(
        bed.factory,
        bed.pipe,
        snapshot,
        max_failures=kwargs.pop("max_failures", 0),
        batch_size=kwargs.pop("batch_size", 20),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Step 1 — the residue predicate and the fingerprint guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_a_memory_with_neither_an_embedding_nor_a_failure_is_outstanding(bed):
    memory_id = await bed.seed("nothing has embedded this yet")
    async with bed.factory() as session:
        assert await backfill.resolve_fingerprint(session) is None
        assert await backfill.outstanding(session, None) == [memory_id]


@pytest.mark.asyncio
async def test_an_embedded_failure_free_memory_is_not_outstanding(bed):
    memory_id = await bed.seed("pgvector is the store")
    await bed.pipe._register_fingerprint(bed.fingerprint)
    table = child_table("memory_embeddings", bed.fingerprint)
    async with bed.factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    f"INSERT INTO {table} (memory_id, fingerprint, embedding) "
                    "VALUES (CAST(:m AS uuid), :f, CAST(:v AS vector))"
                ),
                {"m": str(memory_id), "f": bed.fingerprint, "v": "[0.1,0.2,0.3,0.4]"},
            )
    async with bed.factory() as session:
        assert await backfill.outstanding(session, bed.fingerprint) == []


@pytest.mark.asyncio
async def test_an_unresolved_ingest_failure_makes_an_embedded_memory_outstanding(bed):
    """Clause (b). A savepoint-B failure leaves the vector behind, so clause (a)
    alone would report the memory done while its graph was never written."""
    memory_id = await bed.seed("the graph write failed")
    await bed.pipe._register_fingerprint(bed.fingerprint)
    table = child_table("memory_embeddings", bed.fingerprint)
    async with bed.factory() as session:
        async with session.begin():
            await session.execute(
                text(
                    f"INSERT INTO {table} (memory_id, fingerprint, embedding) "
                    "VALUES (CAST(:m AS uuid), :f, CAST(:v AS vector))"
                ),
                {"m": str(memory_id), "f": bed.fingerprint, "v": "[0.1,0.2,0.3,0.4]"},
            )
            await session.execute(
                text(
                    "INSERT INTO pipeline_failures "
                    "(id, entity_type, entity_id, pipeline_name, failed_step, attempts) "
                    "VALUES (gen_random_uuid(), 'memory', CAST(:m AS uuid), "
                    "'memory_ingest', 'graph', 1)"
                ),
                {"m": str(memory_id)},
            )
    async with bed.factory() as session:
        assert await backfill.outstanding(session, bed.fingerprint) == [memory_id]


@pytest.mark.asyncio
async def test_an_archived_memory_is_outstanding_too(bed):
    """No ``is_archived`` filter on either clause, asserted literally.

    Inheriting ``AnalyticsService.reprocess_all``'s filter would leave archived
    rows outstanding forever and report INCOMPLETE on every future run.
    """
    archived = await bed.seed("hidden but carried", is_archived=True)
    async with bed.factory() as session:
        assert archived in await backfill.outstanding(session, None)


@pytest.mark.asyncio
async def test_two_non_retired_embedders_abort_naming_both(bed):
    async with bed.factory() as session:
        async with session.begin():
            for name, dims in (("alpha|4", 4), ("beta|4", 4)):
                await session.execute(
                    text(
                        "INSERT INTO embedders (fingerprint, model_id, dims, source) "
                        "VALUES (:f, :m, :d, 'llm')"
                    ),
                    {"f": name, "m": name.split("|")[0], "d": dims},
                )
    async with bed.factory() as session:
        with pytest.raises(backfill.BackfillError) as error:
            await backfill.resolve_fingerprint(session)
    assert "alpha|4" in str(error.value)
    assert "beta|4" in str(error.value)


# ---------------------------------------------------------------------------
# Step 2 — the entry builder
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_entry_carries_the_rows_memory_type(bed):
    """Asserted against the literal ``"decision"``.

    ``entry["memory_type"] == memory.memory_type`` would pass if the builder
    dropped the field on a row whose type happened to be NULL, which is the one
    case the assertion exists to exclude.
    """
    memory_id = await bed.seed("a decision was taken", memory_type="decision")
    async with bed.factory() as session:
        entries = await backfill.build_entries(session, [memory_id])
    assert len(entries) == 1
    assert entries[0]["memory_type"] == "decision"
    assert entries[0]["memory_id"] == memory_id


# ---------------------------------------------------------------------------
# Step 3 — the restore, one function over two scopes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_updated_at_survives_the_confidence_rewrite(bed):
    """Probe 5, reproduced end to end.

    ``memories.confidence`` is ``real``: a stored 0.9 loads back as
    0.8999999761581421, the estimator hands back 0.9, and SQLAlchemy emits an
    ``UPDATE`` that writes ``updated_at=now()`` in its own SET list. The value
    round-trips to identical float4 bits, so the write is a no-op the ORM cannot
    see is a no-op — and it destroys the timestamp anyway.
    """
    memory_id = await bed.seed("this deployment is verified", confidence=0.9)
    snapshot = await bed.snapshot()

    await _drain(bed, snapshot)

    row = await bed.row(memory_id)
    assert row["updated_at"] == CARRIED_UPDATED_AT


@pytest.mark.asyncio
async def test_importance_is_restored_over_the_extractor_value(bed):
    memory_id = await bed.seed("a carried memory", importance=0.42)
    bed.default_extraction = {**EMPTY_EXTRACTION, "importance": 0.99}
    snapshot = await bed.snapshot()

    await _drain(bed, snapshot)

    assert (await bed.row(memory_id))["importance"] == pytest.approx(0.42)


@pytest.mark.asyncio
async def test_a_carried_summary_survives_an_empty_classifier(bed):
    """The refuse-the-null half of the enrichment decision.

    ``mem_record.summary = llm_classification.get("summary") or None`` turns an
    empty string into a NULL, which is a deletion with no replacement rather
    than the rebuild doc 19 §4 asks for.
    """
    memory_id = await bed.seed("a carried memory", summary="carried summary")
    bed.classification = dict(EMPTY_CLASSIFICATION)
    snapshot = await bed.snapshot()

    await _drain(bed, snapshot)

    row = await bed.row(memory_id)
    assert row["summary"] == "carried summary"
    assert row["classified_type"] == "carried-type"
    assert json.loads(row["emotions"]) == ["carried"]
    assert json.loads(row["flags"]) == ["verified-carry"]


@pytest.mark.asyncio
async def test_a_rebuilt_summary_is_kept_not_reverted(bed):
    """The other direction of the same COALESCE, so the operator is pinned.

    ``s.summary`` instead of ``COALESCE(m.summary, s.summary)`` would pass the
    test above and silently throw away every new derivation.
    """
    memory_id = await bed.seed("a carried memory", summary="carried summary")
    bed.classification = dict(FULL_CLASSIFICATION)
    snapshot = await bed.snapshot()

    await _drain(bed, snapshot)

    row = await bed.row(memory_id)
    assert row["summary"] == "a rebuilt summary"
    assert row["classified_type"] == "decision"
    assert json.loads(row["flags"]) == ["rebuilt"]


@pytest.mark.asyncio
async def test_a_high_precision_jsonb_value_survives_the_round_trip(bed):
    """The property T1.51's ``json.loads(`` grep stands in for, pinned directly.

    Postgres stores a jsonb numeric as arbitrary-precision ``numeric``. It
    reaches the snapshot as an already-encoded JSON *string* — asyncpg installs
    no json codec — so the drainer's parse hands it back opaque and the restore
    writes the same bytes. Decoding it as a Python float anywhere on that path
    would round it, silently and irreversibly.
    """
    precise = "[1.2345678901234567890123456789]"
    memory_id = await bed.seed("a carried memory", emotions=precise)
    before = (await bed.row(memory_id))["emotions"]
    assert before == precise

    snapshot = await bed.snapshot()
    assert snapshot.rows[str(memory_id)]["emotions"] == precise

    bed.classification = dict(EMPTY_CLASSIFICATION)
    await _drain(bed, snapshot)

    assert (await bed.row(memory_id))["emotions"] == precise


@pytest.mark.asyncio
async def test_the_restore_is_idempotent(bed):
    memory_id = await bed.seed("a carried memory")
    snapshot = await bed.snapshot()
    await _drain(bed, snapshot)
    before = await bed.row(memory_id)

    await backfill.restore_carried_columns(bed.factory, snapshot, [memory_id])
    await backfill.restore_carried_columns(bed.factory, snapshot)

    assert await bed.row(memory_id) == before


@pytest.mark.asyncio
async def test_the_touch_trigger_is_enabled_after_the_restore(bed):
    memory_id = await bed.seed("a carried memory")
    snapshot = await bed.snapshot()
    await backfill.restore_carried_columns(bed.factory, snapshot, [memory_id])

    state = await bed.scalar(
        "SELECT tgenabled::text FROM pg_trigger WHERE tgname = :name",
        name=backfill.TOUCH_TRIGGER,
    )
    assert state == "O"


@pytest.mark.asyncio
async def test_a_null_superseded_by_on_both_sides_is_restored(bed):
    """The mutation proof for ``IS NOT DISTINCT FROM``.

    ``superseded_by`` is NULL on almost every row and ``NULL = NULL`` is NULL,
    so a naive ``=`` sends the whole corpus down the ``ELSE`` arm and the
    restore preserves nothing at all.
    """
    memory_id = await bed.seed("this deployment is verified", confidence=0.9)
    snapshot = await bed.snapshot()
    assert snapshot.rows[str(memory_id)]["superseded_by"] is None

    await _drain(bed, snapshot)

    row = await bed.row(memory_id)
    assert row["superseded_by"] is None
    assert row["updated_at"] == CARRIED_UPDATED_AT


FAISS_EXTRACTION = {
    "entities": [{"name": "faiss", "type": "tool"}],
    "relationships": [],
    "memory_type": "fact",
}

REPLACES_EXTRACTION = {
    "entities": [
        {"name": "Pgvector", "type": "tool"},
        {"name": "faiss", "type": "tool"},
    ],
    "relationships": [
        {"source": "pgvector", "target": "faiss", "type": "REPLACES", "weight": 0.9},
    ],
    "memory_type": "fact",
}


VICTIM_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
REPLACER_ID = uuid.UUID("22222222-2222-4222-8222-222222222222")


async def _seed_supersession_pair(bed: Bed) -> tuple[uuid.UUID, uuid.UUID]:
    """The victim's id sorts first, so the residue's ORDER BY drains it first.

    The victim carries its own extraction because savepoint B recomputes
    ``technologies`` from the graph: an empty extraction would wipe the seeded
    denorm before the replacer's detector reads it, and whether supersession
    fired at all would then depend on batch ordering.
    """
    now = datetime.now(timezone.utc)
    victim = await bed.seed(
        "faiss is the vector store",
        memory_id=VICTIM_ID,
        created_at=now - timedelta(days=3),
        technologies=["faiss"],
    )
    replacer = await bed.seed(
        "pgvector replaces faiss",
        memory_id=REPLACER_ID,
        created_at=now - timedelta(days=1),
    )
    bed.extractions["faiss is the vector store"] = dict(FAISS_EXTRACTION)
    bed.extractions["pgvector replaces faiss"] = dict(REPLACES_EXTRACTION)
    return victim, replacer


@pytest.mark.asyncio
async def test_a_cross_batch_supersession_victim_is_repaired_by_the_sweep(bed):
    """``detect_supersessions`` writes *other* memories' rows.

    A victim finished and restored in batch 1 has its ``updated_at`` moved back
    to wall clock by batch 2, long after batch 1's restore ran. The terminal
    sweep is the only thing that sees it; without the sweep this assertion
    fails.
    """
    victim, replacer = await _seed_supersession_pair(bed)
    snapshot = await bed.snapshot()

    await _drain(bed, snapshot, batch_size=1)

    victim_row = await bed.row(victim)
    assert victim_row["status"] == "superseded"
    assert victim_row["superseded_by"] == str(replacer)
    # The lineage moved, so the carve-out withholds the carried timestamp: a
    # row that vanished from the active view must not claim it was last
    # touched in 2020.
    assert victim_row["updated_at"] > CARRIED_UPDATED_AT

    replacer_row = await bed.row(replacer)
    assert replacer_row["status"] == "active"
    assert replacer_row["updated_at"] == CARRIED_UPDATED_AT


@pytest.mark.asyncio
async def test_a_same_batch_supersession_victim_keeps_the_wall_clock_stamp(bed):
    """The case the plan's first draft got wrong, asserted positively.

    Within-batch supersession is supported behaviour — ``candidate_stmt`` carries
    an id tie-break precisely so it can fire. With the carve-out only on the
    terminal sweep, the per-batch restore wrote the victim's carried
    ``updated_at`` back and the sweep then *skipped* the row, leaving a
    superseded memory claiming it was last touched in 2020 with a zero delta
    that alarms nothing.
    """
    victim, _ = await _seed_supersession_pair(bed)
    snapshot = await bed.snapshot()

    # One batch, both memories.
    await _drain(bed, snapshot, batch_size=10)

    victim_row = await bed.row(victim)
    assert victim_row["status"] == "superseded"
    assert victim_row["updated_at"] > CARRIED_UPDATED_AT


@pytest.mark.asyncio
async def test_technologies_is_rebuilt_and_origin_key_stays_null(bed):
    memory_id = await bed.seed("faiss is the vector store")
    bed.extractions["faiss is the vector store"] = dict(FAISS_EXTRACTION)
    snapshot = await bed.snapshot()
    assert (await bed.row(memory_id))["technologies"] == []

    await _drain(bed, snapshot)

    row = await bed.row(memory_id)
    assert row["technologies"] == ["faiss"]
    assert row["origin_key"] is None


# ---------------------------------------------------------------------------
# Step 3a — the quiescence pre-flight and the snapshot binding
# ---------------------------------------------------------------------------


def test_omitting_target_is_quiesced_is_an_argparse_error():
    with pytest.raises(SystemExit):
        backfill.build_parser().parse_args(
            [
                "--target-dsn", "postgresql://x/y",
                "--snapshot", "s.jsonl",
                "--report-dir", "/tmp/r",
                "--max-failures", "0",
            ]
        )


def test_omitting_max_failures_is_an_argparse_error():
    with pytest.raises(SystemExit):
        backfill.build_parser().parse_args(
            [
                "--target-dsn", "postgresql://x/y",
                "--snapshot", "s.jsonl",
                "--report-dir", "/tmp/r",
                "--target-is-quiesced",
            ]
        )


def test_the_snapshot_path_has_no_default():
    with pytest.raises(SystemExit):
        backfill.build_parser().parse_args(
            [
                "--target-dsn", "postgresql://x/y",
                "--report-dir", "/tmp/r",
                "--max-failures", "0",
                "--target-is-quiesced",
            ]
        )


@pytest.mark.asyncio
async def test_a_snapshot_with_one_drifted_value_aborts_the_virgin_run(bed):
    """Id-set equality does not imply value equality.

    Two loads of the same dump carry identical ids by construction while their
    ``importance`` has drifted through a ``MemoryUpdate``. This fixture is built
    by copying a valid snapshot and editing one value, so the ids are identical
    by construction and only the eleven-column assertion can see the drift.
    """
    memory_id = await bed.seed("a carried memory", importance=0.42)
    good = await bed.snapshot()

    drifted_path = bed.report_dir / "cutover-snapshot-rehearsal.jsonl"
    row = dict(good.rows[str(memory_id)])
    row["importance"] = 0.99
    drifted_path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    drifted = backfill.load_snapshot(drifted_path)
    assert drifted.ids == good.ids

    with pytest.raises(backfill.BackfillError) as error:
        await _drain(bed, drifted)
    assert str(memory_id) in str(error.value)
    assert "importance" in str(error.value)


@pytest.mark.asyncio
async def test_the_virgin_assertion_covers_all_eleven_columns(bed):
    """Every one of the eleven, driven one at a time from a literal list."""
    mutations = {
        "id": str(uuid.uuid4()),
        "memory_type": "problem",
        "importance": 0.99,
        "confidence": 0.5,
        "updated_at": "2021-05-05T00:00:00+00:00",
        "status": "deprecated",
        "superseded_by": str(uuid.uuid4()),
        "classified_type": "other-type",
        "summary": "other summary",
        "emotions": '["other"]',
        "flags": '["other"]',
    }
    assert tuple(mutations) == ELEVEN_COLUMNS

    memory_id = await bed.seed("a carried memory")
    good = await bed.snapshot()

    for column, value in mutations.items():
        path = bed.report_dir / f"snapshot-{column}.jsonl"
        row = dict(good.rows[str(memory_id)])
        row[column] = value
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        with pytest.raises(backfill.BackfillError) as error:
            async with bed.factory() as session:
                await backfill.assert_snapshot_is_this_load(
                    session, backfill.load_snapshot(path)
                )
        assert column in str(error.value), column


@pytest.mark.asyncio
async def test_a_resume_handed_a_different_file_aborts_on_the_sha256(bed):
    """The virgin assertion cannot be repeated on a resume — by then the drain
    has legitimately changed the columns it would compare — so the digest is the
    only thing binding a later pass to the file the first pass adopted."""
    memory_id = await bed.seed("a carried memory")
    snapshot = await bed.snapshot()
    await _drain(bed, snapshot)

    twin = bed.report_dir / "cutover-snapshot-twin.jsonl"
    row = dict(snapshot.rows[str(memory_id)])
    row["summary"] = "a different run's summary"
    twin.write_text(json.dumps(row) + "\n", encoding="utf-8")
    other = backfill.load_snapshot(twin)
    assert other.ids == snapshot.ids

    with pytest.raises(backfill.BackfillError) as error:
        await _drain(bed, other)
    assert other.sha256 in str(error.value)
    assert snapshot.sha256 in str(error.value)


@pytest.mark.asyncio
async def test_a_foreign_connection_is_detected_and_named(bed):
    await bed.seed("a carried memory")
    snapshot = await bed.snapshot()

    intruder = await asyncpg.connect(
        BFILL_DSN, server_settings={"application_name": "pretend-uvicorn"}
    )
    try:
        with pytest.raises(backfill.BackfillError) as error:
            await _drain(bed, snapshot)
        assert "pretend-uvicorn" in str(error.value)
        assert "not quiesced" in str(error.value)
    finally:
        await intruder.close()


@pytest.mark.asyncio
async def test_the_preflight_passes_when_only_the_drainer_is_connected(bed):
    """The other direction, so the detector is not vacuously green."""
    await bed.seed("a carried memory")
    snapshot = await bed.snapshot()
    result = await _drain(bed, snapshot)
    assert result.status == "COMPLETE"


@pytest.mark.asyncio
async def test_a_row_inserted_between_passes_aborts_the_next_pass(bed):
    """A live MCP capture or a ``buffer_flush`` tick, driven directly.

    The connection pre-flight cannot see this — it passed cleanly before the
    first batch — so only the per-pass id re-check does.
    """
    await bed.seed("a carried memory")
    snapshot = await bed.snapshot()

    original = backfill.outstanding
    inserted = uuid.uuid4()

    async def _insert_then_delegate(session, fingerprint):
        rows = await original(session, fingerprint)
        if not getattr(_insert_then_delegate, "done", False):
            _insert_then_delegate.done = True
            await bed.seed("a live capture", memory_id=inserted)
        return rows

    backfill.outstanding = _insert_then_delegate
    try:
        with pytest.raises(backfill.BackfillError) as error:
            await _drain(bed, snapshot)
    finally:
        backfill.outstanding = original
    assert str(inserted) in str(error.value)
    assert "not quiesced" in str(error.value)


@pytest.mark.asyncio
async def test_no_job_prefixed_config_row_is_written(bed):
    await bed.seed("a carried memory")
    snapshot = await bed.snapshot()
    await _drain(bed, snapshot)

    keys = await bed.scalar("SELECT count(*) FROM config WHERE key LIKE 'job:%'")
    assert keys == 0
    state = await bed.scalar(
        "SELECT count(*) FROM config WHERE key = :key", key=backfill.CONFIG_KEY
    )
    assert state == 1


# ---------------------------------------------------------------------------
# Step 4 — the drain loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_an_interrupted_drain_resumes_and_drains_only_the_remainder(bed):
    # Explicit, ordered ids: the residue is ORDER BY id, so batch n holds ids[n].
    ids = [
        await bed.seed(
            f"carried memory {i}",
            memory_id=uuid.UUID(f"{i + 1}{i + 1}{i + 1}{i + 1}1111-1111-4111-8111-111111111111"),
        )
        for i in range(3)
    ]
    snapshot = await bed.snapshot()

    calls: list[list[dict]] = []
    real_process = bed.pipe.process_batch
    explode_on: set[int] = {2}

    async def _recording(entries):
        calls.append(entries)
        if len(calls) in explode_on:
            raise RuntimeError("drain killed mid-run")
        return await real_process(entries)

    bed.pipe.process_batch = _recording  # type: ignore[method-assign]
    # Matched on the message: BackfillError subclasses RuntimeError, so a bare
    # pytest.raises(RuntimeError) would swallow a quiescence abort and the
    # assertions below would then fail on a missing config row instead.
    with pytest.raises(RuntimeError, match="drain killed mid-run"):
        await _drain(bed, snapshot, batch_size=1)

    assert (await bed.row(ids[0]))["updated_at"] == CARRIED_UPDATED_AT
    async with bed.factory() as session:
        state = await backfill.read_state(session)
    assert state["status"] == "INCOMPLETE"
    assert state["outstanding"] == [str(ids[1]), str(ids[2])]

    explode_on.clear()
    calls.clear()
    result = await _drain(bed, snapshot, batch_size=1)

    drained_ids = {str(e["memory_id"]) for batch in calls for e in batch}
    assert drained_ids == {str(ids[1]), str(ids[2])}
    assert result.status == "COMPLETE"


@pytest.mark.asyncio
async def test_a_permanently_failing_row_lands_in_the_stuck_set(bed):
    good = await bed.seed("carried memory that works")
    bad = await bed.seed("carried memory that never extracts")
    bed.extraction_errors.add("carried memory that never extracts")
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot, batch_size=1, max_failures=1)

    assert result.status == "INCOMPLETE"
    assert result.stuck == [str(bad)]
    assert str(good) not in result.outstanding
    assert result.passes < 10


@pytest.mark.asyncio
async def test_a_crash_mid_drain_still_writes_incomplete(bed):
    await bed.seed("carried memory")
    snapshot = await bed.snapshot()

    async def _boom(entries):
        raise RuntimeError("the process died")

    bed.pipe.process_batch = _boom  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="the process died"):
        await _drain(bed, snapshot)

    async with bed.factory() as session:
        state = await backfill.read_state(session)
    assert state["status"] == "INCOMPLETE"
    assert state["error"].startswith("RuntimeError")
    assert len(state["outstanding"]) == 1


@pytest.mark.asyncio
async def test_a_clean_run_reports_complete_and_no_residue(bed):
    await bed.seed("carried memory")
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot)

    assert result.status == "COMPLETE"
    assert result.outstanding == []
    assert result.verification["ok"] is True
    assert result.verification["failures"]["total"] == 0
    assert result.archived_drained == 0


@pytest.mark.asyncio
async def test_archived_rows_are_drained_and_counted(bed):
    await bed.seed("a visible carried memory")
    await bed.seed("a hidden carried memory", is_archived=True)
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot)

    assert result.status == "COMPLETE"
    assert result.archived_drained == 1


# ---------------------------------------------------------------------------
# Step 5 — the six-bucket diff and its mutation proofs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_the_diff_classifies_every_bucket(bed):
    """One row per bucket, including the two states the original three-bucket
    spec left undefined."""
    kept = await bed.seed("kept carried memory")
    superseded = await bed.seed("superseded carried memory")
    gone = await bed.seed("deleted carried memory")
    snapshot = await bed.snapshot()

    new_row = await bed.seed("a live capture")
    async with bed.factory() as session:
        async with session.begin():
            await session.execute(
                text("DELETE FROM memories WHERE id = CAST(:id AS uuid)"),
                {"id": str(gone)},
            )
            await session.execute(
                text(
                    "UPDATE memories SET status='superseded', "
                    "superseded_by=CAST(:k AS uuid) WHERE id = CAST(:s AS uuid)"
                ),
                {"k": str(kept), "s": str(superseded)},
            )
            await session.execute(
                text(
                    "UPDATE memories SET importance = 0.99 WHERE id = CAST(:k AS uuid)"
                ),
                {"k": str(kept)},
            )

    async with bed.factory() as session:
        live = await backfill.read_live_rows(session)
    diff, problems = backfill.classify_diff(snapshot, live)

    assert [v["column"] for v in diff["violation"] if v["memory_id"] == str(kept)] == [
        "updated_at",
        "importance",
    ]
    assert [e["memory_id"] for e in diff["new_derivation"]] == [str(superseded)]
    assert diff["missing"] == [str(gone)]
    assert diff["unsnapshotted"] == [str(new_row)]
    assert diff["frozen_lineage"] == []
    assert len(problems) == 3


@pytest.mark.asyncio
async def test_the_frozen_lineage_bucket_fires_on_a_zero_delta(bed):
    """The one violation detected as an unexpected *equality*."""
    kept = await bed.seed("kept carried memory")
    victim = await bed.seed("victim carried memory")
    snapshot = await bed.snapshot()

    async with bed.factory() as session:
        async with session.begin():
            await session.execute(
                text("ALTER TABLE memories DISABLE TRIGGER memories_touch_updated_at")
            )
            await session.execute(
                text(
                    "UPDATE memories SET status='superseded', "
                    "superseded_by=CAST(:k AS uuid) WHERE id = CAST(:v AS uuid)"
                ),
                {"k": str(kept), "v": str(victim)},
            )
            await session.execute(
                text("ALTER TABLE memories ENABLE TRIGGER memories_touch_updated_at")
            )

    async with bed.factory() as session:
        live = await backfill.read_live_rows(session)
    diff, problems = backfill.classify_diff(snapshot, live)

    assert diff["frozen_lineage"] == [str(victim)]
    assert any("carried updated_at" in p for p in problems)


@pytest.mark.asyncio
async def test_confidence_and_the_enrichment_overwrite_are_expected_not_violations(bed):
    await bed.seed("this deployment is verified", confidence=0.5)
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot)

    diff = result.verification["diff"]
    assert diff["violation"] == []
    assert diff["expected_rederivation"]["confidence"] == 1
    assert diff["expected_rederivation"]["classified_type"] == 1
    assert diff["expected_rederivation"]["summary"] == 1


@pytest.mark.asyncio
async def test_a_null_carried_memory_type_is_counted_as_gained(bed):
    await bed.seed("a carried memory with no type", memory_type=None)
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot)

    assert result.verification["diff"]["memory_type_gained"] == 1
    assert result.verification["diff"]["violation"] == []


@pytest.mark.asyncio
async def test_the_violation_bucket_fills_when_the_restore_is_removed(bed, monkeypatch):
    """The mutation proof. A diff that stays green with the restore disabled is
    a diff that proves nothing."""
    await bed.seed("this deployment is verified", confidence=0.9, importance=0.42)
    bed.default_extraction = {**EMPTY_EXTRACTION, "importance": 0.99}
    snapshot = await bed.snapshot()

    async def _no_restore(*args, **kwargs):
        return 0

    monkeypatch.setattr(backfill, "restore_carried_columns", _no_restore)
    result = await _drain(bed, snapshot)

    columns = {v["column"] for v in result.verification["diff"]["violation"]}
    assert columns == {"updated_at", "importance"}
    assert result.verification["ok"] is False


@pytest.mark.asyncio
async def test_frozen_lineage_fills_when_the_case_is_dropped(bed, monkeypatch):
    """The second mutation proof, and the one that covers the same-batch victim.

    Dropping the ``CASE`` from the shared statement makes the per-batch restore
    write a superseded row's carried ``updated_at`` back. The delta is then
    zero, so only the frozen-lineage bucket can see it.
    """
    victim, _ = await _seed_supersession_pair(bed)
    snapshot = await bed.snapshot()

    flat = text(
        str(backfill.RESTORE_SQL)
        .replace(
            """updated_at      = CASE
            WHEN m.status::text        IS NOT DISTINCT FROM s.status
             AND m.superseded_by::text IS NOT DISTINCT FROM s.superseded_by
            THEN CAST(s.updated_at AS timestamptz)
            ELSE m.updated_at
        END""",
            "updated_at = CAST(s.updated_at AS timestamptz)",
        )
    )
    assert "IS NOT DISTINCT FROM" not in str(flat)
    monkeypatch.setattr(backfill, "RESTORE_SQL", flat)

    result = await _drain(bed, snapshot, batch_size=10)

    assert result.verification["diff"]["frozen_lineage"] == [str(victim)]
    assert result.verification["ok"] is False


@pytest.mark.asyncio
async def test_the_update_memories_writer_set_is_exactly_four(bed):
    """§9.1's logged assertion: the restore's correctness depends on when it runs
    relative to writes it does not issue, so the writer set is checked rather
    than assumed. ``demote_dependents`` must be absent — it fires only from the
    TTL sweep and the interactive delete, so seeing it is a quiescence breach.
    """
    await _seed_supersession_pair(bed)
    snapshot = await bed.snapshot()

    seen: list[str] = []

    @event.listens_for(bed.engine.sync_engine, "before_cursor_execute")
    def _capture(conn, cursor, statement, parameters, context, executemany):
        collapsed = " ".join(statement.split())
        if collapsed.upper().startswith("UPDATE MEMORIES"):
            seen.append(collapsed)

    try:
        await _drain(bed, snapshot, batch_size=1)
    finally:
        event.remove(bed.engine.sync_engine, "before_cursor_execute", _capture)

    def classify(statement: str) -> str:
        if "FROM unnest(" in statement:
            return "restore"
        if "status='deprecated'" in statement:
            return "demote_dependents"
        if "technologies=" in statement:
            return "savepoint_b_technologies"
        if "status=" in statement and "superseded_by=" in statement:
            return "detect_supersessions"
        return "savepoint_a_enrichment"

    writers = {classify(s) for s in seen}
    assert writers == {
        "savepoint_a_enrichment",
        "savepoint_b_technologies",
        "detect_supersessions",
        "restore",
    }
    assert "demote_dependents" not in writers


@pytest.mark.asyncio
async def test_the_failure_residue_is_bounded_by_max_failures(bed):
    await bed.seed("carried memory that never extracts")
    bed.extraction_errors.add("carried memory that never extracts")
    snapshot = await bed.snapshot()

    result = await _drain(bed, snapshot, max_failures=0)

    assert result.verification["ok"] is False
    assert any("--max-failures=0" in p for p in result.verification["problems"])
    assert result.verification["failures"]["total"] == 1
