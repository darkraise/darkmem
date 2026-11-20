"""Vectors for repo-minted entities, so the code bridge anchors (doc 10 §6, T2.97).

Doc 10 §6 sells the bridge on anchoring: a ``postgres`` entity minted from a
repository's imports is meant to be the *same* deduped node as ``postgres``
from a memory. As T2.27 shipped it, that held only for an exact
``(name, entity_type)`` match, because a repo-minted entity carries no row in
``entity_embeddings__<slug>`` and Phase 4's ``find_similar_entity`` probe reads
nothing else. ``postgres`` from code and ``postgresql`` from a memory stayed two
nodes where the memory path merges them at cosine 0.85.

**The deriver stays LLM-free; this module is where the model call lives.**
T2.27's clause forbids an LLM *extraction* call, and an embed is not one — but
the guard that enforces it (``tests/test_code_deriver.py``) forbids the whole
orchestrator surface, ``embed_batch_chunked`` included, and that breadth is
right: an extraction is reached through the same handle. So the embed happens
here, in a Tier-C job outside the deriver's import closure, and the guard is
left exactly as strict as it was. If this module ever appears in that closure
the guard fails the build, which is the property that keeps the two apart.

**Scope: entities a repository asserts, and only those.** Every other row in
``entities`` already has a writer — Phase 5 embeds what extraction mints, and
``ReembedService`` is the operator's whole-corpus repair path for what that
missed. Repo-minted rows had no writer at all. Widening this job to every
entity missing a vector would quietly turn an operator-initiated, progress-
broadcast, whole-corpus re-embed into a background drain that spends model
calls on its own schedule.

**What this closes and what it does not.** A repo indexed before a memory
arrives anchors: the vector is in the partition by the time Phase 4 probes. A
repo indexed *after* the memory already minted the near-named node does not —
Phase 4 dedups at write time and nothing re-runs it, so the two rows coexist
and only a retroactive merge pass can join them. That pass is a different
mechanism (it must move ``memory_ids``/``repo_ids``, re-point relation
endpoints and recompute the ``technologies`` denorm) and it is not this job:
it is :mod:`app.services.entity_merge` (T2.101), which spends the vectors this
job writes and would have nothing to compare without them.

**One fingerprint, resolved by data, and the write follows the embedder.**
Candidates are selected under the fingerprint
:func:`~app.repositories.vector.PostgresVectorRepository.resolve_read_fingerprint`
confirms holds data, never ``llm_fingerprint()`` — a phantom key would make
every repo entity look unembedded, re-embed them into a table nothing reads,
and report a healthy count every run (T2.68, T2.83). The write then goes to the
partition of the fingerprint the embedder *returned*, so an embedder that
rotated between the selection query and the write lands its vectors in the new
partition rather than mixing embedding spaces inside the old one — the same
re-resolve Phase 3 performs when the fingerprint moves under it mid-batch.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table, ensure_registered
from app.services.job_registry import FieldDescriptor

logger = logging.getLogger(__name__)

PARENT_TABLE = "entity_embeddings"
CACHE_PARENT_TABLE = "entity_embedding_cache"

REPO_ENTITY_ANCHORING_JOB_KEY = "repo_entity_anchoring"

DEFAULT_EMBED_CHUNK = 20
DEFAULT_EMBED_CONCURRENCY = 1
DEFAULT_MISSING_BATCH = 200

REPO_ENTITY_ANCHORING_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="missing_batch", label="Repo Entities Per Run",
        default=DEFAULT_MISSING_BATCH, min=0, max=5_000,
        help=(
            "Repository-asserted entities with no vector under the active "
            "embedder that are embedded per run. The arm is exact: it drains "
            "to zero and stays there until a repo is indexed or the embedder "
            "rotates. 0 disables the job, which leaves code-minted entities "
            "deduping only on an exact name match."
        ),
    ),
    FieldDescriptor(
        key="embed_chunk", label="Embed Chunk Size",
        default=DEFAULT_EMBED_CHUNK, min=1, max=200,
        help="Texts per embedder call.",
    ),
]


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


@dataclass
class AnchorOutcome:
    written: int = 0
    fingerprint: str | None = None


def _missing_sql(table: str) -> str:
    # `cardinality(...) > 0` is the repo-asserted scope and it is deliberately
    # not index-driven: the GIN index on `repo_ids` answers containment, not
    # emptiness. The batch is bounded and `entities` is small beside it.
    return f"""
        SELECT CAST(e.id AS text) AS entity_id, e.name
        FROM entities e
        LEFT JOIN {table} ee
               ON ee.entity_id = e.id
              AND ee.fingerprint = CAST(:fp AS text)
        WHERE ee.entity_id IS NULL
          AND COALESCE(cardinality(e.repo_ids), 0) > 0
        ORDER BY e.created_at, e.id
        LIMIT CAST(:limit AS int)
    """


async def resolve_read_fingerprint(session: AsyncSession, llm) -> str:
    """The fingerprint a partition read may safely key on. Delegated, never
    re-derived — see the module docstring on the phantom-fingerprint trap."""
    from app.repositories.vector import PostgresVectorRepository  # noqa: PLC0415

    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


async def repo_entities_missing_vectors(
    session: AsyncSession, fingerprint: str, limit: int,
) -> list[dict]:
    """Repository-asserted entities with no vector under this fingerprint.

    Keyed on one fingerprint on both sides (invariant 2): an entity embedded
    under a previous embedder is missing under the current one and must be
    re-embedded rather than counted as covered.
    """
    if limit <= 0:
        return []
    table = child_table(PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(_missing_sql(table)), {"fp": fingerprint, "limit": limit},
    )
    return [{"entity_id": row[0], "name": row[1]} for row in rows.all()]


async def embed_repo_entities(
    session: AsyncSession,
    llm,
    *,
    entities: Sequence[dict],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed each entity's name into the active partition and the name cache.

    ``None`` means nothing was embedded — an empty request — and therefore that
    no fingerprint was measured. It is not a failure.

    The embedded text is the entity's stored name, which is lowercase on disk,
    because that is exactly what Phase 3 embeds. Anchoring compares a repo-minted
    vector with a memory-minted one at a fixed 0.85 threshold, so the two must be
    produced from the same string under the same embedder or the comparison is
    against a different geometry than the one the threshold was calibrated on.

    The name cache is written alongside the partition for the same reason: Phase
    3 reads it by ``name_lower`` before spending an embed, so a memory that later
    names this entity gets back the identical vector rather than a fresh one.

    **This may commit the caller's transaction**: first contact with an unknown
    fingerprint runs the child-table DDL through ``embedder_registry.register``,
    which commits on this session.
    """
    rows = list(entities)
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["name"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"entity_anchoring: the embedder returned {len(vectors)} vectors "
            f"for {len(rows)} entities; refusing to write vectors under ids "
            "they may not belong to"
        )

    await ensure_registered(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    cache = child_table(CACHE_PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (entity_id, fingerprint, embedding)
                VALUES (CAST(:eid AS uuid), CAST(:fp AS text),
                        CAST(:embedding AS vector))
                ON CONFLICT (entity_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {
                "eid": row["entity_id"],
                "fp": fingerprint,
                "embedding": str(list(vector)),
            },
        )
        await session.execute(
            text(f"""
                INSERT INTO {cache} (name_lower, fingerprint, embedding)
                VALUES (:name, CAST(:fp AS text), CAST(:embedding AS vector))
                ON CONFLICT (name_lower, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding,
                        last_used_at = NOW()
            """),
            {
                "name": row["name"],
                "fp": fingerprint,
                "embedding": str(list(vector)),
            },
        )

    return WriteResult(fingerprint=fingerprint, written=len(rows))


async def refresh_repo_entity_anchors(
    session: AsyncSession,
    llm,
    *,
    missing_batch: int = DEFAULT_MISSING_BATCH,
    chunk_size: int = DEFAULT_EMBED_CHUNK,
) -> AnchorOutcome:
    """One tick of the anchoring arm.

    One arm, not two. ``relation_embeddings`` carries a rotation backstop
    because a relation's embedded text is derived from names that can change
    under it, leaving a stale vector nothing on disk can detect. An entity's
    embedded text *is* its primary key half: a renamed entity is a different
    row, and one whose vector went stale for any other reason is what the
    operator re-embed exists for. A rotation arm here would re-spend model
    calls on rows that cannot have drifted.

    An install where nothing has been embedded yet has no fingerprint to key
    on, and this returns an empty outcome rather than inventing one.
    """
    from app.repositories.vector import (  # noqa: PLC0415
        EmbedderFingerprintUnresolved,
    )

    outcome = AnchorOutcome()
    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info(
            "repo_entity_anchoring: no fingerprint holds data yet; nothing to anchor"
        )
        return outcome
    await ensure_registered(session, fingerprint)
    outcome.fingerprint = fingerprint

    missing = await repo_entities_missing_vectors(session, fingerprint, missing_batch)
    if not missing:
        return outcome

    written = await embed_repo_entities(
        session, llm, entities=missing, chunk_size=chunk_size,
    )
    if written is not None:
        outcome.written = written.written
        outcome.fingerprint = written.fingerprint
    return outcome
