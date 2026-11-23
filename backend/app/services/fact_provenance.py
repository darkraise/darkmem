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

**Withdrawal is not scoped by project, deliberately.** ``source_ref`` is a
soft reference, and one human reviewer or one shared repository is the same
ref across several scopes, so a by-source read of those kinds needs a project.
A memory id is not: it is globally unique and names exactly one row, so every
``('memory', id)`` provenance row belongs to this memory whatever project the
fact carries. Scoping the sweep to the memory's *current* project would silently
strand provenance behind a memory that had since been moved between projects.
Each event's ``project`` column is taken from the fact it concerns.

**Three entries, one withdrawal.** ``reconcile_memory_sources`` (re-extraction),
``withdraw_memory_sources`` (every delete path) and
``reap_orphaned_memory_sources`` (the backstop) differ only in *which rows they
select*; all three hand those rows to ``_withdraw``, which owns the delete, the
surviving-source test, the inline expiry and the emit. A second copy of that
sequence would be a second chance to get the expiry or the payload spelling
wrong, and the two copies would drift apart silently -- provenance loss has no
error and no symptom.

**Why a backstop exists at all, and what it may not touch.** Routing every
delete path through ``withdraw_memory_sources`` closes the paths that *skip*
withdrawal; it cannot close the path that *attempts* it and fails, because
``ProcessingPipeline.delete_memory`` swallows its exceptions. Either way the end
state is identical and is the direction the truth core forbids: a fact whose
only source has vanished keeps serving as ``corroborated`` with ``expired_at``
NULL, and no ``sources_changed`` ever revisits it. So the backstop reaps
provenance whose memory is gone whatever removed it.

**The predicate is narrow on purpose, and its default is to do nothing.** This
is an anti-join, so *failing to match is reaping*: every way a row can fall
through the existence test ends in deletion. That inverts the usual reading of a
filter, and both guards below exist because of it.

*The kind filter.* ``source_ref`` carries no type discriminator -- the kind
lives in ``source_kind`` -- so "no ``memories`` row matches this ref" is
evidence of orphanhood only for ``source_kind = 'memory'``. A ``human``
reviewer's ref or a ``code`` repository id is not a memory id and matches no
``memories`` row *by construction*, so an unfiltered anti-join would reap every
one of them and expire the facts they solely source.

*The canonical-spelling filter.* Among memory-kind rows, only a ref spelled the
way ``memory_source_ref`` mints one may be reaped (``_CANONICAL_REF``). Without
it the anti-join reaps a ref that names a **live** memory under a different
spelling -- ``{...}`` braced, or upper-cased -- because that spelling matches no
``CAST(memories.id AS text)`` either. That is destruction of live provenance,
where the pre-existing contract (see ``memory_source_ref``) promised the exact
opposite: that a mis-spelled ref is merely invisible to the withdrawal sweep.
**The ruling is that the conservative reading wins.** A ref this module cannot
interpret is left alone, exactly as it was before the backstop existed, because
"never withdrawn" is a stranding that a later fix can still repair while
"reaped" is irrecoverable -- and the truth core's direction of error is to
under-claim. The cost is that a genuinely orphaned row carrying a non-canonical
ref is never reaped; that is the pre-backstop status quo for that row, and it is
the behaviour ``memory_source_ref``'s docstring already documents.

*The cast direction.* The existence test compares ``CAST(memories.id AS text)``
against the stored ref rather than casting the ref to ``uuid``: the ref column
holds every kind's spelling, ``AND`` is not evaluation order in SQL, and a
planner free to hoist ``CAST(source_ref AS uuid)`` above the kind filter would
abort the sweep on the first non-uuid ref. ``CAST(uuid AS text)`` renders the
lowercase hyphenated form ``memory_source_ref`` mints, so a canonically spelled
ref always matches its live memory.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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

