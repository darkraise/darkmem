"""The ``triple_embeddings`` writer and the fact grouping it exists to serve.

Doc 08 §5.3 deferred this writer behind a *measured* undercount of the
same-endpoint + ``pg_trgm`` contradiction shortlist, and doc 04 §5.3 landed the
partition template inert for it. The measurement has been taken:
``docs/eval/2026-08-05-t2.52-contradiction-missrate.md`` records **41.7% (5/12)
missed on the `lexically-disjoint` slice against a 20% bar stated beforehand**,
so the vector-ANN arm is justified and this module is it.

**Grouping is for counting. It never merges rows and it never rewrites
``triple_key``.** That is doc 08 §5.3's wording and it is the whole safety
argument: two facts that say the same thing in different words are *evidence
about one claim*, so the corroboration arithmetic may count their origins
together, but the rows stay separate and keep their own identity. A writer that
collapsed them would destroy a distinct belief with no error and no symptom —
the rows would simply stop existing, and every later "what did we believe as of
date X" answer would be wrong. So this module writes exactly ONE table, the
per-fingerprint ``triple_embeddings__<slug>`` partition; it issues no statement
against ``knowledge_triples`` other than ``SELECT``, and
``tests/test_triple_embeddings.py`` fails the build on any other verb reaching
that table from here.

**``names_distinct`` is carried into the grouping, and completely.** It is the
same guard Phase-4 entity dedup carries (doc 06 §5): names differing by a
discriminating token — a number, a date, a version, a month — are distinct
however close their embeddings sit, so ``postgres 14`` never groups with
``postgres 15`` on cosine similarity alone. Two things make the guard total
rather than decorative here:

- It is checked on **both endpoints** of the triple plus the predicate. Facts
  whose ``rel_type`` differs are different claims and never group, which is the
  conservative direction: grouping is what *raises* a corroboration count, so
  every doubt resolves toward fewer groups.
- Merging uses **complete linkage**, not transitive closure. ``names_distinct``
  is very nearly an equivalence on its discriminating-token key, but not
  exactly: its "same string modulo punctuation" early return can make ``a~b``
  and ``b~c`` mergeable while ``a~c`` is distinct. Union-find over pairs would
  then merge ``a`` with ``c`` through ``b`` and the guard would be silently
  bypassed on exactly the pair it was written for. So two groups combine only
  when **every** cross-pair passes; a single distinct pair blocks the merge.

**Partition discipline (CLAUDE.md, doc 08 §5.3).** Child tables are named only
through ``child_table(parent, fingerprint)``, one fingerprint is used per call,
and nothing here joins across fingerprints — a cross-fingerprint cosine has no
defined meaning. The two sides resolve the fingerprint the way live paths do
and neither calls ``llm_fingerprint()``: the writer takes it from
``embed_batch_chunked``'s return value, an actual vector's length, so the
``model|0`` sentinel that has already cost three tasks (T2.68, T2.83, T2.12's
F3) is not representable on that path at all; the read side goes through
``PostgresVectorRepository.resolve_read_fingerprint``, which refuses to key a
partition read on a fingerprint no real embed ran under. The fingerprint
identifies the embedder, not the parent table, so resolving it against the
memory partitions is the same answer for this one.

**Nothing calls this yet, by design.** T2.33 is terminal in the task graph: the
consumer doc 08 §5.3 names is ``contradiction_scan``, which is still a
``PlaceholderJobRunner`` (T2.11). This module is the arm that task will reach
for, landing reviewed and tested ahead of it, exactly as its template did.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_triples import LIVE_PREDICATE, OPEN_BELIEF_PREDICATE
from app.repositories.vector import PostgresVectorRepository
from app.services.embedder_registry import child_table
from app.services.relations import names_distinct

logger = logging.getLogger(__name__)

PARENT_TABLE = "triple_embeddings"

DEFAULT_EMBED_CHUNK = 64
DEFAULT_EMBED_CONCURRENCY = 4

# Doc 08 §5.3's per-fact bound, mirroring `contradiction_candidate_top_k`'s
# default: the ANN arm is a shortlist generator, not a scan.
DEFAULT_GROUP_TOP_K = 10

# Cosine similarity two facts must reach before the name guard is even asked.
# Every knob on this path errs toward fewer groups, because a group is what
# raises a corroboration count and the fact layer may undercount but never
# overcount (doc 08 §4.1).
DEFAULT_GROUP_THRESHOLD = 0.90


@dataclass(frozen=True)
class FactRow:
    """The identity a grouping decision is made on, and nothing more."""

    fact_id: str
    subject_name: str
    object_name: str
    rel_type: str


@dataclass(frozen=True)
class FactNeighbour:
    row: FactRow
    similarity: float


@dataclass(frozen=True)
class FactGroup:
    """Facts the counter may treat as evidence about one claim.

    ``fact_ids`` are the members' ids, sorted. A one-member group is a fact
    nothing groups with, and it is returned rather than dropped: the result is
    a complete partition of the facts in scope, so a counter never has to guess
    whether a missing fact was ungrouped or out of scope.
    """

    fact_ids: tuple[str, ...]

    @property
    def size(self) -> int:
        return len(self.fact_ids)


@dataclass(frozen=True)
class WriteResult:
    fingerprint: str
    written: int


_LIVE_FACT_TEXTS = f"""
    SELECT CAST(id AS text) AS fact_id, fact
    FROM knowledge_triples
    WHERE id = ANY(CAST(:ids AS uuid[]))
      AND {LIVE_PREDICATE}
    ORDER BY id
