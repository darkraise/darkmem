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

**Repointing the fact layer's ids is only half of it, because fact identity is
name-keyed.** ``knowledge_triples`` denormalises both endpoint *names* beside
those ids and derives ``triple_key`` from them, and the canonicalisation
(``app.services.triple_key``) is lexical only — ``postgres`` and ``postgresql``
are two identities however close their embeddings sit. ``fact_lift``'s pending
predicate groups the graph by live entity name and matches existing open facts
on that name, so a merge that moved the ids and left the names would
re-qualify every already-lifted group as pending and mint a **second** open
triple for the same assertion set on the next tick: corroboration and
verification split across two rows, the facts channel serves both, and
``contradiction_scan``'s same-endpoint arm stops pairing across the boundary.
So the names and the key move with the ids, which is a rename of the fact's
identity — and recomputing ``triple_key`` can collide with an already-open row
on ``ux_knowledge_triples_open``. That collision is a **fact merge**, the
analogue one layer up of the relation fold below, and its rules are in
``_fold_open_facts``.

**One residue, stated rather than papered over.** A fact row whose endpoint id
is NULL or already dangling — the rot a strip-and-recreate leaves behind, since
the recreated entity carries a new id — keeps its name, because nothing ties it
to the losing row and the fact layer carries no ``entity_type`` to disambiguate
a name-only match. That row is not the duplicate-lift defect: the graph group it
came from no longer exists under the vanished name, so nothing re-lifts it. It
is an orphaned open fact, and it was orphaned before this pass ran.

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
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.repositories.graph import PostgresGraphRepository
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.embedder_registry import child_table
from app.services.events import record_event
from app.services.job_registry import FieldDescriptor
from app.services.relations import TECH_TYPES, names_distinct
from app.services.triple_key import compute_triple_key

logger = logging.getLogger(__name__)

PARENT_TABLE = "entity_embeddings"

REPO_ENTITY_MERGE_JOB_KEY = "repo_entity_merge"

# The scan's rotation cursor, in its own `config` row rather than inside
# `job:repo_entity_merge`'s `config` dict — the idiom
# `verification_recompute`'s slow arm already uses, and for its reason:
# `JobRegistry.set_config` is the operator-facing surface behind
# `PUT /api/v1/jobs/{key}/config` and validates every write against the
# schema below, so internal bookkeeping routed through it would either be
# rejected as an unknown key or, once admitted to the schema, become an
# operator-editable value.
MERGE_STATE_CONFIG_KEY = "repo_entity_merge_state"

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
_NIL_UUID = "00000000-0000-0000-0000-000000000000"

MERGED_EVENT_TYPE = "merged"

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
            "steady state. Successive runs rotate through the whole "
            "population rather than re-probing the same oldest slice, so "
            "this bounds the cost of one run, never the coverage. 0 disables "
            "the job, which leaves a repo indexed after its memories with "
            "two nodes where there should be one."
        ),
    ),
]

# The fact layer's own precedence, read off `verification_ladder.decide` rather
# than invented here: it holds a `confirmed` fact against every machine verdict
# including the veto ("the machine never moves it in either direction — not
# down on a lost origin, not sideways on a contradiction"), and the veto
# outranks any number of corroborations. `corroborated` over `candidate` is the
# monotonicity argument in `_fold_open_facts`.
_VERIFICATION_RANK = {
    "candidate": 0,
    "corroborated": 1,
    "disputed": 2,
    "confirmed": 3,
}


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
    facts_renamed: int
    facts_folded: int
    memories_retouched: int


@dataclass
class MergeOutcome:
    merged: int = 0
    probed: int = 0
    fingerprint: str | None = None
    wrapped: bool = False
    cursor: "MergeScanState | None" = None
    pairs: list[MergedPair] = field(default_factory=list)


