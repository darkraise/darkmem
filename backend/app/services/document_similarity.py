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

So: walk the live embedders newest first and take the first whose partitions
hold rows for both sides. It degrades correctly — during a rotation the panel
serves the old fingerprint's comparison until both sides finish re-embedding,
rather than serving a comparison that does not mean anything.
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
    """The newest live fingerprint holding vectors for both sides, or None."""
    if counterpart not in COUNTERPARTS:
        raise ValueError(f"counterpart must be one of {COUNTERPARTS!r}")

    rows = (await session.execute(_LIVE_EMBEDDERS)).all()
    for (fingerprint,) in rows:
        # Interpolated, not bound: these are table identifiers, which no
        # driver parameterises. They come from `child_table` over a
        # fingerprint read out of `embedders`, never from a caller.
        blocks = child_table("block_embeddings", fingerprint)
        has_document = await session.scalar(
            text(
                f"SELECT EXISTS (SELECT 1 FROM {blocks} be "
                f"JOIN blocks b ON b.id = be.block_id "
                f"WHERE b.document_id = CAST(:document_id AS uuid))"
            ),
            {"document_id": document_id},
        )
        if not has_document:
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

        if has_counterpart:
            return fingerprint
    return None