"""


async def embed_facts(
    session: AsyncSession,
    llm,
    *,
    fact_ids: Sequence[str],
    chunk_size: int = DEFAULT_EMBED_CHUNK,
    concurrency: int = DEFAULT_EMBED_CONCURRENCY,
) -> WriteResult | None:
    """Embed each live fact's ``fact`` text into the active partition.

    ``None`` means nothing was embedded — no live row among ``fact_ids``, or an
    empty request — and therefore that no fingerprint was measured. It is not a
    failure: a caller draining a work set legitimately finds it empty.

    Scoped to ``LIVE_PREDICATE`` rather than to open belief. A window-closed row
    is retained history and is exactly what bi-temporal contradiction search
    reads back (doc 08 §3.1), so dropping its vector would blind the arm to the
    past it exists to search.

    Re-embedding an already-embedded fact refreshes its vector and leaves
    ``created_at`` at the first write, so the row records when this fact entered
    the partition rather than when it was last touched.
    """
    ids = [str(fact_id) for fact_id in fact_ids]
    if not ids:
        return None

    rows = (await session.execute(text(_LIVE_FACT_TEXTS), {"ids": ids})).mappings().all()
    if not rows:
        return None

    vectors, fingerprint = await llm.embed_batch_chunked(
        [row["fact"] for row in rows], chunk_size, concurrency,
    )
    if len(vectors) != len(rows):
        raise RuntimeError(
            f"triple_embeddings: the embedder returned {len(vectors)} vectors for "
            f"{len(rows)} facts; refusing to write vectors under ids they may not belong to"
        )

    await _ensure_partition(session, fingerprint)
    table = child_table(PARENT_TABLE, fingerprint)
    for row, vector in zip(rows, vectors):
        await session.execute(
            text(f"""
                INSERT INTO {table} (fact_id, fingerprint, embedding)
                VALUES (CAST(:fact_id AS uuid), CAST(:fp AS text), CAST(:embedding AS vector))
                ON CONFLICT (fact_id, fingerprint) DO UPDATE
                    SET embedding = EXCLUDED.embedding
            """),
            {"fact_id": row["fact_id"], "fp": fingerprint, "embedding": str(list(vector))},
        )

    return WriteResult(fingerprint=fingerprint, written=len(rows))


async def _ensure_partition(session: AsyncSession, fingerprint: str) -> None:
    from app.services.embedder_registry import (  # noqa: PLC0415
        EmbedderInfo, embedder_registry, parse_fingerprint,
    )
    if embedder_registry.is_known(fingerprint):
        return
    model_id, dims = parse_fingerprint(fingerprint)
    await embedder_registry.register(
        session,
        EmbedderInfo(fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"),
    )


async def resolve_read_fingerprint(session: AsyncSession, llm) -> str:
    """The fingerprint a partition read may safely key on.

    Delegated, never re-derived: ``llm_fingerprint()`` is a pure formatter over
    static config and can name a partition no embed ever wrote to — the ``|0``
    sentinel under unset dimensions, or a syntactically valid but permanently
    empty table under a wrong positive one. Both read as "no similar facts
    exist", forever, with no error. Raises
    :class:`~app.repositories.vector.EmbedderFingerprintUnresolved` rather than
    proceeding on an unconfirmed key.
    """
    return await PostgresVectorRepository(session).resolve_read_fingerprint(llm)


_OPEN_FACTS = f"""
    SELECT CAST(id AS text) AS fact_id, subject_name, object_name, rel_type
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND {OPEN_BELIEF_PREDICATE}
    ORDER BY id