def _candidate_sql(table: str) -> str:
    # `cardinality(...) > 0` is the repo-asserted scope, the same predicate the
    # anchoring job selects on and deliberately not index-driven: the GIN index
    # on `repo_ids` answers containment, not emptiness.
    #
    # The join to the partition is the other half of the scope: an entity with
    # no vector under this fingerprint has nothing to probe with, and it is the
    # anchoring job's business rather than this one's.
    #
    # The `(created_at, id)` keyset is what makes the batch a *window* rather
    # than a fixed prefix. `created_at` alone cannot carry it: rows written in
    # one transaction share one `now()`, so a bare `>` would skip the rest of a
    # tie and a bare `>=` would never leave it.
    return f"""
        SELECT CAST(e.id AS text) AS entity_id, e.name, e.entity_type,
               e.created_at,
               CAST(ee.embedding AS text) AS embedding
        FROM entities e
        JOIN {table} ee
          ON ee.entity_id = e.id
         AND ee.fingerprint = CAST(:fp AS text)
        WHERE COALESCE(cardinality(e.repo_ids), 0) > 0
          AND e.created_at >= CAST(:cur_ts AS timestamptz)
          AND (e.created_at > CAST(:cur_ts AS timestamptz)
               OR e.id > CAST(:cur_id AS uuid))
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


@dataclass(frozen=True)
class MergeScanState:
    """Where the last run stopped, so the next one starts after it.

    ``None`` on both fields is the start of the table, which is also what a
    short scan writes back: fewer rows than the batch means the walk reached the
    end, so the next run wraps. Without this the scan is a fixed prefix — a
    stable ``ORDER BY`` with a ``LIMIT`` and no cursor probes the same oldest
    ``candidate_batch`` entities forever, and an install with more never probes
    the rest, with no error and no symptom.
    """

    cursor_created_at: datetime | None = None
    cursor_entity_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "cursor_created_at": (
                self.cursor_created_at.isoformat()
                if self.cursor_created_at is not None else None
            ),
            "cursor_entity_id": self.cursor_entity_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MergeScanState":
        raw = data.get("cursor_created_at")
        parsed = None
        if raw:
            parsed = datetime.fromisoformat(raw)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
        return cls(cursor_created_at=parsed, cursor_entity_id=data.get("cursor_entity_id"))


async def load_scan_state(session: AsyncSession) -> MergeScanState:
    row = (await session.execute(
        select(Config).where(Config.key == MERGE_STATE_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None or not isinstance(row.value, dict):
        return MergeScanState()
    return MergeScanState.from_dict(row.value)


async def _save_scan_state(session: AsyncSession, state: MergeScanState) -> None:
    row = (await session.execute(
        select(Config).where(Config.key == MERGE_STATE_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key=MERGE_STATE_CONFIG_KEY, value=state.to_dict()))
    else:
        row.value = state.to_dict()


async def repo_entity_merge_candidates(
    session: AsyncSession,
    fingerprint: str,
    limit: int,
    state: MergeScanState | None = None,
) -> list[dict]:
    """Repository-asserted entities carrying a vector under this fingerprint,
    one rotation window at a time.

    No ``to_regclass`` guard: ``resolve_read_fingerprint`` only ever returns a
    live row in ``embedders``, and registration is what created the child table.
    """
    if limit <= 0:
        return []
    state = state or MergeScanState()
    table = child_table(PARENT_TABLE, fingerprint)
    rows = await session.execute(
        text(_candidate_sql(table)),
        {
            "fp": fingerprint,
            "limit": limit,
            "cur_ts": state.cursor_created_at or _EPOCH,
            "cur_id": state.cursor_entity_id or _NIL_UUID,
        },
    )
    return [
        {
            "entity_id": row[0],
            "name": row[1],
            "entity_type": row[2],
            "created_at": row[3],
            "embedding": _parse_vector(row[4]),
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

        facts_renamed, facts_folded = await _rename_facts(
            session,
            survivor_id=survivor_id,
            loser_id=loser_id,
            survivor_name=survivor["name"],
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

        pair = MergedPair(
            survivor_id=survivor_id,
            survivor_name=survivor["name"],
            loser_id=loser_id,
            loser_name=loser["name"],
            entity_type=survivor["entity_type"],
            relations_repointed=repointed,
            relations_folded=folded,
            facts_renamed=facts_renamed,
            facts_folded=facts_folded,
            memories_retouched=retouched,
        )
        # Inside the savepoint, so a merge that rolls back journals nothing:
        # `record_event` writes through a SAVEPOINT of its own nested in this
        # one, which unwinds with it.
        await record_event(
            session,
            event_type=MERGED_EVENT_TYPE,
            object_type="entity",
            object_id=UUID(survivor_id),
            payload={
                "survivor": {"id": survivor_id, "name": survivor["name"]},
                "loser": {"id": loser_id, "name": loser["name"]},
                "entity_type": survivor["entity_type"],
                "relations_repointed": repointed,
                "relations_folded": folded,
                "facts_renamed": facts_renamed,
                "facts_folded": facts_folded,
                "memories_retouched": retouched,
            },
        )

    return pair


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


_FACTS_ON_LOSER = text("""
    SELECT CAST(id AS text) AS id, project, rel_type,
           CAST(subject_id AS text) AS subject_id,
           CAST(object_id AS text) AS object_id,
           subject_name, object_name, verification_status, created_at,
           (expired_at IS NULL AND invalid_at IS NULL) AS open_belief
    FROM knowledge_triples
    WHERE subject_id = CAST(:lid AS uuid)
       OR object_id = CAST(:lid AS uuid)
    ORDER BY created_at, id
    FOR UPDATE