# The shape `memory_source_ref` mints: lowercase hex, hyphenated 8-4-4-4-12.
# The backstop reaps only refs matching this, so it is the spelling contract in
# executable form rather than in prose. `test_the_minted_ref_matches_the_shape
# _the_backstop_trusts` pins the two together; if they drift, the backstop
# either stops reaping real orphans or starts reaping live provenance.
_CANONICAL_REF = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"


def memory_source_ref(memory_id: UUID | str) -> str:
    """The canonical spelling of a memory's ``source_ref``.

    Normalised through ``UUID`` rather than stringified as given: a padded or
    upper-cased id would write a ref this module's sweep can never match, so
    the rows would never be withdrawn and their facts never expire — an
    invisible failure with no error and no symptom. Producers and the sweep
    have to agree on one spelling, so the one spelling is minted here.

    That "invisible" is load-bearing and is enforced rather than hoped for.
    ``reap_orphaned_memory_sources`` is an anti-join, where a ref that matches
    nothing is *deleted*, so a mis-spelled ref would be destroyed rather than
    ignored — the opposite of what the paragraph above promises. The backstop
    therefore reaps only refs matching ``_CANONICAL_REF``, which is exactly
    what this function emits. A producer that bypasses this function still
    fails invisibly; it does not lose the row.
    """
    return str(UUID(str(memory_id)))


_MEMORY_PROVENANCE = text("""
    SELECT fs.id AS source_id, fs.fact_id, fs.source_ref AS memory_ref,
           kt.triple_key, kt.project, kt.expired_at
    FROM fact_sources fs
    JOIN knowledge_triples kt ON kt.id = fs.fact_id
    WHERE fs.source_kind = CAST(:kind AS text)
      AND fs.source_ref = CAST(:ref AS text)
    ORDER BY fs.fact_id
""")

_ORPHANED_PROVENANCE = text("""
    SELECT fs.id AS source_id, fs.fact_id, fs.source_ref AS memory_ref,
           kt.project, kt.expired_at
    FROM fact_sources fs
    JOIN knowledge_triples kt ON kt.id = fs.fact_id
    WHERE fs.source_kind = CAST(:kind AS text)
      AND fs.source_ref ~ CAST(:canonical AS text)
      AND NOT EXISTS (
          SELECT 1 FROM memories m WHERE CAST(m.id AS text) = fs.source_ref
      )
    ORDER BY fs.fact_id
""")

_ASSERTED_TRIPLES = text("""
    SELECT se.name AS subject_name, r.rel_type, oe.name AS object_name
    FROM entity_relations r
    JOIN entities se ON se.id = r.source_entity_id
    JOIN entities oe ON oe.id = r.target_entity_id
    WHERE r.memory_ids @> ARRAY[CAST(:mid AS uuid)]
""")

_WITHDRAW = text("DELETE FROM fact_sources WHERE id = ANY(CAST(:ids AS uuid[]))")

_STILL_SOURCED = text("""
    SELECT DISTINCT fact_id
    FROM fact_sources
    WHERE fact_id = ANY(CAST(:ids AS uuid[]))
""")


WITHDRAWAL_LOCK_TIMEOUT = "5s"
_CURRENT_LOCK_TIMEOUT = text("SELECT current_setting('lock_timeout')")
_SET_LOCK_TIMEOUT = text("SELECT set_config('lock_timeout', CAST(:value AS text), true)")


@asynccontextmanager
async def _bounded_lock_wait(session: AsyncSession) -> AsyncIterator[None]:
    """Bound the fact-lock wait, then put the caller's ``lock_timeout`` back.

    A Tier-C tick can hold these fact locks for a whole batch; waiting past the
    bound fails the caller's savepoint instead of stalling it behind the batch.
    A set_config that is local to the transaction outlives a released
    savepoint, so the previous value is restored once the block has run; a
    failure restores it by rolling back.
    """
    previous = (await session.execute(_CURRENT_LOCK_TIMEOUT)).scalar_one()
    await session.execute(_SET_LOCK_TIMEOUT, {"value": WITHDRAWAL_LOCK_TIMEOUT})
    yield
    await session.execute(_SET_LOCK_TIMEOUT, {"value": previous})


