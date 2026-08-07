"""Retroactive entity merge — the anchoring order that never healed (T2.101).

Doc 10 §6 sells the code bridge on anchoring: a ``postgres`` entity minted
from a repository's imports is meant to be the *same* deduped node as
``postgres`` from a memory. T2.97 embedded repo-minted entities so Phase 4's
ANN probe could see them, which closes exactly one order — repo indexed, then
anchored, then the memory ingested. The other order never healed:
``assert_from_repo`` is an exact-key ``ON CONFLICT (name, entity_type)`` upsert
with no probe, Phase 4 dedups at write time only, and the strip-and-rewrite is
keyed the same way, so re-derivation reproduces the same two rows. **That is
the order an existing install produces the first time it indexes a repo**, so
it is the common case rather than a corner, and it was pinned red by
``test_a_repo_indexed_after_the_memory_still_leaves_two_nodes``.

**Finding the pairs is the same comparison Phase 4 makes, run after the fact.**
The candidate set is the repo-asserted entities that already carry a vector;
the probe is ``find_similar_entity`` at the same 0.85 threshold under the same
``names_distinct`` gate. There is deliberately no second similarity path and no
second threshold: if retroactive merging ever warrants a different one, that is
a measured decision against the F1 harness (doc 06 §10), not a constant edited
here.

**The query vector is read out of the partition, never re-embedded.** Both
sides of every cosine therefore come from the same child table, which is what
makes invariant 2 structural rather than a promise — and it is why this pass
needs no embedder call at all. The fingerprint is resolved once, by data
(``resolve_read_fingerprint``, never ``llm_fingerprint()``), and the rotation
exposure Phase 3 documents does not apply: **this pass writes no vector**. An
embedder that rotates mid-run cannot mix two geometries into one table, because
the only rows it writes are graph rows, which carry no fingerprint, and the only
partition rows it removes are the loser's — removed by the ``ON DELETE CASCADE``
on ``entity_embeddings__<slug>.entity_id``, which reaches *every* fingerprint's
partition rather than the one that happened to be active. The decision itself
("these two names denote one node") is name-semantic and survives a rotation.

**Which entity survives, and why it is not symmetric.** The repo-asserted row
wins; if both sides are repo-asserted, the older ``created_at`` wins with the
smaller id as tie-break. The rule is chosen so the two indexing orders converge
on the *same* node: the eager order already canonicalises the memory-minted
name onto the pre-existing repo-minted one, so a retroactive pass that kept the
memory-minted row instead would trade an order-dependent node count for an
order-dependent node *name*. The tie-break exists so the outcome cannot depend
on which side of the pair the scan reached first, which is also what makes the
pass idempotent.

**The loser's id is not free, and the merge repoints what points at it.**
Nothing has a foreign key onto ``entities.id`` except ``entity_relations``
(cascade) and the ``entity_embeddings__<slug>`` partitions (cascade). One thing
references it without a key: ``knowledge_triples.subject_id`` / ``object_id``,
written by ``fact_lift`` and joined by ``review_ranking``'s salience arm, which
reads a dangling pointer as zero salience — silently, and forever. Those are
repointed here rather than left to rot.

**``(name, entity_type)`` uniqueness is what makes this delicate**, and the
relation constraint mirrors it: repointing an endpoint onto the survivor can
collide with an existing ``(source, target, rel_type)`` row, which is a relation
merge of its own — union the arrays, keep the greater weight, drop the duplicate
— never an integrity error left for the constraint to raise. Every pair is
merged inside one ``begin_nested()`` savepoint, the idiom ``assert_from_repo``
already uses, so a failure rolls back to two intact nodes rather than a
half-merged one.

**Tier C, and not a dream-job family member** (contract 6 fixes that family at
six; ``ppr_snapshot``, ``code_deriver`` and ``repo_entity_anchoring`` are the
precedents for Tier-C jobs outside it). Invariant 15 is unaffected: neither
capture nor retrieval reaches this module.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.graph import PostgresGraphRepository
from app.services.embedder_registry import child_table
from app.services.job_registry import FieldDescriptor
from app.services.relations import TECH_TYPES, names_distinct

logger = logging.getLogger(__name__)

PARENT_TABLE = "entity_embeddings"

REPO_ENTITY_MERGE_JOB_KEY = "repo_entity_merge"

# Phase 4's threshold, not a second one. `tests/test_repo_entity_merge.py`
# reads the literal Phase 4 passes out of `pipeline.py`'s AST and fails if the
# two drift apart, so this constant cannot quietly become a looser bar.
MERGE_THRESHOLD = 0.85

DEFAULT_CANDIDATE_BATCH = 200

REPO_ENTITY_MERGE_CONFIG_SCHEMA: list[FieldDescriptor] = [
    FieldDescriptor(
        key="candidate_batch", label="Repo Entities Probed Per Run",
        default=DEFAULT_CANDIDATE_BATCH, min=0, max=5_000,
        help=(
            "Repository-asserted entities with a vector under the active "
            "embedder that are probed for a near-named duplicate per run. "
            "Unlike the anchoring job's arm this one does not drain to zero: "
            "it is a rescan, and a run that merges nothing is the healthy "
            "steady state. 0 disables the job, which leaves a repo indexed "
            "after its memories with two nodes where there should be one."
        ),
    ),
]


class EntityMergeRefused(Exception):
    """A merge that must not be attempted, raised before anything is written.

    Distinct from a merge that fails: this is the pass refusing a pair whose
    shape violates a graph invariant, and the savepoint it raises inside leaves
    both rows exactly as they were.
    """


@dataclass(frozen=True)
class MergedPair:
    survivor_id: str
    survivor_name: str
    loser_id: str
    loser_name: str
    entity_type: str
    relations_repointed: int
    relations_folded: int
    memories_retouched: int


@dataclass
class MergeOutcome:
    merged: int = 0
    probed: int = 0
    fingerprint: str | None = None
    pairs: list[MergedPair] = field(default_factory=list)


def _candidate_sql(table: str) -> str:
    # `cardinality(...) > 0` is the repo-asserted scope, the same predicate the
    # anchoring job selects on and deliberately not index-driven: the GIN index
    # on `repo_ids` answers containment, not emptiness.
    #
    # The join to the partition is the other half of the scope: an entity with
    # no vector under this fingerprint has nothing to probe with, and it is the
    # anchoring job's business rather than this one's.
    return f"""
        SELECT CAST(e.id AS text) AS entity_id, e.name, e.entity_type,
               CAST(ee.embedding AS text) AS embedding
        FROM entities e
        JOIN {table} ee
          ON ee.entity_id = e.id
         AND ee.fingerprint = CAST(:fp AS text)
        WHERE COALESCE(cardinality(e.repo_ids), 0) > 0
        ORDER BY e.created_at, e.id
        LIMIT CAST(:limit AS int)
    """


def _parse_vector(raw: str) -> list[float]:
    return [float(x) for x in raw.strip("[]").split(",")]


async def resolve_read_fingerprint(session: AsyncSession, llm) -> str:
    """The fingerprint a partition read may safely key on. Delegated, never
    re-derived: ``llm_fingerprint()`` is a formatter over static config and can
    name a partition no embed ever wrote to (T2.68, T2.83), which here would
    silently report that no repo entity has a duplicate."""
    from app.repositories.vector import PostgresVectorRepository  # noqa: PLC0415

    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


async def repo_entity_merge_candidates(
    session: AsyncSession, fingerprint: str, limit: int,
) -> list[dict]:
    """Repository-asserted entities carrying a vector under this fingerprint.

    No ``to_regclass`` guard: ``resolve_read_fingerprint`` only ever returns a
    live row in ``embedders``, and registration is what created the child table.
    """
    if limit <= 0:
        return []
    table = child_table(PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(_candidate_sql(table)), {"fp": fingerprint, "limit": limit},
    )
    return [
        {
            "entity_id": row[0],
            "name": row[1],
            "entity_type": row[2],
            "embedding": _parse_vector(row[3]),
        }
        for row in rows.all()
    ]


def _choose_survivor(a: dict, b: dict) -> tuple[dict, dict]:
    """The survivor rule, applied to two freshly locked rows.

    Repo-asserted wins, so the retroactive order converges on the node the
    eager order already produces. Otherwise older wins, id as tie-break — the
    same shape as the supersession detector's equal-timestamp rule, and for the
    same reason: without it the outcome depends on which row the scan reached
    first, and the pass stops being idempotent.
    """
    a_repo = bool(a["repo_ids"])
    b_repo = bool(b["repo_ids"])
    if a_repo != b_repo:
        return (a, b) if a_repo else (b, a)
    if a["created_at"] != b["created_at"]:
        return (a, b) if a["created_at"] < b["created_at"] else (b, a)
    return (a, b) if a["id"] < b["id"] else (b, a)


def _merged_ids(survivor: list, loser: list) -> list[str]:
    """Union preserving the survivor's order, then the loser's own.

    Not ``array_agg(DISTINCT ...)``: that would re-sort ids the write path
    appends in assertion order, rewriting rows the merge has no reason to touch.
    """
    seen = {str(x) for x in survivor}
    out = [str(x) for x in survivor]
    for value in loser:
        key = str(value)
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out


def _merged_properties(survivor: dict, loser: dict, survivor_name: str) -> dict:
    """Survivor's keys win; ``display_name`` is kept only if it still renders
    this row's name.

    Invariant 7 pairs a lowercase name on disk with its original casing in
    ``properties.display_name``, and the two must stay one fact: adopting a
    losing ``postgresql`` row's ``"PostgreSQL"`` onto a surviving ``postgres``
    row would make the UI (``memory_community_labels``) render a name the graph
    does not hold.
    """
    props: dict[str, Any] = {**(loser or {}), **(survivor or {})}
    display = props.get("display_name")
    if not isinstance(display, str) or display.strip().lower() != survivor_name:
        props.pop("display_name", None)
    return props


async def merge_entities(
    session: AsyncSession, first_id: str, second_id: str,
) -> MergedPair | None:
    """Fuse two entity rows into one, atomically, or leave both untouched.

    ``None`` means there was nothing to do — the same row twice, or a row a
    previous merge in this run already consumed. Anything that cannot be
    completed raises out of the savepoint, and the caller sees two intact nodes.
    """
    ids = sorted({first_id, second_id})
    if len(ids) < 2:
        return None

    async with session.begin_nested():
        # Locked in id order so two concurrent merges over an overlapping pair
        # queue instead of deadlocking.
        rows = (await session.execute(
            text("""
                SELECT CAST(id AS text) AS id, name, entity_type, properties,
                       memory_ids, repo_ids, created_at
                FROM entities
                WHERE id = ANY(CAST(:ids AS uuid[]))
                ORDER BY id
                FOR UPDATE
            """),
            {"ids": ids},
        )).mappings().all()
        if len(rows) != 2:
            return None

        left, right = rows
        if left["entity_type"] != right["entity_type"]:
            # Unreachable through the type-constrained probe, and asserted
            # rather than assumed: a name embedding cannot tell a `tool` named
            # `react` from a `concept` named `react`, and fusing them corrupts
            # the (name, entity_type) binding that entity uniqueness, the
            # lowercase `technologies` denorm and relation-endpoint resolution
            # all rest on.
            raise EntityMergeRefused(
                f"refusing to merge across entity_type: "
                f"{left['name']}/{left['entity_type']} and "
                f"{right['name']}/{right['entity_type']}"
            )

        survivor, loser = _choose_survivor(left, right)
        survivor_id, loser_id = survivor["id"], loser["id"]
        merged_memory_ids = _merged_ids(
            survivor["memory_ids"] or [], loser["memory_ids"] or []
        )

        await session.execute(
            text("""
                UPDATE entities
                SET memory_ids = CAST(:mids AS uuid[]),
                    repo_ids   = CAST(:rids AS uuid[]),
                    properties = CAST(:props AS jsonb)
                WHERE id = CAST(:sid AS uuid)
            """),
            {
                "mids": merged_memory_ids,
                "rids": _merged_ids(
                    survivor["repo_ids"] or [], loser["repo_ids"] or []
                ),
                "props": json.dumps(_merged_properties(
                    survivor["properties"] or {}, loser["properties"] or {},
                    survivor["name"],
                )),
                "sid": survivor_id,
            },
        )

        repointed, folded = await _repoint_relations(
            session, survivor_id=survivor_id, loser_id=loser_id,
        )

        # `knowledge_triples` carries no foreign key onto `entities.id`, so
        # nothing would complain about the dangling pointer; `review_ranking`'s
        # salience arm would just read zero neighbours for every fact whose
        # subject was the losing row.
        for column in ("subject_id", "object_id"):
            await session.execute(
                text(f"""
                    UPDATE knowledge_triples
                    SET {column} = CAST(:sid AS uuid)
                    WHERE {column} = CAST(:lid AS uuid)
                """),
                {"sid": survivor_id, "lid": loser_id},
            )

        # The FK on entity_relations is ON DELETE CASCADE, so a relation this
        # loop missed would be destroyed by the DELETE below rather than
        # reported. Fail the savepoint instead: two nodes beat a merged node
        # with somebody else's edge silently gone.
        stranded = (await session.execute(
            text("""
                SELECT COUNT(*) FROM entity_relations
                WHERE source_entity_id = CAST(:lid AS uuid)
                   OR target_entity_id = CAST(:lid AS uuid)
            """),
            {"lid": loser_id},
        )).scalar_one()
        if stranded:
            raise EntityMergeRefused(
                f"{stranded} relation(s) still reference the losing entity "
                f"{loser_id}; refusing to let the cascade delete them"
            )

        # Takes the loser's rows in every `entity_embeddings__<slug>` partition
        # with it, per fingerprint, through that FK's cascade — which is the
        # only reach this pass has across partitions and the only one it needs.
        await session.execute(
            text("DELETE FROM entities WHERE id = CAST(:lid AS uuid)"),
            {"lid": loser_id},
        )

        retouched = await _recompute_technologies(
            session,
            entity_type=survivor["entity_type"],
            memory_ids=merged_memory_ids,
        )

    return MergedPair(
        survivor_id=survivor_id,
        survivor_name=survivor["name"],
        loser_id=loser_id,
        loser_name=loser["name"],
        entity_type=survivor["entity_type"],
        relations_repointed=repointed,
        relations_folded=folded,
        memories_retouched=retouched,
    )


async def _repoint_relations(
    session: AsyncSession, *, survivor_id: str, loser_id: str,
) -> tuple[int, int]:
    """Move every edge off the losing endpoint, folding constraint collisions.

    Both entities' incident edges are locked, not only the loser's: a repointed
    edge's collision partner is always one of the survivor's, because the new
    key always contains the survivor.
    """
    incident = (await session.execute(
        text("""
            SELECT CAST(id AS text) AS id,
                   CAST(source_entity_id AS text) AS source_entity_id,
                   CAST(target_entity_id AS text) AS target_entity_id,
                   rel_type
            FROM entity_relations
            WHERE source_entity_id = ANY(CAST(:ids AS uuid[]))
               OR target_entity_id = ANY(CAST(:ids AS uuid[]))
            ORDER BY id
            FOR UPDATE
        """),
        {"ids": [survivor_id, loser_id]},
    )).mappings().all()

    repointed = 0
    folded = 0
    for relation in incident:
        source = relation["source_entity_id"]
        target = relation["target_entity_id"]
        if loser_id not in (source, target):
            continue
        # A loser-to-survivor edge becomes a self-loop rather than being
        # dropped, because that is precisely what the eager order produces:
        # Phase 4 canonicalises both endpoint names onto one, and Phase 5's
        # `create_relationship` then resolves both to the same id. The
        # consumers that would be confused by one already exclude it
        # (`ppr_snapshot`, `review_ranking`'s salience arm).
        new_source = survivor_id if source == loser_id else source
        new_target = survivor_id if target == loser_id else target

        # Re-queried per edge rather than read from the snapshot above: an
        # earlier iteration may already have moved a row onto this key.
        collision = (await session.execute(
            text("""
                SELECT CAST(id AS text)
                FROM entity_relations
                WHERE source_entity_id = CAST(:src AS uuid)
                  AND target_entity_id = CAST(:tgt AS uuid)
                  AND rel_type = :rel
                  AND id <> CAST(:rid AS uuid)
            """),
            {
                "src": new_source, "tgt": new_target,
                "rel": relation["rel_type"], "rid": relation["id"],
            },
        )).scalar_one_or_none()

        if collision is None:
            await session.execute(
                text("""
                    UPDATE entity_relations
                    SET source_entity_id = CAST(:src AS uuid),
                        target_entity_id = CAST(:tgt AS uuid)
                    WHERE id = CAST(:rid AS uuid)
                """),
                {"src": new_source, "tgt": new_target, "rid": relation["id"]},
            )
            repointed += 1
            continue

        # The unions are computed in SQL against the keeper's current row, not
        # against a snapshot: a previous iteration in this same loop may have
        # folded into it already.
        await session.execute(
            text("""
                UPDATE entity_relations k
                SET memory_ids = k.memory_ids || ARRAY(
                        SELECT DISTINCT x FROM unnest(d.memory_ids) x
                        WHERE NOT (x = ANY(k.memory_ids))
                        ORDER BY 1
                    ),
                    repo_ids = k.repo_ids || ARRAY(
                        SELECT DISTINCT x FROM unnest(d.repo_ids) x
                        WHERE NOT (x = ANY(k.repo_ids))
                        ORDER BY 1
                    ),
                    weight = GREATEST(k.weight, d.weight),
                    properties = d.properties || k.properties
                FROM entity_relations d
                WHERE k.id = CAST(:kid AS uuid)
                  AND d.id = CAST(:did AS uuid)
            """),
            {"kid": collision, "did": relation["id"]},
        )
        await session.execute(
            text("DELETE FROM entity_relations WHERE id = CAST(:rid AS uuid)"),
            {"rid": relation["id"]},
        )
        folded += 1

    return repointed, folded


async def _recompute_technologies(
    session: AsyncSession, *, entity_type: str, memory_ids: list[str],
) -> int:
    """Refresh the ``memories.technologies`` denorm for every affected memory.

    Skipped whole when the merged type is not a ``TECH_TYPES`` member, and that
    is an equivalence rather than a shortcut: ``technologies_for_memory``
    projects only entities whose type is in that set, so neither the vanished
    name nor the surviving one can appear in any memory's array. Merging a
    ``concept`` therefore cannot change a single row, and running the recompute
    anyway would bump ``updated_at`` through the `touch_updated_at` trigger on
    memories nothing about them changed.

    The write is guarded by ``IS DISTINCT FROM`` for the same reason: within a
    tech-typed merge, a memory that asserted the survivor and not the loser
    keeps the array it had.
    """
    if entity_type not in TECH_TYPES or not memory_ids:
        return 0

    graph_repo = PostgresGraphRepository(session)
    touched = 0
    for memory_id in memory_ids:
        technologies = await graph_repo.technologies_for_memory(memory_id)
        result = await session.execute(
            text("""
                UPDATE memories
                SET technologies = CAST(:techs AS text[])
                WHERE id = CAST(:mid AS uuid)
                  AND technologies IS DISTINCT FROM CAST(:techs AS text[])
            """),
            {"techs": technologies, "mid": memory_id},
        )
        touched += result.rowcount or 0
    return touched


async def merge_repo_entity_duplicates(
    session: AsyncSession,
    llm,
    *,
    candidate_batch: int = DEFAULT_CANDIDATE_BATCH,
) -> MergeOutcome:
    """One tick of the retroactive merge pass.

    An install where nothing has been embedded yet has no fingerprint to key
    on, and this returns an empty outcome rather than inventing one.
    """
    from app.repositories.vector import (  # noqa: PLC0415
        EmbedderFingerprintUnresolved,
    )

    outcome = MergeOutcome()
    try:
        fingerprint = await resolve_read_fingerprint(session, llm)
    except EmbedderFingerprintUnresolved:
        logger.info(
            "repo_entity_merge: no fingerprint holds data yet; nothing to merge"
        )
        return outcome
    outcome.fingerprint = fingerprint

    candidates = await repo_entity_merge_candidates(
        session, fingerprint, candidate_batch,
    )
    graph_repo = PostgresGraphRepository(session)
    consumed: set[str] = set()

    for candidate in candidates:
        if candidate["entity_id"] in consumed:
            continue
        outcome.probed += 1
        match = await graph_repo.find_similar_entity(
            candidate["embedding"],
            fingerprint=fingerprint,
            threshold=MERGE_THRESHOLD,
            entity_type=candidate["entity_type"],
            exclude_entity_id=candidate["entity_id"],
        )
        if match is None or match["id"] in consumed:
            continue
        # The precision gate the embedding recall lacks, and deliberately the
        # stricter side of the trade here as much as in Phase 4: a false merge
        # cannot be undone by re-derivation, because the graph then records only
        # the merged form.
        if names_distinct(candidate["name"], match["name"]):
            continue

        try:
            pair = await merge_entities(session, candidate["entity_id"], match["id"])
        except Exception as exc:
            logger.warning(
                "repo_entity_merge: %s/%s and %s left unmerged: %s",
                candidate["name"], candidate["entity_type"], match["name"], exc,
            )
            continue
        if pair is None:
            continue

        consumed.add(pair.loser_id)
        outcome.merged += 1
        outcome.pairs.append(pair)

    return outcome
