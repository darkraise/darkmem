"""Layer-2 fact lifting — the first and only producer of the truth core.

Doc 08 §5.2. This derives *candidate* facts and their ``fact_sources`` from the
Layer-1 candidate graph and then stops: the lift **creates** the fact and its
provenance, the Tier-C recompute (T2.09) **counts and promotes**. Nothing here
reads the ladder, adjudicates a contradiction, or writes ``verification_status``
— the split is what keeps a producer from grading its own output.

**Identity is ``compute_triple_key``, and the project is part of it.** A
relation asserted by memories in two projects lifts to two facts, each sourced
only by its own project's memories, because ``triple_key`` embeds ``project``
verbatim. Merging them would merge their corroboration counts.

**Idempotence is identity plus first-assertion-wins, not bookkeeping.** A re-run
resolves the same ``triple_key`` to the same open row and finds every source
already present, so it writes nothing and — critically — emits nothing. The
no-op guard is the set difference below: the ``(source_kind, source_ref)`` keys
already stored on the fact against the keys this run would assert. That is the
same comparison basis ``fact_provenance`` uses on the withdrawal side, so the
two halves of the provenance contract can never disagree about what "changed"
means. Without it every tick would read as evidence churn and the recompute
would thrash ``corroborated <-> candidate`` on facts whose evidence never moved.

**The two temporal passes (§3.2) reduce to one reachable branch, and that is a
finding rather than an omission.** Stale-on-arrival closes an older open row
when a *newer belief* lands on the same ``triple_key``; the disjoint-window pass
leaves both live when their validity windows do not overlap. Layer 1 carries no
temporal qualifier — ``entity_relations`` has no validity window and no date
field — so two lifts of one triple are the same belief re-asserted, never a
newer one, and there is no window to be disjoint from. So every lifted row is
open-ended (``valid_at`` NULL, read as unbounded-past) and a re-lift reuses the
open row. The tempting alternative is to *derive* ``valid_at`` from a
``HAPPENED_ON`` object, and it is wrong: ``LEGACY_RELATION_TYPE_MAP`` folds
``VISITED`` and ``LIVES_IN`` into ``HAPPENED_ON``, so its object may be a place
("alice happened on paris"), and a date parse over it would either fail or
invent a belief window out of a location. Nothing here treats any relation as
date-valued.

**Born ``candidate``, and structurally so.** ``insert_open`` omits
``verification_status`` from its column list, so the row takes the schema
default; ``_BIRTH_STATUS`` below re-reads what actually landed, because a fact
born above ``candidate`` is exactly this layer's failure mode — silent
over-confidence, not a crash. Only doc 10's code deriver (T2.28) may open above
``candidate``, on the parse-is-verification rule, and ``confirmed`` is
human-only (T2.05).

**Every lifted fact traces to its sources by construction.** A candidate with no
asserting memory is dropped before the fact row is minted, and each candidate is
written inside its own savepoint, so a provenance failure rolls the fact back
with it. An unfalsifiable fact — one with no ``fact_sources`` row — is not
reachable from here.

**Provenance is re-read at write time, never trusted from the scan.** The scan
snapshots a whole batch; the writes follow one candidate at a time, and Tier B
does not stand still in between. A memory whose relations Phase 5 stripped, and
whose provenance the withdrawal sweep already reconciled away, is still in the
snapshot — writing it back would put a row on a **live** fact that nothing
withdraws again, so a memory asserting nothing would count as a distinct origin
in ``COUNT(DISTINCT origin_key)``. That is over-serving, and it is the one
direction of error this layer may not take. ``_STILL_ASSERTING`` re-reads the
assertion inside the savepoint, under the fact's own lock, so what is written
is what the graph says at write time.

**Grouping is on canonical names, because identity is.** ``entities.name`` is
stripped and lowered on write but not whitespace-collapsed, while
``compute_triple_key`` collapses; grouping on raw spellings therefore splits one
fact into two groups, and the damage is not cosmetic — see ``_canon``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.events import record_event
from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
from app.services.job_registry import FieldDescriptor
from app.services.triple_key import compute_triple_key

logger = logging.getLogger(__name__)

# Doc 08 §5.2's salience bar, "start with asserted by at least one memory, tune
# against candidate-fact volume". The batch bound keeps one tick's write set
# bounded; the scan below selects only groups with outstanding work, so
# successive ticks make progress instead of re-walking the same prefix.
DEFAULT_LIFT_BATCH = 50
MAX_LIFT_BATCH = 1000
DEFAULT_MIN_ASSERTING_MEMORIES = 1
MAX_MIN_ASSERTING_MEMORIES = 10

# The key and bounds are carried over from T2.08's placeholder schema
# deliberately: a value already persisted in the job's config row stays inside
# the same range and keeps a compatible meaning, so no stale-key strip is
# needed. Only the help text and the second field are new.
LIFT_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="batch_size", label="Batch Size",
        default=DEFAULT_LIFT_BATCH, min=1, max=MAX_LIFT_BATCH,
        help=(
            "Relation groups with outstanding lift work processed per run. "
            "Groups already lifted and fully sourced are not counted against it."
        ),
    ),
    FieldDescriptor(
        key="min_asserting_memories", label="Min Asserting Memories",
        default=DEFAULT_MIN_ASSERTING_MEMORIES, min=1, max=MAX_MIN_ASSERTING_MEMORIES,
        help=(
            "Salience bar (doc 08 §5.2): distinct memories that must assert a "
            "relation before it becomes a candidate fact."
        ),
    ),
]

_BIRTH_STATUS = "candidate"

def _canon(column: str) -> str:
    r"""Canonicalise a name in SQL the way ``compute_triple_key`` does.

    The scan has to group on **fact identity**, not on raw spellings, and the
    two differ on disk: Phase 5 writes ``entities.name`` as ``strip().lower()``
    (``pipeline.py``) while the identity function additionally collapses
    interior whitespace. Grouping on the raw name splits one fact into two
    groups, and the consequences are not cosmetic -- the losing spelling never
    matches the minted row, so it is reported as outstanding work on every tick
    forever, occupying a batch slot; and the salience bar counts per raw group,
    so two memories asserting one fact under two spellings never clear a
    threshold of two.

    ``\s`` is the database's whitespace class, which is narrower than Python's
    ``str.split()`` for exotic separators. That residue can only merge fewer
    names than the identity function does, and the merge in
    ``_pending_candidates`` still catches it before any write; what it cannot
    do is keep the group out of the next scan, so ``_lift_one`` reports such a
    candidate as stalled rather than letting it sit silently.
    """
    return rf"lower(btrim(regexp_replace({column}, '\s+', ' ', 'g')))"


# One row per relation group that still has lift work outstanding, with its
# asserting memories folded in. Grouped and matched on canonical names, so a
# group corresponds to a fact rather than to a spelling.
#
# The `open_fact` lateral is a *batch filter*, matched on the denormalised
# names rather than on `triple_key`, because uuid5 has no SQL spelling; identity
# is resolved authoritatively by `_open_fact_id` below.
#
# **Cost, stated accurately.** Canonicalising `knowledge_triples`' side of the
# match leaves no indexable predicate on it, and the lateral is correlated --
# it runs for every grouped row, before the WHERE and the LIMIT -- so a tick is
# O(groups x facts), not one scan. That is the right trade here and only here:
# a wrong pending predicate starves the batch permanently, while at homelab
# volume this is a background pass with a 300s ceiling. It does not scale to
# G-C volume; the fix at that point is an index on the canonical expression,
# which is a schema change and therefore a Tier-2 amendment, not something to
# reach for silently.
_PENDING_GROUPS = text(f"""
    WITH asserted AS (
        SELECT
            m.project             AS project,
            {_canon("se.name")}   AS subject_name,
            r.rel_type            AS rel_type,
            {_canon("oe.name")}   AS object_name,
            m.id                  AS memory_id,
            m.origin_key          AS origin_key,
            m.created_at          AS memory_created_at,
            se.id                 AS subject_id,
            oe.id                 AS object_id
        FROM entity_relations r
        JOIN entities se ON se.id = r.source_entity_id
        JOIN entities oe ON oe.id = r.target_entity_id
        JOIN memories m ON m.id = ANY(r.memory_ids)
    ),
    grouped AS (
        SELECT
            project, subject_name, rel_type, object_name,
            MIN(memory_created_at)     AS reference_time,
            MIN(CAST(subject_id AS text)) AS subject_id,
            MIN(CAST(object_id AS text))  AS object_id,
            COUNT(DISTINCT memory_id)  AS asserting_memories,
            jsonb_agg(DISTINCT jsonb_build_object(
                'memory_id', memory_id, 'origin_key', origin_key
            )) AS sources
        FROM asserted
        GROUP BY project, subject_name, rel_type, object_name
    )
    SELECT g.project, g.subject_name, g.rel_type, g.object_name,
           g.reference_time, g.subject_id, g.object_id, g.sources
    FROM grouped g
    LEFT JOIN LATERAL (
        SELECT kt.id
        FROM knowledge_triples kt
        WHERE kt.project = g.project
          AND {_canon("kt.subject_name")} = g.subject_name
          AND kt.rel_type = g.rel_type
          AND {_canon("kt.object_name")} = g.object_name
          AND kt.expired_at IS NULL
          AND kt.invalid_at IS NULL
        ORDER BY kt.created_at, kt.id
        LIMIT 1
    ) open_fact ON TRUE
    WHERE g.asserting_memories >= CAST(:min_memories AS integer)
      AND (
          open_fact.id IS NULL
          OR EXISTS (
              SELECT 1
              FROM jsonb_array_elements(g.sources) AS s
              WHERE NOT EXISTS (
                  SELECT 1 FROM fact_sources fs
                  WHERE fs.fact_id = open_fact.id
                    AND fs.source_kind = CAST(:kind AS text)
                    AND fs.source_ref = (s ->> 'memory_id')
              )
          )
      )
    ORDER BY g.project, g.subject_name, g.rel_type, g.object_name
    LIMIT CAST(:batch AS integer)