"""

_OPEN_FACTS_RESTRICTED = f"""
    SELECT CAST(id AS text) AS fact_id, subject_name, object_name, rel_type
    FROM knowledge_triples
    WHERE project = CAST(:project AS text)
      AND id = ANY(CAST(:ids AS uuid[]))
      AND {OPEN_BELIEF_PREDICATE}
    ORDER BY id
"""


async def open_facts(
    session: AsyncSession, *, project: str, fact_ids: Sequence[str] | None = None,
) -> list[FactRow]:
    """The project's currently-believed facts, in id order.

    Open belief, not "live": a window-closed row is history, and counting its
    origins toward a claim nothing currently asserts would corroborate a belief
    that has already been withdrawn.
    """
    if fact_ids is None:
        result = await session.execute(text(_OPEN_FACTS), {"project": project})
    else:
        ids = [str(fact_id) for fact_id in fact_ids]
        if not ids:
            return []
        result = await session.execute(
            text(_OPEN_FACTS_RESTRICTED), {"project": project, "ids": ids},
        )
    return [_row(mapping) for mapping in result.mappings()]


def _row(mapping) -> FactRow:
    return FactRow(
        fact_id=mapping["fact_id"],
        subject_name=mapping["subject_name"],
        object_name=mapping["object_name"],
        rel_type=mapping["rel_type"],
    )


async def fact_vectors(
    session: AsyncSession, *, fingerprint: str, fact_ids: Sequence[str],
) -> dict[str, list[float]]:
    """Each fact's vector from the active partition, in one read.

    Never falls back to another fingerprint: a cross-fingerprint cosine has no
    defined meaning, so a fact with no row here is left ungrouped rather than
    probed somewhere else.
    """
    ids = [str(fact_id) for fact_id in fact_ids]
    if not ids:
        return {}
    table = child_table(PARENT_TABLE, fingerprint)
    result = await session.execute(
        text(
            f"SELECT CAST(fact_id AS text) AS fact_id, embedding::text AS embedding_text "
            f"FROM {table} WHERE fact_id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": ids},
    )
    return {
        mapping["fact_id"]: [float(v) for v in mapping["embedding_text"].strip("[]").split(",")]
        for mapping in result.mappings()
    }


async def similar_facts(
    session: AsyncSession,
    *,
    fingerprint: str,
    project: str,
    fact_id: str,
    vector: Sequence[float],
    top_k: int = DEFAULT_GROUP_TOP_K,
) -> list[FactNeighbour]:
    """One ANN probe: the project's nearest open facts to ``vector``.

    The candidate arm doc 08 §5.3 justifies — the semantic complement to the
    same-endpoint and ``pg_trgm`` shortlists, which is why it exists: those two
    are lexical and miss a contradiction whose two sides share no tokens.
    """
    table = child_table(PARENT_TABLE, fingerprint)
    result = await session.execute(
        text(f"""
            SELECT CAST(t.id AS text) AS fact_id,
                   t.subject_name,
                   t.object_name,
                   t.rel_type,
                   1 - (e.embedding <=> CAST(:vec AS vector)) AS similarity
            FROM {table} e
            JOIN knowledge_triples t ON t.id = e.fact_id
            WHERE t.project = CAST(:project AS text)
              AND {OPEN_BELIEF_PREDICATE}
              AND e.fact_id <> CAST(:fact_id AS uuid)
            ORDER BY e.embedding <=> CAST(:vec AS vector)
            LIMIT CAST(:top_k AS integer)
        """),
        {
            "vec": str(list(vector)),
            "project": project,
            "fact_id": str(fact_id),
            "top_k": top_k,
        },
    )
    return [
        FactNeighbour(row=_row(mapping), similarity=float(mapping["similarity"]))
        for mapping in result.mappings()
    ]


def may_group(a: FactRow, b: FactRow) -> bool:
    """Whether two facts may be counted as evidence about one claim.

    Embedding similarity has already been asked by the time this is called;
    this is the lexical precision the similarity lacks. A differing predicate,
    a discriminating token on either endpoint, and the two facts are separate
    claims however close their vectors sit.
    """
    if a.rel_type.strip().lower() != b.rel_type.strip().lower():
        return False
    if names_distinct(a.subject_name, b.subject_name):
        return False
    return not names_distinct(a.object_name, b.object_name)


async def group_facts(
    session: AsyncSession,
    *,
    fingerprint: str,
    project: str,
    fact_ids: Sequence[str] | None = None,
    threshold: float = DEFAULT_GROUP_THRESHOLD,
    top_k: int = DEFAULT_GROUP_TOP_K,
) -> list[FactGroup]:
    """Partition the project's open facts into counting groups.

    Reads only. The returned groups are an *answer*, not a mutation: no row is
    merged, no ``triple_key`` is rewritten, and running this twice over an
    unchanged corpus writes nothing either time.

    ``fact_ids`` restricts which facts are grouped *among themselves*; a
    neighbour outside that set is ignored rather than pulled in, so a caller
    draining a work set gets groups over its own batch.
    """
    rows = await open_facts(session, project=project, fact_ids=fact_ids)
    if len(rows) < 2:
        return [FactGroup(fact_ids=(row.fact_id,)) for row in rows]

    by_id = {row.fact_id: row for row in rows}
    vectors = await fact_vectors(
        session, fingerprint=fingerprint, fact_ids=list(by_id),
    )

    pairs: dict[tuple[str, str], float] = {}
    for row in rows:
        vector = vectors.get(row.fact_id)
        if vector is None:
            continue
        for neighbour in await similar_facts(
            session,
            fingerprint=fingerprint,
            project=project,
            fact_id=row.fact_id,
            vector=vector,
            top_k=top_k,
        ):
            other = neighbour.row.fact_id
            if other not in by_id or neighbour.similarity < threshold:
                continue
            key = (row.fact_id, other) if row.fact_id < other else (other, row.fact_id)
            # The two directions of one pair can differ in the last bits of a
            # float; keeping the larger keeps the ordering below symmetric.
            pairs[key] = max(pairs.get(key, 0.0), neighbour.similarity)

    return _agglomerate(rows, by_id, pairs)


def _agglomerate(
    rows: list[FactRow],
    by_id: dict[str, FactRow],
    pairs: dict[tuple[str, str], float],
) -> list[FactGroup]:
    """Complete-linkage merge under :func:`may_group`.

    Closest pair first, and two groups combine only when every cross-pair
    passes the guard — so a fact can never be dragged into a group it is
    distinct from by way of an intermediate it happens to match.
    """
    component: dict[str, str] = {row.fact_id: row.fact_id for row in rows}
    members: dict[str, list[str]] = {row.fact_id: [row.fact_id] for row in rows}

    ordered = sorted(pairs.items(), key=lambda item: (-item[1], item[0]))
    for (left, right), _similarity in ordered:
        a, b = component[left], component[right]
        if a == b:
            continue
        if not all(may_group(by_id[x], by_id[y]) for x in members[a] for y in members[b]):
            continue
        keep, drop = (a, b) if a < b else (b, a)
        for fact_id in members[drop]:
            component[fact_id] = keep
        members[keep].extend(members.pop(drop))

    return sorted(
        (FactGroup(fact_ids=tuple(sorted(group))) for group in members.values()),
        key=lambda group: group.fact_ids,
    )
