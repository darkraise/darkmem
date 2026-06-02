"""ANN entity dedup must not collapse across entity_type.

The Phase-4 dedup probe matched on name-embedding cosine only, with no
entity_type filter, and canonical_map was keyed by name alone. So a `concept`
named "react" could canonicalize onto a pre-existing `tool` named "react" (their
bare-name embeddings are near-identical), corrupting the (name, type) binding —
and through it the lowercase `technologies` denorm and relation-endpoint
resolution. find_similar_entity must accept and honour an entity_type filter.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table

FP = "entity-dedup|4"


async def _seed_entity_partition(session) -> str:
    await session.execute(
        text("INSERT INTO embedders (fingerprint, model_id, dims, source) "
             "VALUES (:fp, 'm', 4, 'llm') ON CONFLICT (fingerprint) DO NOTHING"),
        {"fp": FP},
    )
    child = child_table("entity_embeddings", FP)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " entity_id UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        " embedding vector(4) NOT NULL,"
        " PRIMARY KEY (entity_id, fingerprint))"
    ))
    return child


@pytest.mark.asyncio
async def test_find_similar_entity_does_not_collapse_across_types(session):
    repo = PostgresGraphRepository(session)
    child = await _seed_entity_partition(session)
    mem = uuid.uuid4()

    tool = await repo.create_entity(name="react", entity_type="tool", properties={}, memory_id=mem)
    concept = await repo.create_entity(name="react", entity_type="concept", properties={}, memory_id=mem)

    for eid, vec in ((tool["id"], "[1,0,0,0]"), (concept["id"], "[0.99,0.01,0,0]")):
        await session.execute(
            text(f"INSERT INTO {child} (entity_id, fingerprint, embedding) "
                 "VALUES (CAST(:e AS uuid), :fp, CAST(:v AS vector))"),
            {"e": eid, "fp": FP, "v": vec},
        )

    # A probe for a new 'concept' must match only same-typed candidates, never
    # the 'tool' row, even though the tool's name embedding is closer.
    match = await repo.find_similar_entity(
        [0.995, 0.005, 0, 0], fingerprint=FP, threshold=0.85, entity_type="concept",
    )
    assert match is not None
    assert match["entity_type"] == "concept"
    assert match["id"] == concept["id"]