""")

# Re-read of the assertion the scan snapshotted, run at write time.
#
# The scan and the write are separated by every candidate before this one, and
# Tier B does not stand still across that gap: Phase 5 can strip a memory's
# relations and reconcile away its provenance in between. Writing from the
# snapshot alone would then re-add provenance for a memory that asserts
# nothing, and the row would land on a *live* fact where nothing withdraws it
# again -- a phantom origin inflating COUNT(DISTINCT origin_key), which is
# over-serving, the one direction this layer may not err in.
#
# **Every triple these memories assert, filtered by identity in Python.** The
# obvious shape -- pushing the candidate's endpoint names into the WHERE clause
# -- reintroduces the very defect `_canon` exists to fix, one level down: it
# matches only the spelling this candidate happens to carry, which is *narrower*
# than the retention predicate `reconcile_memory_sources` applies. A memory
# asserting the same fact under a spelling the database canonicaliser keeps
# apart would then be dropped by the lift while the sweep would have kept it --
# silently losing a legitimate witness, and losing it permanently. Matching on
# `compute_triple_key` instead is *exact* parity with the withdrawal half rather
# than approximate parity through SQL, which is the only claim worth making:
# the two halves must agree about what "this memory sources this fact" means.
_STILL_ASSERTING = text("""
    SELECT CAST(m.id AS text) AS memory_id,
           se.name AS subject_name,
           r.rel_type AS rel_type,
           oe.name AS object_name
    FROM entity_relations r
    JOIN entities se ON se.id = r.source_entity_id
    JOIN entities oe ON oe.id = r.target_entity_id
    JOIN memories m ON m.id = ANY(r.memory_ids)
    WHERE m.id = ANY(CAST(:memory_ids AS uuid[]))
