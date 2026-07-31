"""The emit side of the enqueue-for-verification hook (doc 05 §8.4, doc 08 §3.3).

Tier B never reconciles the vault. When a memory's Layer-1 contributions
change, this module withdraws the ``fact_sources`` rows that memory no longer
supports, expires inline any live triple thereby left with **no** surviving
source, and emits one ``sources_changed`` event per affected fact. The Tier-C
verification recompute drains those events. Nothing here recomputes a
verification status and nothing here reaches a consolidation job (invariant 15);
the inline expiry is the single deterministic belief-lifecycle action doc 08
§3.3 permits at this tier, precisely because it involves no model and no
judgment -- a fact whose last source was just withdrawn has to stop being served
now rather than lingering as ``corroborated`` until the next Tier-C tick.

**What "identical" is compared over, and why nothing finer would mean anything.**
The provenance no-op guard compares the set of ``(fact_id, source_kind,
source_ref)`` dedupe keys this memory contributes -- with the kind and ref
pinned to ``('memory', <memory id>)`` for one sweep, that is exactly the set of
facts it sources. No finer comparison is observable. ``add_source`` is
first-assertion-wins and rewrites neither ``origin_key`` nor ``detail`` on
re-assertion, so re-asserting an existing key changes no column of any row; and
this module only ever *removes* rows, because minting provenance belongs to
fact lifting, which owns its own emitter. The only difference a re-extraction
can produce is therefore a withdrawal, and "withdrew nothing" is "changed
nothing". Without that guard every reprocess of every memory would read as
evidence churn and the recompute would thrash ``corroborated <-> candidate`` on
facts whose evidence never moved.

**Retention is decided by fact identity, not by row bookkeeping.** A memory
still sources a fact when its post-rewrite graph still asserts that fact's
triple, tested through ``compute_triple_key`` -- the same identity function that
minted the fact. The asserted set is read back from ``entity_relations`` after
Phase 5's strip-and-write rather than from the extraction payload, so what is
compared is what landed on disk.

**Withdrawal is not scoped by project, deliberately.** ``facts_for_source``
requires a project because ``source_ref`` is a soft reference and one human
reviewer or one shared repository is the same ref across several scopes. A
memory id is not: it is globally unique and names exactly one row, so every
``('memory', id)`` provenance row belongs to this memory whatever project the
fact carries. Scoping the sweep to the memory's *current* project would silently
strand provenance behind a memory that had since been moved between projects.
Each event's ``project`` column is taken from the fact it concerns.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import record_event
from app.services.triple_key import compute_triple_key

logger = logging.getLogger(__name__)

# The `fact_sources.source_kind` a memory asserts under, and the spelling of the
# `source_ref` that goes with it. Both sides of the provenance contract read
# these rather than re-deriving the convention: a producer writing a differently
# spelled ref would be invisible to this sweep, so its rows would never be
# withdrawn and its facts would never expire.
MEMORY_SOURCE_KIND = "memory"


def memory_source_ref(memory_id: UUID | str) -> str:
    """The canonical spelling of a memory's ``source_ref``.

    Normalised through ``UUID`` rather than stringified as given: a padded or
    upper-cased id would write a ref this module's sweep can never match, so
    the rows would never be withdrawn and their facts never expire — an
    invisible failure with no error and no symptom. Producers and the sweep
    have to agree on one spelling, so the one spelling is minted here.
    """
    return str(UUID(str(memory_id)))


_MEMORY_PROVENANCE = text("""
    SELECT fs.id AS source_id, fs.fact_id, kt.triple_key, kt.project,
           kt.expired_at
    FROM fact_sources fs
    JOIN knowledge_triples kt ON kt.id = fs.fact_id
    WHERE fs.source_kind = CAST(:kind AS text)
      AND fs.source_ref = CAST(:ref AS text)
    ORDER BY fs.fact_id
""")

_ASSERTED_TRIPLES = text("""
    SELECT se.name AS subject_name, r.rel_type, oe.name AS object_name
    FROM entity_relations r
    JOIN entities se ON se.id = r.source_entity_id
    JOIN entities oe ON oe.id = r.target_entity_id
    WHERE CAST(:mid AS uuid) = ANY(r.memory_ids)