async def lock_facts_for_withdrawal(session: AsyncSession, fact_ids: list[str]) -> None:
    await session.execute(
        text("SELECT id FROM knowledge_triples WHERE id = ANY(CAST(:ids AS uuid[])) ORDER BY id FOR UPDATE"),
        {"ids": sorted(set(fact_ids))},
    )


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


async def _orphaned_provenance(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        _ORPHANED_PROVENANCE,
        {"kind": MEMORY_SOURCE_KIND, "canonical": _CANONICAL_REF},
    )
    return [dict(row) for row in result.mappings().all()]


async def _withdraw(session: AsyncSession, *, rows: list[dict]) -> list[str]:
    """Withdraw ``rows``, expire what they orphan, and enqueue the difference.

    The empty case returns before touching anything: no withdrawal is no
    provenance change, and an event emitted there would be indistinguishable to
    the drain from real evidence movement.

    Each row names its own memory through ``memory_ref``, read back from the
    ``fact_sources`` row rather than passed in alongside it: the backstop
    withdraws rows belonging to many memories at once, and reading the stored
    ref makes the emitted payload the spelling the producer actually wrote
    instead of one re-derived beside it.
    """
    if not rows:
        return []

    fact_ids = [str(row["fact_id"]) for row in rows]
    await lock_facts_for_withdrawal(session, fact_ids)
    await session.execute(
        _WITHDRAW, {"ids": [str(row["source_id"]) for row in rows]}
    )

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
        # The expired_at test is redundant, not load-bearing: `expire` COALESCEs
        # so a second call keeps the first timestamp, and it journals only a real
        # transition. Removing it changes no observable behaviour, which is why
        # no test pins it. It stays because skipping a known no-op is cheaper
        # than issuing it, and because it states the intent at the call site.
        if str(fact_id) not in surviving and row["expired_at"] is None:
            await triples.expire(fact_id)
        await record_event(
            session,
            event_type="sources_changed",
            object_type="fact",
            object_id=fact_id,
            project=row["project"],
            # The same spelling the producer wrote: the drain groups these
            # payloads, so two halves rendering one memory id two ways would
            # split one fact's evidence movement into two.
            payload={"fact_id": str(fact_id), "memory_id": row["memory_ref"]},
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
    if not withdrawn:
        return []
    # Past the bound, savepoint B fails and the buffer retries it.
    async with _bounded_lock_wait(session):
        return await _withdraw(session, rows=withdrawn)


async def withdraw_memory_sources(
    session: AsyncSession, *, memory_id: UUID | str
) -> list[str]:
    """The deletion sweep: a deleted memory sources nothing, so all of it goes."""
    rows = await _memory_provenance(session, memory_id)
    async with _bounded_lock_wait(session):
        return await _withdraw(session, rows=rows)


async def reap_orphaned_memory_sources(session: AsyncSession) -> list[str]:
    """The backstop: withdraw ``('memory', ref)`` rows whose memory is gone.

    Returns the affected fact ids. Unlike the two by-memory entries this one is
    driven by the data rather than by a caller who knows what it deleted, so it
    heals stranding whose cause it cannot see -- including the interactive
    delete path's swallowed withdrawal failure, where nothing bypassed the hook
    and there is therefore nothing to route.

    It is a backstop, not a substitute for routing: it runs on a cadence, and
    between a delete and the next tick a fact whose last source vanished still
    serves as ``corroborated``. Every delete path still withdraws inline.

    Reaping is the *default* outcome of the anti-join, so both filters on
    ``_ORPHANED_PROVENANCE`` are protecting rows from deletion rather than
    selecting rows for it: non-memory kinds, and memory-kind refs not spelled
    the way ``memory_source_ref`` mints them. See the module docstring.
    """
    return await _withdraw(session, rows=await _orphaned_provenance(session))