""")

# FOR UPDATE, not a bare read: the Tier-B withdrawal sweep expires a fact under
# the same lock, so holding it from this read through the provenance write is
# what stops a source landing on a row that is being expired out from under it.
_OPEN_FACT = text("""
    SELECT id
    FROM knowledge_triples
    WHERE triple_key = CAST(:key AS text)
      AND expired_at IS NULL
      AND invalid_at IS NULL
    ORDER BY created_at, id
    LIMIT 1
    FOR UPDATE
""")

_EXISTING_REFS = text("""
    SELECT source_ref
    FROM fact_sources
    WHERE fact_id = CAST(:fact_id AS uuid)
      AND source_kind = CAST(:kind AS text)
""")


@dataclass
class _Candidate:
    """One prospective fact, keyed by the identity function itself."""

    triple_key: str
    project: str
    subject_name: str
    rel_type: str
    object_name: str
    subject_id: str | None
    object_id: str | None
    reference_time: datetime
    # source_ref -> origin_key. Keyed by ref so a memory asserting a triple
    # through two relation rows (two entity types sharing a name) is one source.
    origins: dict[str, str | None] = field(default_factory=dict)


@dataclass(frozen=True)
class _LiftedOne:
    """One candidate's outcome. ``stalled`` is the phantom-pending signature."""

    minted: bool = False
    sources_added: int = 0
    stalled: bool = False


@dataclass(frozen=True)
class LiftOutcome:
    """What one tick did, for the job log and for tests that want a summary."""

    candidates: int = 0
    facts_created: int = 0
    sources_added: int = 0
    events_emitted: int = 0


