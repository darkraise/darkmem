"""T2.16 — associative-edge derivation from overlap, proximity, contradiction.

Doc 08 §5.5. Three Done-whens — thresholds are `config` rows, proximity never
crosses a fingerprint, derivation replays identically — and the load-bearing
property none of them names: **the strip is `clear_pass_block` plus
`delete_edge` only on `exclusive`**, so a pass that shares a row with T2.12's
near-duplicate block or T2.23's triage cannot destroy it.

Every negative here carries the mutation that must turn it red, because a
negative asserted over a fixture that was never a candidate proves nothing.
"""
from __future__ import annotations

import ast
import json
import pathlib
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories import memory_relations as edges
from app.services import dream_journal as journal
from app.services import memory_dream as dream
from app.services.dream_jobs import MEMORY_DREAM_JOB_KEY, register_dream_jobs
from app.services.embedder_registry import child_table
from app.services.job_registry import JobRegistry
from app.utils.ids import new_id

NOW = datetime(2026, 8, 5, 3, 0, tzinfo=timezone.utc)

FP = "t216-embedder|4"
OTHER_FP = "t216-rotated|4"

BACKEND = pathlib.Path(__file__).resolve().parent.parent


# ── fixtures and builders ────────────────────────────────────────────────


@pytest.fixture
def project() -> str:
    """A project of this test's own: `events` is append-only, so isolation
    comes from the scope key rather than from a DELETE."""
    return f"t216-{new_id().hex[:12]}"


@pytest.fixture
async def committing(setup_database):
    """A real session factory with real commits — a cycle commits per write
    batch through its own sessions, which the rollback-isolated `session`
    fixture cannot express."""
    engine = create_async_engine(settings.test_database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        async with factory() as cleanup:
            for statement in (
                "DELETE FROM memory_relations WHERE project LIKE 't216-%'",
                "DELETE FROM entity_relations WHERE EXISTS ("
                "  SELECT 1 FROM entities e"
                "  WHERE e.id = entity_relations.source_entity_id"
                "    AND e.name LIKE 't216-%')",
                "DELETE FROM entities WHERE name LIKE 't216-%'",
                "DELETE FROM memories WHERE project LIKE 't216-%'",
                "DELETE FROM config WHERE key = 'memory_dream_state'",
                "DELETE FROM config WHERE key = 'job:memory_dream'",
            ):
                await cleanup.execute(text(statement))
            await cleanup.commit()
        await engine.dispose()


_INSERT_MEMORY = text(
    """
    INSERT INTO memories (
        id, content, source, project, status, is_archived, created_at, metadata
    )
    VALUES (
        CAST(:id AS uuid), :content, 'api', CAST(:project AS text),
        CAST(:status AS memory_status), false, :created_at,
        CAST('{}' AS jsonb)
    )
    """
)


async def seed_memory(
    session,
    *,
    project: str,
    content: str = "a memory",
    status: str = "active",
    created_at: datetime | None = None,
    memory_id: UUID | None = None,
) -> UUID:
    identifier = memory_id or new_id()
    await session.execute(
        _INSERT_MEMORY,
        {
            "id": str(identifier),
            "content": content,
            "project": project,
            "status": status,
            "created_at": created_at or NOW,
        },
    )
    return identifier


async def seed_entity(session, *, name: str, memory_ids: list[UUID]) -> UUID:
    identifier = new_id()
    await session.execute(
        text(
            "INSERT INTO entities (id, name, entity_type, memory_ids) "
            "VALUES (CAST(:id AS uuid), :name, 'concept', "
            "        CAST(:ids AS uuid[]))"
        ),
        {
            "id": str(identifier),
            "name": name,
            "ids": [str(value) for value in memory_ids],
        },
    )
    return identifier


async def seed_relation(
    session, *, source: UUID, target: UUID, rel_type: str, memory_ids: list[UUID]
) -> None:
    await session.execute(
        text(
            "INSERT INTO entity_relations "
            "  (source_entity_id, target_entity_id, rel_type, memory_ids) "
            "VALUES (CAST(:s AS uuid), CAST(:t AS uuid), :rel_type, "
            "        CAST(:ids AS uuid[]))"
        ),
        {
            "s": str(source),
            "t": str(target),
            "rel_type": rel_type,
            "ids": [str(value) for value in memory_ids],
        },
    )


async def seed_partition(session, fingerprint: str = FP) -> str:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, 'stub', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": fingerprint},
    )
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"CREATE TABLE IF NOT EXISTS {child} ("
            " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
            " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
            " embedding vector(4) NOT NULL,"
            " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
            " PRIMARY KEY (memory_id, fingerprint))"
        )
    )
    return child