""")

# Re-queried per row rather than read from a snapshot: an earlier row in this
# same loop may already have taken this key. `id <>` is what keeps a row whose
# canonical key does not actually move — two spellings the identity function
# folds together — from colliding with itself.
_OPEN_FACT_ON_KEY = text("""
    SELECT CAST(id AS text) AS id, verification_status, created_at
    FROM knowledge_triples
    WHERE triple_key = CAST(:key AS text)
      AND expired_at IS NULL
      AND invalid_at IS NULL
      AND id <> CAST(:rid AS uuid)
    ORDER BY created_at, id
    LIMIT 1
    FOR UPDATE
""")

_RENAME_FACT = text("""
    UPDATE knowledge_triples
    SET subject_id   = CAST(:subject_id AS uuid),
        object_id    = CAST(:object_id AS uuid),
        subject_name = CAST(:subject_name AS text),
        object_name  = CAST(:object_name AS text),
        triple_key   = CAST(:key AS text)
    WHERE id = CAST(:rid AS uuid)
""")


async def _rename_facts(
    session: AsyncSession, *, survivor_id: str, loser_id: str, survivor_name: str,
) -> tuple[int, int]:
    """Move the fact layer's identity off the losing name, folding collisions.

    Scoped by the endpoint *id* — the pointer this merge owns — rather than by
    the name: the id is what says a fact row came from the losing entity, and
    the fact layer carries no ``entity_type`` to disambiguate a name-only match
    from the same name under another type. The module docstring records what
    that leaves behind and why it is not the duplicate-lift defect.

    ``fact`` is deliberately not rewritten. It is the fact's prose, written once
    by the lift and by nothing else since — the FTS and trigram indexes over it
    are expression indexes built on that premise — and its shape is owned by a
    single function this module may not reach (invariant 15's family scan).
    """
    rows = (await session.execute(_FACTS_ON_LOSER, {"lid": loser_id})).mappings().all()

    renamed = folded = 0
    for row in rows:
        subject_moves = row["subject_id"] == loser_id
        object_moves = row["object_id"] == loser_id
        new_subject_name = survivor_name if subject_moves else row["subject_name"]
        new_object_name = survivor_name if object_moves else row["object_name"]
        new_key = compute_triple_key(
            row["project"], new_subject_name, row["rel_type"], new_object_name,
        )

        if row["open_belief"]:
            partner = (await session.execute(
                _OPEN_FACT_ON_KEY, {"key": new_key, "rid": row["id"]},
            )).mappings().first()
            if partner is not None:
                await _fold_open_facts(session, row, partner)
                folded += 1

        await session.execute(
            _RENAME_FACT,
            {
                "subject_id": survivor_id if subject_moves else row["subject_id"],
                "object_id": survivor_id if object_moves else row["object_id"],
                "subject_name": new_subject_name,
                "object_name": new_object_name,
                "key": new_key,
                "rid": row["id"],
            },
        )
        renamed += 1

    return renamed, folded


def _fact_rank(status: Any) -> int:
    return _VERIFICATION_RANK.get(str(status), 0)


async def _fold_open_facts(session: AsyncSession, renamed: Any, partner: Any) -> None:
    """Two open rows for one logical fact become one. The rules, and why.

    **Which row keeps the id is a truth-layer choice, so it is made on the
    verification axis and nowhere else**: the higher rung survives, ties broken
    by the older ``created_at`` and then the smaller id — the ordering
    ``knowledge_triples``' own open-fact lookup already uses, so the fold cannot
    depend on which side the scan reached first. Choosing the keeper this way is
    what lets the fold write **no** verification column at all: the surviving
    rung is the one the sanctioned door already wrote, so no promotion escapes
    the ladder, no ratification escapes the human path, and no ``verified``
    journal row appears for a transition no evidence explains.

    The precedence is the ladder's own. ``confirmed`` outranks everything
    because the machine never moves a ratified fact in either direction, not
    even sideways on a contradiction; ``disputed`` outranks the counted rungs
    because one non-echo contradiction beats any number of corroborations, and
    the counterpart that produced it survives the fold; ``corroborated``
    outranks ``candidate`` because the keeper's evidence after the fold is a
    **superset** of what either row had and corroboration is monotone in that
    set — so the higher rung is the one the union supports, and demoting here
    would strip a badge the evidence still carries.

    **The evidence moves, it is not copied.** ``fact_sources`` is what
    ``COUNT(DISTINCT origin_key)`` reads, so leaving a copy behind would let one
    memory corroborate one claim twice. Exact duplicates are dropped rather than
    moved, because the target already holds that witness.

    **The retired row is expired, never deleted.** ``article_citations`` takes a
    hard FK onto ``knowledge_triples.id`` precisely because facts are
    invalidate-not-delete. ``expired_at`` rather than ``invalid_at`` is the
    right marker: the row is not a belief that stopped holding, it is a
    duplicate identity being withdrawn, and the contradiction scan's shortlist
    is partial on ``expired_at IS NULL`` — closing the window instead would
    leave the scan free to pair a fact against itself under its other name.
    """
    def order(row: Any) -> tuple:
        return (-_fact_rank(row["verification_status"]), row["created_at"], row["id"])

    keeper, retired = (
        (renamed, partner) if order(renamed) <= order(partner) else (partner, renamed)
    )

    await session.execute(
        text("""
            UPDATE fact_sources fs
            SET fact_id = CAST(:keeper AS uuid)
            WHERE fs.fact_id = CAST(:retired AS uuid)
              AND NOT EXISTS (
                  SELECT 1 FROM fact_sources k
                  WHERE k.fact_id = CAST(:keeper AS uuid)
                    AND k.source_kind IS NOT DISTINCT FROM fs.source_kind
                    AND k.source_ref IS NOT DISTINCT FROM fs.source_ref
              )
        """),
        {"keeper": keeper["id"], "retired": retired["id"]},
    )
    await session.execute(
        text("DELETE FROM fact_sources WHERE fact_id = CAST(:retired AS uuid)"),
        {"retired": retired["id"]},
    )

    # Serving heat is a derived aggregate over one logical fact; split across
    # two rows it under-reports the survivor to `review_ranking`'s frequency arm.
    await session.execute(
        text("""
            INSERT INTO fact_access_stats (fact_id, access_count, last_accessed)
            SELECT CAST(:keeper AS uuid), access_count, last_accessed
            FROM fact_access_stats WHERE fact_id = CAST(:retired AS uuid)
            ON CONFLICT (fact_id) DO UPDATE
            SET access_count  = fact_access_stats.access_count
                                + EXCLUDED.access_count,
                last_accessed = GREATEST(fact_access_stats.last_accessed,
                                         EXCLUDED.last_accessed)
        """),
        {"keeper": keeper["id"], "retired": retired["id"]},
    )
    await session.execute(
        text("DELETE FROM fact_access_stats WHERE fact_id = CAST(:retired AS uuid)"),
        {"retired": retired["id"]},
    )

    # The belief window is the union of two open-ended ones, so it starts at the
    # earlier of the two: both rows asserted the claim, and the keeper's own
    # start would disown a stretch the vault did believe it. A NULL `valid_at`
    # is unbounded, so it dominates rather than losing to `LEAST`. `LEAST` is
    # the whole rule for `stated_expiry` — it ignores NULLs, which lands on the
    # earlier stated expiry, the under-claiming direction this layer is required
    # to err in. `learned_in` has no writer in the tree today and is left alone.
    await session.execute(
        text("""
            UPDATE knowledge_triples k
            SET reference_time = LEAST(k.reference_time, d.reference_time),
                valid_at = CASE
                    WHEN k.valid_at IS NULL OR d.valid_at IS NULL THEN NULL
                    ELSE LEAST(k.valid_at, d.valid_at)
                END,
                stated_expiry = LEAST(k.stated_expiry, d.stated_expiry)
            FROM knowledge_triples d
            WHERE k.id = CAST(:keeper AS uuid)
              AND d.id = CAST(:retired AS uuid)
        """),
        {"keeper": keeper["id"], "retired": retired["id"]},
    )

    await KnowledgeTripleRepository(session).expire(retired["id"])


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

    The tick probes one rotation window, then persists where it stopped, so
    ``candidate_batch`` bounds a run's cost and not the population the pass can
    reach. A window shorter than the batch is the end of the table, and the
    cursor resets.
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

    state = await load_scan_state(session)
    candidates = await repo_entity_merge_candidates(
        session, fingerprint, candidate_batch, state,
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

    # Advanced over the window that was *scanned*, not the pairs that merged: a
    # candidate the probe cleared is exactly the one that must not be re-probed
    # before the rest of the table has been.
    if candidates:
        last = candidates[-1]
        state = replace(
            state,
            cursor_created_at=last["created_at"],
            cursor_entity_id=last["entity_id"],
        )
    if len(candidates) < candidate_batch:
        state = MergeScanState()
        outcome.wrapped = True
    if candidate_batch > 0:
        await _save_scan_state(session, state)
    outcome.cursor = state
    return outcome