def fact_sentence(subject_name: str, rel_type: str, object_name: str) -> str:
    """The embeddable ``fact`` text, and the only place its shape is decided.

    Rendered as a readable clause because it is what the contradiction scan
    runs ``pg_trgm`` over (doc 08 §5.3) and what a Layer-3 article quotes; a
    raw tuple dump would trigram-match on the punctuation every fact shares.
    """
    predicate = rel_type.lower().replace("_", " ")
    return f"{subject_name} {predicate} {object_name}"


async def _pending_candidates(
    session: AsyncSession, *, batch_size: int, min_asserting_memories: int
) -> list[_Candidate]:
    result = await session.execute(
        _PENDING_GROUPS,
        {
            "batch": batch_size,
            "min_memories": min_asserting_memories,
            "kind": MEMORY_SOURCE_KIND,
        },
    )
    by_key: dict[str, _Candidate] = {}
    for row in result.mappings().all():
        key = compute_triple_key(
            row["project"], row["subject_name"], row["rel_type"], row["object_name"]
        )
        # Two name spellings the canonicaliser folds together are one fact.
        # Merging them here is what keeps the run from attempting two open rows
        # on one triple_key, which ux_knowledge_triples_open would refuse.
        candidate = by_key.get(key)
        if candidate is None:
            candidate = _Candidate(
                triple_key=key,
                project=row["project"],
                subject_name=row["subject_name"],
                rel_type=row["rel_type"],
                object_name=row["object_name"],
                subject_id=row["subject_id"],
                object_id=row["object_id"],
                reference_time=row["reference_time"],
            )
            by_key[key] = candidate
        elif row["reference_time"] < candidate.reference_time:
            candidate.reference_time = row["reference_time"]
        for entry in row["sources"] or ():
            memory_id = entry.get("memory_id")
            if not memory_id:
                continue
            ref = memory_source_ref(memory_id)
            candidate.origins.setdefault(ref, entry.get("origin_key"))
    return list(by_key.values())


async def _open_fact_id(session: AsyncSession, triple_key: str) -> str | None:
    result = await session.execute(_OPEN_FACT, {"key": triple_key})
    row = result.scalar_one_or_none()
    return str(row) if row is not None else None


async def _mint_fact(session: AsyncSession, candidate: _Candidate) -> str:
    # `confidence` is deliberately not passed: doc 08 §4.1 binds it to an
    # aggregated support estimate recomputed alongside the status, so a value
    # written at birth would be exactly the single-source guess that forbids.
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=candidate.triple_key,
        subject_name=candidate.subject_name,
        object_name=candidate.object_name,
        rel_type=candidate.rel_type,
        fact=fact_sentence(
            candidate.subject_name, candidate.rel_type, candidate.object_name
        ),
        reference_time=candidate.reference_time,
        project=candidate.project,
        subject_id=candidate.subject_id,
        object_id=candidate.object_id,
    )
    if row["verification_status"] != _BIRTH_STATUS:
        raise RuntimeError(
            f"lifted fact {row['id']} was born {row['verification_status']!r}, "
            f"not {_BIRTH_STATUS!r}: only the code deriver's parse-is-verification "
            f"rule may open a fact above candidate, and confirmed is human-only"
        )
    return row["id"]


async def _existing_refs(session: AsyncSession, fact_id: str) -> set[str]:
    result = await session.execute(
        _EXISTING_REFS, {"fact_id": fact_id, "kind": MEMORY_SOURCE_KIND}
    )
    return {str(ref) for ref in result.scalars().all()}


async def _still_asserting(session: AsyncSession, candidate: _Candidate) -> set[str]:
    """Which of the snapshot's memories still assert *this fact*, by identity.

    The project rides ``candidate.project`` rather than filtering the memories
    by their own — the same choice ``reconcile_memory_sources`` makes, and for
    the same reason: the fact's project is part of its identity, so a memory
    moved between projects after the scan still sources the fact it was
    asserting, and scoping to the memory's current project would strand it.
    """
    result = await session.execute(
        _STILL_ASSERTING, {"memory_ids": sorted(candidate.origins)}
    )
    return {
        memory_source_ref(row["memory_id"])
        for row in result.mappings().all()
        if compute_triple_key(
            candidate.project,
            row["subject_name"],
            row["rel_type"],
            row["object_name"],
        )
        == candidate.triple_key
    }