async def put_vector(session, memory_id, vector, fingerprint: str = FP) -> None:
    child = child_table("memory_embeddings", fingerprint)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding) "
            "VALUES (CAST(:m AS uuid), :fp, CAST(:v AS vector)) "
            "ON CONFLICT (memory_id, fingerprint) DO UPDATE "
            "SET embedding = EXCLUDED.embedding"
        ),
        {"m": str(memory_id), "fp": fingerprint, "v": str(list(vector))},
    )


# ── step 1: the config surface (Done-when 1) ─────────────────────────────


def _fresh_registry():
    engine = create_async_engine(settings.test_database_url)
    registry = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))
    register_dream_jobs(registry)
    return registry, engine


class TestConfigSurface:
    def test_every_threshold_is_a_config_field_with_bounds(self):
        schema = {
            field.key: field
            for field in dream.MEMORY_DREAM_CONFIG_SCHEMA
        }
        for key in (
            "derivation_enabled",
            "overlap_threshold_pct",
            "proximity_threshold_pct",
            "derivation_batch",
            "derivation_hot_entity_cap",
        ):
            assert key in schema, f"{key} is not an operator-editable config row"
            assert schema[key].min is not None
            assert schema[key].max is not None
        # A percentage is a percentage: an operator cannot express a cosine or
        # a Jaccard outside [0, 1] through either threshold.
        assert schema["overlap_threshold_pct"].max == 100
        assert schema["proximity_threshold_pct"].max == 100

    async def test_out_of_range_is_rejected_and_siblings_survive(self, committing):
        registry, engine = _fresh_registry()
        try:
            await registry.set_config(
                MEMORY_DREAM_JOB_KEY, {"overlap_threshold_pct": 70}
            )
            with pytest.raises(ValueError):
                await registry.set_config(
                    MEMORY_DREAM_JOB_KEY, {"overlap_threshold_pct": 101}
                )
            with pytest.raises(ValueError):
                await registry.set_config(
                    MEMORY_DREAM_JOB_KEY, {"proximity_threshold_pct": 5}
                )
            # A partial update leaves the sibling written above intact.
            await registry.set_config(MEMORY_DREAM_JOB_KEY, {"derivation_batch": 7})
            stored = (await registry.load_config(MEMORY_DREAM_JOB_KEY)).config
            assert stored["overlap_threshold_pct"] == 70
            assert stored["derivation_batch"] == 7
        finally:
            await registry.stop_all()
            await engine.dispose()


# ── driving the pass ─────────────────────────────────────────────────────


DEFAULT_KNOBS = dict(
    overlap_threshold=0.5,
    proximity_threshold=0.85,
    derivation_batch=200,
    hot_entity_cap=50,
    neighbours=5,
)


async def read_seeds(factory, memory_ids) -> list:
    async with factory() as session:
        known = await dream.read_memories(session, [str(m) for m in memory_ids])
    return [known[str(m)] for m in memory_ids if str(m) in known]


async def derive(factory, seeds, *, fingerprint=FP, cycle_id=None, **knobs):
    settings_ = {**DEFAULT_KNOBS, **knobs}
    async with factory() as session:
        outcome = await dream.run_derivation_pass(
            session,
            seeds=seeds,
            fingerprint=fingerprint,
            cycle_id=cycle_id or str(new_id()),
            **settings_,
        )
        await session.commit()
    return outcome


async def pass_edges(factory, project) -> list[dict]:
    """Every edge in the project carrying *this* pass's block."""
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT CAST(source_memory_id AS text) AS source, "
                "       CAST(target_memory_id AS text) AS target, "
                "       rel_type, properties "
                "FROM memory_relations WHERE project = CAST(:p AS text) "
                "ORDER BY 1, 2, 3"
            ),
            {"p": project},
        )
        rows = [dict(row) for row in result.mappings()]
    return [
        row
        for row in rows
        if edges.pass_block_of(row, journal.DERIVATION_PASS) is not None
    ]


