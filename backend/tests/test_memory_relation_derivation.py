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