async def _lift_one(session: AsyncSession, candidate: _Candidate) -> _LiftedOne:
    """Resolve or mint the fact, add the missing sources, emit the difference.

    One event per newly written ``fact_sources`` row: the payload doc 08 §4.3
    fixes is ``{fact_id, memory_id}``, so an event is (fact, memory)-grained by
    construction — the same grain the withdrawal side emits at — and a fact that
    gained two sources in one tick has two memories to name, not one. The drain
    dedups fact ids.

    The assertion is **re-read here**, inside the savepoint and under the fact's
    own lock, rather than trusted from the scan's snapshot. See
    ``_STILL_ASSERTING``: provenance is a claim about what the graph says now,
    and writing it from a stale snapshot manufactures a witness.
    """
    if not candidate.origins:
        return _LiftedOne()

    fact_id = await _open_fact_id(session, candidate.triple_key)
    live = await _still_asserting(session, candidate)
    if not live:
        # Every memory behind this candidate stopped asserting it between the
        # scan and now. Minting on the strength of the snapshot would create a
        # fact no memory stands behind.
        #
        # The salience bar is NOT re-applied to `live`: it was evaluated by the
        # scan, so under this race a bar of two can mint a fact whose surviving
        # sources number one. Every such source is real, which is why this is
        # left rather than tightened -- re-applying the bar here would also
        # delete nothing and merely defer the fact to a tick where the count
        # recovers. Recorded so the bar is read as scan-time, not write-time.
        return _LiftedOne()

    minted = fact_id is None
    if fact_id is None:
        fact_id = await _mint_fact(session, candidate)
        stored: set[str] = set()
    else:
        stored = await _existing_refs(session, fact_id)

    sources = FactSourceRepository(session)
    added = 0
    for ref in sorted(live):
        if ref in stored:
            continue
        await sources.add_source(
            fact_id=fact_id,
            source_kind=MEMORY_SOURCE_KIND,
            source_ref=ref,
            origin_key=candidate.origins[ref],
        )
        await record_event(
            session,
            event_type="sources_changed",
            object_type="fact",
            object_id=UUID(fact_id),
            project=candidate.project,
            payload={"fact_id": fact_id, "memory_id": ref},
        )
        added += 1
    # Loaded as outstanding work and yet nothing was written: the scan's
    # pending predicate and the identity resolution disagree about this group,
    # so it will be reported outstanding again on every tick and hold a batch
    # slot. Rare -- it needs a name pair the database canonicaliser keeps apart
    # and the identity function folds -- but silent starvation is what makes it
    # worth a line in the log.
    #
    # Deliberately **not** conditioned on the whole snapshot still asserting.
    # An earlier spelling of this guard required `live == candidate.origins`
    # and was therefore inert in exactly the shape it was written for: when a
    # spelling-split group carries a memory the identity check excludes, `live`
    # is a strict subset and the warning never fired. A guard that is decorative
    # in its own motivating case is worse than none, because it reads as
    # coverage. The cost of the wider rule is one spurious line after a
    # re-extraction race retires the last memory that had work outstanding, so
    # this warning is a prompt to look, not proof of a defect.
    stalled = not minted and added == 0
    return _LiftedOne(minted=minted, sources_added=added, stalled=stalled)


async def run_lift(
    session: AsyncSession,
    *,
    batch_size: int = DEFAULT_LIFT_BATCH,
    min_asserting_memories: int = DEFAULT_MIN_ASSERTING_MEMORIES,
) -> LiftOutcome:
    """One lift tick. Does not commit — transaction control is the caller's.

    Each candidate is written inside its own savepoint so a poisonous one
    settles alone: a provenance failure rolls back the fact row it was meant to
    justify, rather than leaving an unfalsifiable fact behind or aborting the
    whole tick.
    """
    candidates = await _pending_candidates(
        session,
        batch_size=batch_size,
        min_asserting_memories=min_asserting_memories,
    )
    created = added = 0
    for candidate in candidates:
        try:
            async with session.begin_nested():
                lifted = await _lift_one(session, candidate)
        except Exception:
            logger.exception(
                "fact lifting failed for %s (%s %s %s) in project %s",
                candidate.triple_key,
                candidate.subject_name,
                candidate.rel_type,
                candidate.object_name,
                candidate.project,
            )
            continue
        if lifted.stalled:
            logger.warning(
                "fact %s (%s %s %s, project %s) is reported as outstanding work "
                "but resolves to a fact that already holds every source it "
                "asserts; it will hold a batch slot until its endpoint names "
                "canonicalise identically in SQL and in compute_triple_key",
                candidate.triple_key,
                candidate.subject_name,
                candidate.rel_type,
                candidate.object_name,
                candidate.project,
            )
        created += int(lifted.minted)
        added += lifted.sources_added
    return LiftOutcome(
        candidates=len(candidates),
        facts_created=created,
        sources_added=added,
        events_emitted=added,
    )