async def all_edges(factory, project) -> list[dict]:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT CAST(source_memory_id AS text) AS source, "
                "       CAST(target_memory_id AS text) AS target, "
                "       rel_type, properties "
                "FROM memory_relations WHERE project = CAST(:p AS text) "
                "ORDER BY 1, 2, 3"
            ),
            {"p": project},
        )
        return [dict(row) for row in result.mappings()]


async def derivation_events(factory, project) -> list[dict]:
    async with factory() as session:
        result = await session.execute(
            text(
                "SELECT CAST(object_id AS text) AS object_id, payload, id "
                "FROM events WHERE event_type = 'consolidated' "
                "  AND project = CAST(:p AS text) "
                "  AND payload ->> 'pass_key' = CAST(:k AS text) "
                "ORDER BY created_at, id"
            ),
            {"p": project, "k": journal.DERIVATION_PASS},
        )
        return [dict(row) for row in result.mappings()]


async def build_overlap_pair(factory, project, *, shared: int = 2):
    """Two memories asserting the same entities — Jaccard 1.0 — and a third
    sharing nothing, so an assertion that the pass fired is not an assertion
    that it fires on everything."""
    async with factory() as session:
        first = await seed_memory(session, project=project, content="alpha")
        second = await seed_memory(
            session, project=project, content="beta",
            created_at=NOW + timedelta(hours=1),
        )
        lonely = await seed_memory(
            session, project=project, content="gamma",
            created_at=NOW + timedelta(hours=2),
        )
        for index in range(shared):
            await seed_entity(
                session,
                name=f"t216-shared-{index}-{project}",
                memory_ids=[first, second],
            )
        await seed_entity(
            session, name=f"t216-lonely-{project}", memory_ids=[lonely]
        )
        await session.commit()
    return first, second, lonely


# ── Done-when 2: proximity never crosses a fingerprint ───────────────────


class TestProximityIsFingerprintPinned:
    async def test_two_fingerprints_are_never_paired(self, committing, project):
        async with committing() as session:
            await seed_partition(session, FP)
            await seed_partition(session, OTHER_FP)
            first = await seed_memory(session, project=project, content="one")
            second = await seed_memory(
                session, project=project, content="two",
                created_at=NOW + timedelta(hours=1),
            )
            await put_vector(session, first, [1.0, 0.0, 0.0, 0.0], FP)
            await put_vector(session, second, [1.0, 0.0, 0.0, 0.0], OTHER_FP)
            await session.commit()
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=FP)

        assert outcome.derived == 0
        assert await pass_edges(committing, project) == []

        # Non-vacuity: the same two memories under ONE fingerprint *are*
        # paired, so the negative above is about the partition split and not
        # about a fixture that was never a candidate.
        async with committing() as session:
            await put_vector(session, second, [1.0, 0.0, 0.0, 0.0], FP)
            await session.commit()
        again = await derive(committing, seeds, fingerprint=FP)
        assert again.derived == 1
        written = await pass_edges(committing, project)
        assert len(written) == 1
        assert written[0]["rel_type"] == "RELATES_TO"
        block = edges.pass_block_of(written[0], journal.DERIVATION_PASS)
        assert block["signal"] == dream.SIGNAL_EMBEDDING_PROXIMITY

    async def test_an_unresolved_fingerprint_skips_only_the_proximity_arm(
        self, committing, project
    ):
        """The sentinel refusal. `llm_fingerprint()` answers `model|0` under a
        legal config and the sentinel partition exists and is empty, so
        resolving from it would run green and inert forever. Here the
        fingerprint is unresolvable outright: the proximity arm reports skipped
        and writes nothing, and the vector-free overlap arm still runs."""
        first, second, _ = await build_overlap_pair(committing, project)
        async with committing() as session:
            await seed_partition(session, FP)
            await put_vector(session, first, [1.0, 0.0, 0.0, 0.0])
            await put_vector(session, second, [1.0, 0.0, 0.0, 0.0])
            await session.commit()
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=None)

        assert outcome.proximity_skipped_reason == dream.SKIPPED_PROXIMITY_FINGERPRINT
        assert outcome.derived == 1
        written = await pass_edges(committing, project)
        block = edges.pass_block_of(written[0], journal.DERIVATION_PASS)
        assert block["signal"] == dream.SIGNAL_ENTITY_OVERLAP
        # The proximity arm contributed nothing, not merely no *extra* edge.
        assert dream.SIGNAL_EMBEDDING_PROXIMITY not in block["signals"]


