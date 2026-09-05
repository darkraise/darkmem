"""The fingerprint a document relatedness read compares under (spec §3.5).

Two surfaces need this before they can compare anything — `document_related`
(a document's blocks against the project's memories) and `document_connections`
(a document's blocks against other documents' blocks) — and both need the same
guarantee: a fingerprint in which BOTH sides hold vectors. A cosine across
fingerprints has no defined value, so comparing under one side's fingerprint
alone is not a degraded answer, it is a meaningless one.

**Derived from the data, never resolved through the embedder.**
`block_embeddings.resolve_active_fingerprint` is a real embed call per caller —
a network call this read must not make, since it would oblige
`refuse_when_read_only` on the route and break the no-model-call pin these
surfaces carry. `resolve_read_fingerprint` is a data probe biased toward a
stale populated partition after a rotation, which would serve old-embedder rows
while search serves the active ones.

So: walk the live embedders newest first, and prefer the newest fingerprint
holding a vector for **every** block of this document; fall back to the newest
holding *some* block of it. Both passes additionally require the counterpart
side to hold at least one vector.

**What that does and does not guarantee, stated exactly, because the sentence
here used to overclaim.** It said the panel "serves the old fingerprint's
comparison until both sides finish re-embedding". That was false of a
completeness-blind `EXISTS` check, and it is only half true now. Both
re-embed paths are incremental — `reembed.py` commits per batch,
`block_embedding_refresh` embeds `batch` blocks per tick — so a partially
filled new partition exists long before it is usable. Measured on a two-
fingerprint database with NEW holding 1 of 3 blocks and 1 of 3 memories while
OLD held 3 of 3 on both sides, the `EXISTS`-only resolver picked NEW and
reported one comparable memory. The document-side completeness pass fixes that
case: a half-embedded document no longer wins over a fully embedded one.

The **counterpart side is still existence-only**, and deliberately: completeness
there means scanning every memory (or every other document's blocks) in the
project on every panel read, which is a cost this surface has not measured and
does not need to pay to fix the reproduced defect. The residual is real and
named — a fingerprint whose document side is complete but whose memory or
document re-embed is still in flight wins, and the panel under-reports how much
it compared against. The counts on the envelope are `comparable_*`, which
`document_related` and `document_connections` compute independently of any
fingerprint, so that under-report shows up as returned items rather than as a
smaller denominator.

**Adjacent hazard, recorded rather than fixed: `retired_at` has no writer.**
The query below orders live embedders by `registered_at` and nothing in
`backend/app` ever writes `retired_at` (grep: it is read in `vector.py`,
`reembed.py`, `embedder_registry.py` and here, and written only by the baseline
DDL as a nullable column). So after a rotate-back — A, then B, then A again —
B stays live and newest forever, and its stale partition wins every resolution
in which it holds any vector for the document. Retiring an embedder is
today a manual `UPDATE`.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedder_registry import child_table

__all__ = ["COUNTERPARTS", "resolve_shared_fingerprint"]

COUNTERPARTS = ("memory", "block")

_LIVE_EMBEDDERS = text(
    "SELECT fingerprint FROM embedders "
    "WHERE retired_at IS NULL ORDER BY registered_at DESC"
)


async def resolve_shared_fingerprint(
    session: AsyncSession,
    *,
    document_id: str,
    project: str,
    counterpart: str,
) -> str | None:
    """The fingerprint to compare under, preferring complete document coverage.

    Returns the newest live fingerprint holding a vector for every block of
    this document and at least one on the counterpart side; failing that, the
    newest holding at least one block of it and at least one counterpart;
    failing that, `None`.
    """
    if counterpart not in COUNTERPARTS:
        raise ValueError(f"counterpart must be one of {COUNTERPARTS!r}")

    rows = (await session.execute(_LIVE_EMBEDDERS)).all()
    partial: str | None = None

    for (fingerprint,) in rows:
        # Interpolated, not bound: these are table identifiers, which no
        # driver parameterises. They come from `child_table` over a
        # fingerprint read out of `embedders`, never from a caller.
        blocks = child_table("block_embeddings", fingerprint)
        coverage = (await session.execute(
            text(
                f"SELECT count(*) AS total, "
                f"count(be.block_id) AS embedded "
                f"FROM blocks b "
                f"LEFT JOIN {blocks} be ON be.block_id = b.id "
                f"WHERE b.document_id = CAST(:document_id AS uuid)"
            ),
            {"document_id": document_id},
        )).mappings().one()
        total, embedded = int(coverage["total"]), int(coverage["embedded"])
        if embedded == 0:
            continue

        if counterpart == "memory":
            memories = child_table("memory_embeddings", fingerprint)
            has_counterpart = await session.scalar(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {memories} me "
                    f"JOIN memories m ON m.id = me.memory_id "
                    f"WHERE m.project = :project)"
                ),
                {"project": project},
            )
        else:
            has_counterpart = await session.scalar(
                text(
                    f"SELECT EXISTS (SELECT 1 FROM {blocks} be "
                    f"JOIN blocks b ON b.id = be.block_id "
                    f"JOIN documents d ON d.id = b.document_id "
                    f"WHERE d.project = :project "
                    f"AND d.id <> CAST(:document_id AS uuid))"
                ),
                {"project": project, "document_id": document_id},
            )

        if not has_counterpart:
            continue
        if embedded == total:
            return fingerprint
        if partial is None:
            partial = fingerprint

    return partial