""")

_WITHDRAW = text("DELETE FROM fact_sources WHERE id = ANY(CAST(:ids AS uuid[]))")

_STILL_SOURCED = text("""
    SELECT DISTINCT fact_id
    FROM fact_sources
    WHERE fact_id = ANY(CAST(:ids AS uuid[]))
""")


async def _memory_provenance(session: AsyncSession, memory_id: UUID | str) -> list[dict]:
    result = await session.execute(
        _MEMORY_PROVENANCE,
        {"kind": MEMORY_SOURCE_KIND, "ref": memory_source_ref(memory_id)},
    )
    return [dict(row) for row in result.mappings().all()]


async def _asserted_triples(
    session: AsyncSession, memory_id: UUID | str
) -> list[tuple[str, str, str]]:
    result = await session.execute(_ASSERTED_TRIPLES, {"mid": str(memory_id)})
    return [
        (row["subject_name"], row["rel_type"], row["object_name"])
        for row in result.mappings().all()
    ]


async def _withdraw(
    session: AsyncSession, *, memory_id: UUID | str, rows: list[dict]
) -> list[str]:
    """Withdraw ``rows``, expire what they orphan, and enqueue the difference.

    The empty case returns before touching anything: no withdrawal is no
    provenance change, and an event emitted there would be indistinguishable to
    the drain from real evidence movement.
    """
    if not rows:
        return []

    await session.execute(
        _WITHDRAW, {"ids": [str(row["source_id"]) for row in rows]}
    )

    fact_ids = [str(row["fact_id"]) for row in rows]
    surviving = {
        str(fact_id)
        for fact_id in (
            await session.execute(_STILL_SOURCED, {"ids": fact_ids})
        ).scalars().all()
    }

    triples = KnowledgeTripleRepository(session)
    affected: list[str] = []
    for row in rows:
        # Normalised at the boundary: asyncpg hands these back as UUID, the
        # callers hold str, and a mismatch drops matches silently (invariant 9).
        fact_id = UUID(str(row["fact_id"]))
        if str(fact_id) not in surviving and row["expired_at"] is None:
            await triples.expire(fact_id)
        await record_event(
            session,
            event_type="sources_changed",
            object_type="fact",
            object_id=fact_id,
            project=row["project"],
            payload={"fact_id": str(fact_id), "memory_id": str(memory_id)},
        )
        affected.append(str(fact_id))
    return affected


async def reconcile_memory_sources(
    session: AsyncSession, *, memory_id: UUID | str
) -> list[str]:
    """Phase 5's hook: reconcile one memory's provenance against its new graph.

    Returns the affected fact ids -- empty when the rewrite was a provenance
    no-op, which is the common case and, on a first ingest, the only one: a
    brand-new memory has no ``fact_sources`` rows at all because facts are
    lifted from corroborated Layer-1 relations by Tier-C consolidation, not by
    the pipeline. The provenance read comes first so that case costs one
    indexed lookup and stops.
    """
    rows = await _memory_provenance(session, memory_id)
    if not rows:
        return []

    asserted = await _asserted_triples(session, memory_id)
    keys_by_project: dict[str, set[str]] = {}

    def retained(project: str) -> set[str]:
        if project not in keys_by_project:
            keys_by_project[project] = {
                compute_triple_key(project, subject, rel_type, obj)
                for subject, rel_type, obj in asserted
            }
        return keys_by_project[project]

    withdrawn = [
        row for row in rows if row["triple_key"] not in retained(row["project"])
    ]
    return await _withdraw(session, memory_id=memory_id, rows=withdrawn)


async def withdraw_memory_sources(
    session: AsyncSession, *, memory_id: UUID | str
) -> list[str]:
    """The deletion sweep: a deleted memory sources nothing, so all of it goes."""
    rows = await _memory_provenance(session, memory_id)
    return await _withdraw(session, memory_id=memory_id, rows=rows)
