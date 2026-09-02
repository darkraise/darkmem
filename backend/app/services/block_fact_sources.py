"""Block-sourced facts: one document is one origin (TH1.12, doc 16 §5).

**The rule this module exists for.** A document's blocks assert facts under the
`block` source kind, and every one of them carries the **document** as its
`origin_key` — never the block. Corroboration counts `COUNT(DISTINCT
origin_key)`, so a 400-block document that mentions the same claim in forty
places is one independent source, exactly as a repository with four hundred
files is one. Keying the origin on the block would manufacture forty origins
for one author's opinion and promote it on the strength of its own repetition,
which is the failure the whole independence rule exists to prevent.

`source_ref` stays the **block** id, so provenance is still per-span and a
reader can get back to the sentence. Origin is about independence; ref is about
traceability, and collapsing them in either direction loses one of the two.

**Withdrawal closes the window.** Removing a document withdraws its blocks'
provenance and enqueues every fact that lost a source for the ordinary
verification recompute — the same sweep a withdrawn memory or repository goes
through, not a bespoke one. A fact whose corroboration falls below its
threshold demotes there, on the ladder's own terms; nothing here writes a
verification column.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import BLOCK_SOURCE_KIND, FactSourceRepository

logger = logging.getLogger(__name__)

__all__ = [
    "BLOCK_SOURCE_KIND",
    "BlockWithdrawal",
    "record_block_source",
    "withdraw_blocks",
    "withdraw_document",
]

_BLOCK_DOCUMENT_SQL = text(
    "SELECT CAST(document_id AS text) AS document_id FROM blocks "
    "WHERE id = CAST(:id AS uuid)"
)
_DOCUMENT_BLOCKS_SQL = text(
    "SELECT CAST(id AS text) AS id FROM blocks WHERE document_id = CAST(:id AS uuid)"
)
_DELETE_SOURCES_SQL = text(
    "DELETE FROM fact_sources WHERE source_kind = :kind AND source_ref = ANY(:refs) "
    "RETURNING CAST(fact_id AS text) AS fact_id"
)


@dataclass(frozen=True)
class BlockWithdrawal:
    document_id: str
    blocks: int
    sources_removed: int
    facts_enqueued: tuple[str, ...]


async def record_block_source(
    session: AsyncSession,
    *,
    fact_id: UUID | str,
    block_id: UUID | str,
    detail: dict | None = None,
) -> dict | None:
    """Record that a block asserts a fact, under its document's origin.

    The caller passes the **block**, and this resolves the document itself
    rather than accepting one: a caller that could pass both could pass a
    mismatched pair, and the origin key is the number corroboration counts on.
    `None` when the block does not exist — a source pointing at nothing would
    count toward a fact's independence forever.
    """
    row = (await session.execute(
        _BLOCK_DOCUMENT_SQL, {"id": str(block_id)}
    )).mappings().first()
    if row is None:
        logger.warning("block_fact_sources: no block %s; recording nothing", block_id)
        return None

    return await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=BLOCK_SOURCE_KIND,
        source_ref=str(block_id),
        # The document, never the block. This one line is the rule.
        origin_key=row["document_id"],
        detail=detail,
    )


async def withdraw_document(
    session: AsyncSession, *, document_id: UUID | str,
) -> BlockWithdrawal:
    """Withdraw every block-source this document asserted.

    Returns the facts that lost a source so the caller can enqueue them for the
    ordinary verification recompute. Deliberately does not demote anything
    itself: the ladder decides what a fact's remaining corroboration is worth,
    and a withdrawal that wrote a rung would be a second authority over the
    verification column.
    """
    blocks = [
        row["id"] for row in (await session.execute(
            _DOCUMENT_BLOCKS_SQL, {"id": str(document_id)}
        )).mappings()
    ]
    return await withdraw_blocks(
        session, block_ids=blocks, document_id=str(document_id)
    )


async def withdraw_blocks(
    session: AsyncSession,
    *,
    block_ids: Sequence[str],
    document_id: UUID | str,
) -> BlockWithdrawal:
    """Withdraw the block-kind sources for exactly these blocks.

    The subtree half of :func:`withdraw_document`: a block delete removes one
    subtree rather than the document, and only that subtree's provenance goes
    with it. ``blocks.id`` is ``fact_sources.source_ref`` for block-kind
    sources and carries **no** foreign key, so deleting a block row without
    this leaves a fact corroborated by evidence that no longer exists.

    ``document_id`` is carried through rather than derived: the origin of a
    block source is its document, so it is what the caller must journal, and
    a delete has already removed the rows it could be re-derived from.

    Like its caller, this deliberately demotes nothing. The ladder decides
    what a fact's remaining corroboration is worth, and a withdrawal that
    wrote a rung would be a second authority over the verification column.
    """
    if not block_ids:
        return BlockWithdrawal(str(document_id), 0, 0, ())

    removed = (await session.execute(
        _DELETE_SOURCES_SQL, {"kind": BLOCK_SOURCE_KIND, "refs": list(block_ids)}
    )).mappings().all()
    fact_ids = tuple(dict.fromkeys(row["fact_id"] for row in removed))
    return BlockWithdrawal(
        document_id=str(document_id),
        blocks=len(block_ids),
        sources_removed=len(removed),
        facts_enqueued=fact_ids,
    )