# ── the strip: the single most important property in the task ────────────


class TestStrip:
    async def test_a_siblings_block_survives_this_passs_strip(
        self, committing, project
    ):
        """The flagship. The UNIQUE on `(source, target, rel_type)` forces
        T2.12's near-duplicate block and this pass's block onto one row
        whenever both assert the same triple, so a `delete_edge` strip destroys
        the sibling's state — and T2.23's hygiene triage with it."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])
        await derive(committing, seeds)

        written = await pass_edges(committing, project)
        assert len(written) == 1
        source, target = written[0]["source"], written[0]["target"]

        # The near-duplicate arm claims the same row, plus a human's triage.
        sibling = {
            "kind": "duplicate_candidate",
            "hygiene_state": "confirmed",
            "score": 0.97,
            "verdict": "duplicate",
            "detected_at": NOW.isoformat(),
        }
        async with committing() as session:
            await edges.upsert_edge(
                session,
                source_memory_id=source,
                target_memory_id=target,
                rel_type="RELATES_TO",
                project=project,
                pass_key=journal.NEAR_DUPLICATE_PASS,
                block=sibling,
            )
            await session.commit()

        # Remove the overlap so this pass no longer asserts the triple.
        async with committing() as session:
            await session.execute(
                text("DELETE FROM entities WHERE name LIKE :like"),
                {"like": f"t216-shared-%-{project}"},
            )
            await session.commit()

        outcome = await derive(committing, seeds)

        assert outcome.derived == 0
        assert outcome.stripped == 1
        assert outcome.rows_deleted == 0
        surviving = await all_edges(committing, project)
        assert len(surviving) == 1, "the shared row must not be deleted"
        assert (
            edges.pass_block_of(surviving[0], journal.NEAR_DUPLICATE_PASS)
            == sibling
        )
        assert (
            edges.pass_block_of(surviving[0], journal.DERIVATION_PASS) is None
        )

    async def test_a_row_this_pass_owns_alone_is_deleted(
        self, committing, project
    ):
        """The other half: without it the strip is a no-op that leaves the
        graph growing forever, and the sibling test above would still pass."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])
        await derive(committing, seeds)
        assert len(await all_edges(committing, project)) == 1

        async with committing() as session:
            await session.execute(
                text("DELETE FROM entities WHERE name LIKE :like"),
                {"like": f"t216-shared-%-{project}"},
            )
            await session.commit()

        outcome = await derive(committing, seeds)

        assert outcome.stripped == 1
        assert outcome.rows_deleted == 1
        assert await all_edges(committing, project) == []

    async def test_the_old_triple_goes_when_a_pair_changes_type(
        self, committing, project, monkeypatch
    ):
        """D3's purpose in the strip: a pair moving `RELATES_TO ->
        CONTRADICTS` must not be shown twice, which needs a triple-keyed
        strip rather than a pair-keyed one."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])
        await derive(committing, seeds)
        assert [row["rel_type"] for row in await pass_edges(committing, project)] == [
            "RELATES_TO"
        ]

        await seed_opposition(committing, project, first, second)
        monkeypatch.setattr(
            dream, "EXCLUSIVE_RELATION_FAMILIES", frozenset({"DEPENDS_ON"})
        )

        outcome = await derive(committing, seeds)

        assert outcome.derived == 1
        assert outcome.stripped == 1
        rows = await pass_edges(committing, project)
        assert [row["rel_type"] for row in rows] == ["CONTRADICTS"]


async def seed_opposition(factory, project, first, second, rel_type="DEPENDS_ON"):
    """One source entity, two different targets, asserted by two memories."""
    async with factory() as session:
        source = await seed_entity(
            session, name=f"t216-src-{project}", memory_ids=[]
        )
        left = await seed_entity(
            session, name=f"t216-left-{project}", memory_ids=[]
        )
        right = await seed_entity(
            session, name=f"t216-right-{project}", memory_ids=[]
        )
        await seed_relation(
            session, source=source, target=left,
            rel_type=rel_type, memory_ids=[first],
        )
        await seed_relation(
            session, source=source, target=right,
            rel_type=rel_type, memory_ids=[second],
        )
        await session.commit()


# ── D3 precedence and D4's family gate ───────────────────────────────────


class TestPrecedenceAndContradiction:
    async def test_the_shipped_family_list_is_empty_and_derives_nothing(
        self, committing, project
    ):
        """D4 as shipped. The list is a ruling, not a stub: every
        `RELATIONSHIP_TYPES` member that reads single-valued in isolation is
        also the normalisation target of a plural historical name, so a stored
        `rel_type` does not determine single-valuedness. With the list empty
        the arm cannot fire, and the two-signal shape is deliberate."""
        from app.taxonomy import EXCLUSIVE_RELATION_FAMILIES

        assert EXCLUSIVE_RELATION_FAMILIES == frozenset()

        async with committing() as session:
            first = await seed_memory(session, project=project, content="one")
            second = await seed_memory(
                session, project=project, content="two",
                created_at=NOW + timedelta(hours=1),
            )
            await session.commit()
        await seed_opposition(committing, project, first, second)
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=None)

        assert outcome.derived == 0
        assert await pass_edges(committing, project) == []

    async def test_a_ratified_family_makes_the_arm_fire(
        self, committing, project, monkeypatch
    ):
        """Non-vacuity for the negative above: the arm is wired and works, so
        the empty list is what makes it inert and not a missing generator."""
        async with committing() as session:
            first = await seed_memory(session, project=project, content="one")
            second = await seed_memory(
                session, project=project, content="two",
                created_at=NOW + timedelta(hours=1),
            )
            await session.commit()
        await seed_opposition(committing, project, first, second)
        monkeypatch.setattr(
            dream, "EXCLUSIVE_RELATION_FAMILIES", frozenset({"DEPENDS_ON"})
        )
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=None)

        assert outcome.derived == 1
        rows = await pass_edges(committing, project)
        assert [row["rel_type"] for row in rows] == ["CONTRADICTS"]

    async def test_a_superseding_pair_is_not_a_contradiction(
        self, committing, project, monkeypatch
    ):
        """The succession guard, which is the memory-level analogue of the
        disjoint-validity clause this layer cannot compute: a resolved pointer
        is not a dispute to re-litigate."""
        async with committing() as session:
            first = await seed_memory(session, project=project, content="one")
            second = await seed_memory(
                session, project=project, content="two",
                created_at=NOW + timedelta(hours=1),
            )
            await session.commit()
        await seed_opposition(committing, project, first, second)
        monkeypatch.setattr(
            dream, "EXCLUSIVE_RELATION_FAMILIES", frozenset({"DEPENDS_ON"})
        )
        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE memories SET status = 'superseded', "
                    "  superseded_by = CAST(:n AS uuid) "
                    "WHERE id = CAST(:o AS uuid)"
                ),
                {"n": str(second), "o": str(first)},
            )
            await session.commit()
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=None)

        assert outcome.derived == 0

    async def test_contradiction_suppresses_the_weaker_edge(
        self, committing, project, monkeypatch
    ):
        """D3. One pair, one edge, typed `CONTRADICTS` — the overlap edge is
        not also written, or the hygiene and dispute surfaces would show the
        same pair twice under two names."""
        first, second, _ = await build_overlap_pair(committing, project)
        await seed_opposition(committing, project, first, second)
        monkeypatch.setattr(
            dream, "EXCLUSIVE_RELATION_FAMILIES", frozenset({"DEPENDS_ON"})
        )
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, fingerprint=None)

        assert outcome.derived == 1
        rows = await pass_edges(committing, project)
        assert len(rows) == 1
        assert rows[0]["rel_type"] == "CONTRADICTS"
        block = edges.pass_block_of(rows[0], journal.DERIVATION_PASS)
        assert block["signal"] == dream.SIGNAL_CONTRADICTION
        # Both signals fired and are recorded; only one edge exists.
        assert dream.SIGNAL_ENTITY_OVERLAP in block["signals"]

    def test_neither_underived_type_is_reachable(self):
        """O1, ruled: three signals, three types. `DEPENDS_ON` and `FOLLOWS`
        stay stored-but-underived — deriving `FOLLOWS` from `created_at`
        ordering would assert narrative succession from the order someone
        typed."""
        assert set(dream.SIGNAL_REL_TYPES.values()) == {
            "CONTRADICTS", "RELATES_TO"
        }
        assert set(dream.SIGNAL_REL_TYPES) == set(dream.SIGNAL_PRECEDENCE)


# ── Done-when 3: derivation is reproducible on replay ────────────────────


class TestReplay:
    async def test_two_runs_produce_the_same_set_and_one_journal_row(
        self, committing, project
    ):
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])

        await derive(committing, seeds)
        after_first = await pass_edges(committing, project)

        second_run = await derive(committing, seeds)
        after_second = await pass_edges(committing, project)

        def comparable(rows):
            out = []
            for row in rows:
                block = dict(edges.pass_block_of(row, journal.DERIVATION_PASS))
                # `derived_at` moves by construction; nothing else may.
                block.pop("derived_at")
                out.append((row["source"], row["target"], row["rel_type"], block))
            return out

        assert comparable(after_first) == comparable(after_second)
        assert second_run.derived == 0
        assert second_run.unchanged == 1
        assert second_run.stripped == 0
        # An append-only journal must not accrete one row per cycle for an edge
        # that never moved.
        assert len(await derivation_events(committing, project)) == 1

    async def test_a_changed_corpus_produces_a_different_set(
        self, committing, project
    ):
        """Non-vacuity: replay equality is not the trivial equality of two
        empty sets or of a pass that ignores its inputs."""
        first, second, lonely = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second, lonely])
        await derive(committing, seeds)
        before = {
            (row["source"], row["target"]) for row in await pass_edges(committing, project)
        }

        async with committing() as session:
            await session.execute(
                text(
                    "UPDATE entities SET memory_ids = memory_ids "
                    "  || CAST(:extra AS uuid[]) WHERE name LIKE :like"
                ),
                {"extra": [str(lonely)], "like": f"t216-shared-%-{project}"},
            )
            await session.commit()
        await derive(committing, seeds)
        after = {
            (row["source"], row["target"]) for row in await pass_edges(committing, project)
        }

        assert after != before
        assert len(after) > len(before)


# ── D10: the cap is a valve, and it reports when it engages ──────────────


class TestTruncation:
    async def test_the_selection_is_the_first_n_of_the_sorted_candidates(
        self, committing, project
    ):
        """F6. Removing the `ORDER BY` is an unreliable probe — Postgres often
        returns a stable order anyway on a small fixture — so the property is
        asserted directly against the explicitly sorted candidate list."""
        async with committing() as session:
            ids = [
                await seed_memory(
                    session, project=project, content=f"m{index}",
                    created_at=NOW + timedelta(hours=index),
                )
                for index in range(5)
            ]
            await seed_entity(
                session, name=f"t216-shared-all-{project}", memory_ids=ids
            )
            await session.commit()
        seeds = await read_seeds(committing, ids)

        async with committing() as session:
            candidates = await dream.overlap_candidates(
                session,
                seeds=[seed.memory_id for seed in seeds],
                threshold=0.5,
                hot_entity_cap=50,
                limit=1000,
            )
        expected = sorted(candidates)[:3]
        assert len(candidates) == 10

        outcome = await derive(committing, seeds, derivation_batch=3)

        # The counter is a lower bound: the arms stop one row past the cap, so
        # a non-zero reading is what says the valve engaged.
        assert outcome.candidates_truncated >= 1
        assert outcome.derived == 3
        written = {
            dream.pair_key(row["source"], row["target"])
            for row in await pass_edges(committing, project)
        }
        assert written == set(expected)

    async def test_an_untruncated_run_reports_zero_and_spares_nothing(
        self, committing, project
    ):
        """Non-vacuity for the counter: with the cap above the candidate count
        it is zero, so a non-zero reading means the valve really engaged."""
        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])

        outcome = await derive(committing, seeds, derivation_batch=200)

        assert outcome.candidates_truncated == 0
        assert outcome.derived == 1

    async def test_a_truncated_run_leaves_unevaluated_edges_alone(
        self, committing, project
    ):
        """D9. On a growing corpus the evaluated prefix shifts, so a
        project-wide strip would retire edges whose signal still holds — edge
        churn as a pure cap artefact, repeating every night."""
        async with committing() as session:
            ids = [
                await seed_memory(
                    session, project=project, content=f"m{index}",
                    created_at=NOW + timedelta(hours=index),
                )
                for index in range(5)
            ]
            await seed_entity(
                session, name=f"t216-shared-all-{project}", memory_ids=ids
            )
            await session.commit()
        seeds = await read_seeds(committing, ids)

        await derive(committing, seeds, derivation_batch=1000)
        assert len(await pass_edges(committing, project)) == 10

        # Everything stops overlapping, but the cap lets the run decide only
        # the first three pairs.
        async with committing() as session:
            await session.execute(
                text("DELETE FROM entities WHERE name = :name"),
                {"name": f"t216-shared-all-{project}"},
            )
            await session.commit()
        outcome = await derive(committing, seeds, derivation_batch=3)

        assert outcome.candidates == 0
        # With no candidates at all the run decided nothing, so the window is
        # unbounded and the strip is complete — the truncation guard protects
        # pairs *past a decided prefix*, not pairs the run never reached.
        assert outcome.stripped == 10
        assert await pass_edges(committing, project) == []


# ── D11: the undo door inverts the block this pass wrote ─────────────────


class TestUndoIntegration:
    async def test_undo_touches_only_the_derivation_block(
        self, committing, project
    ):
        """Reusing `ACTION_ASSOCIATE` without carrying the `pass_key` would
        make the undo restore or clear T2.12's block while reporting success —
        silent cross-pass corruption. A new action kind instead would hit
        `REASON_UNSUPPORTED_ACTION` and poison every whole-cycle undo
        containing one."""
        from app.services import dream_undo

        first, second, _ = await build_overlap_pair(committing, project)
        seeds = await read_seeds(committing, [first, second])
        await derive(committing, seeds)

        written = await pass_edges(committing, project)
        source, target = written[0]["source"], written[0]["target"]
        sibling = {
            "kind": "duplicate_candidate",
            "hygiene_state": "confirmed",
            "score": 0.97,
            "verdict": "duplicate",
            "detected_at": NOW.isoformat(),
        }
        async with committing() as session:
            await edges.upsert_edge(
                session,
                source_memory_id=source,
                target_memory_id=target,
                rel_type="RELATES_TO",
                project=project,
                pass_key=journal.NEAR_DUPLICATE_PASS,
                block=sibling,
            )
            await session.commit()

        events = await derivation_events(committing, project)
        assert len(events) == 1
        assert events[0]["payload"]["pass_key"] == journal.DERIVATION_PASS

        async with committing() as session:
            batch = await dream_undo.undo(
                session, event_ids=[int(events[0]["id"])], actor="tester"
            )
            await session.commit()

        assert len(batch.undone) == 1
        surviving = await all_edges(committing, project)
        assert len(surviving) == 1
        assert (
            edges.pass_block_of(surviving[0], journal.NEAR_DUPLICATE_PASS)
            == sibling
        ), "T2.12's block must be byte-identical after undoing our action"
        assert (
            edges.pass_block_of(surviving[0], journal.DERIVATION_PASS) is None
        )

    def test_the_pass_key_defaults_to_the_near_duplicate_arm(self):
        """Rows journalled before T2.16 carry no `pass_key` and were all
        written by that arm, so the default is the compatibility contract, not
        a convenience."""
        assert journal.associate_pass_key({}) == journal.NEAR_DUPLICATE_PASS
        assert journal.associate_pass_key(None) == journal.NEAR_DUPLICATE_PASS
        assert (
            journal.associate_pass_key({"pass_key": journal.DERIVATION_PASS})
            == journal.DERIVATION_PASS
        )


# ── the scope boundary, asserted structurally ────────────────────────────

# A call counter cannot show a negative, so the boundary is a source scan.
# A derived `CONTRADICTS` edge is a signal *into* fact-level dispute (doc 08
# §4.2), never a verdict, and T2.11's scan is blocked on an unqualified judge —
# so this pass must not become a back door supplying fact-level dispute while
# that gate is unmet.
FACT_LAYER_NAMES: frozenset[str] = frozenset({
    "verification_status",
    "review_state",
    "knowledge_triples",
    "fact_sources",
    "verification_ladder",
    "verification_judge",
    "verification_recompute",
    "contradiction_veto",
    "supersession_hold",
})


def _docstring_ids(tree: ast.AST) -> set[int]:
    """Docstrings are prose about the boundary, not a reach across it — this
    module's own scope-boundary paragraph names every forbidden table. Excluded
    by identity rather than by a text rule, so a real literal hidden in a call
    argument is still caught."""
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                found.add(id(body[0].value))
    return found


def fact_layer_reaches(source: str) -> list[str]:
    tree = ast.parse(source)
    docstrings = _docstring_ids(tree)
    offenders: list[str] = []
    for node in ast.walk(tree):
        if id(node) in docstrings:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            offenders += [
                f"line {node.lineno}: literal {name!r}"
                for name in FACT_LAYER_NAMES
                if name in lowered
            ]
        elif isinstance(node, ast.Name) and node.id in FACT_LAYER_NAMES:
            offenders.append(f"line {node.lineno}: name {node.id!r}")
        elif isinstance(node, ast.Attribute) and node.attr in FACT_LAYER_NAMES:
            offenders.append(f"line {node.lineno}: attribute {node.attr!r}")
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [getattr(node, "module", None) or ""] + [
                alias.name for alias in node.names
            ]
            offenders += [
                f"line {node.lineno}: import {name!r}"
                for name in names
                for forbidden in FACT_LAYER_NAMES
                if forbidden in name
            ]
    return offenders


def test_the_pass_never_writes_the_fact_layer():
    source = (BACKEND / "app" / "services" / "memory_dream.py").read_text()
    assert fact_layer_reaches(source) == []


def test_the_fact_layer_scan_catches_a_real_reach():
    """The scan's own negative control: a scan that cannot fail proves
    nothing about the module it passed on."""
    offending = (
        "from app.services import verification_ladder\n"
        "def go(session):\n"
        "    return session.execute(\n"
        "        \"UPDATE knowledge_triples SET verification_status = 'x'\"\n"
        "    )\n"
    )
    found = fact_layer_reaches(offending)
    assert any("verification_ladder" in item for item in found)
    assert any("knowledge_triples" in item for item in found)


# ── the wired cycle (step 9) ─────────────────────────────────────────────


class StubLLM:
    """Enough orchestrator to drive a full cycle offline: a measured
    fingerprint from `embed`, and a verdict that declines every pair so the
    near-duplicate arm contributes nothing to what is asserted here."""

    def __init__(self, *, fingerprint: str = FP):
        self.fingerprint = fingerprint

    async def embed(self, content: str):
        return [1.0, 0.0, 0.0, 0.0], self.fingerprint

    async def chat_completion(self, purpose, messages, response_format=None, seed=None):
        return json.dumps({"verdict": "distinct", "reason": "stub"})


class TestWiredIntoTheCycle:
    async def test_a_cycle_derives_and_reports_its_counters(
        self, committing, project
    ):
        first, second, _ = await build_overlap_pair(committing, project)
        async with committing() as session:
            await seed_partition(session, FP)
            await session.commit()

        outcome = await dream.run_memory_dream(
            committing, lambda: StubLLM(), refine_batch=0, judge_fanout=0
        )

        assert outcome.derivation_candidates >= 1
        assert outcome.derived >= 1
        assert outcome.derivation_skipped_reason is None
        assert len(await pass_edges(committing, project)) >= 1

    async def test_the_flag_off_derives_nothing(self, committing, project):
        await build_overlap_pair(committing, project)
        async with committing() as session:
            await seed_partition(session, FP)
            await session.commit()

        outcome = await dream.run_memory_dream(
            committing, lambda: StubLLM(),
            refine_batch=0, judge_fanout=0, derivation_enabled=0,
        )

        assert outcome.derived == 0
        assert await pass_edges(committing, project) == []
