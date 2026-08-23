"""The document door's write half (spec 2026-08-23).

**Embed after commit, never inside the filing.** First contact with an unknown
fingerprint runs child-table DDL through `embedder_registry.register`, which
commits on this session; embedding inside the filing transaction would make the
filing non-rollback-able. So: file, commit, then embed.

**The `unchanged` path still embeds.** `ingest_document` returns UNCHANGED
before touching any block, so a re-push of an identical file files nothing —
which is exactly the state a caller is in after an embed failed post-commit.
Stopping there would make the agent's one natural repair a no-op, so this path
finds blocks of the document that carry no vector under the active fingerprint
and embeds those.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.repositories.vector import EmbedderFingerprintUnresolved
from app.services.block_embeddings import (
    PARENT_TABLE, embed_blocks, resolve_read_fingerprint,
)
from app.services.block_fact_sources import withdraw_document
from app.services.block_pipeline import ingest_document
from app.services.document_ingest import UNCHANGED
from app.services.embedder_registry import child_table
from app.services.events import record_event

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "DocumentTooLarge",
    "PutResult",
    "delete_document",
    "put_document",
]

# An order of magnitude above any plan or ledger. These exist to refuse a
# pathological input, not to shape usage: an unbounded document drives a
# synchronous parse and embed before the call returns, with no analogue of
# `buffer_wait_timeout_seconds` to degrade against.
MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000


class DocumentTooLarge(ValueError):
    """Refused at the door. The message names which bound was hit."""


@dataclass(frozen=True)
class PutResult:
    document_id: str
    outcome: str
    blocks_filed: int
    blocks_embedded: int
    # False only when `outcome == UNCHANGED`: `file_document`'s content-hash
    # gate short-circuits before any row write runs, so a re-filed identical
    # document's explicit `title` (or any other field) is never applied.
    # Every transport this door reaches has to serve this signal identically,
    # which is why it is computed here rather than by each caller.
    title_applied: bool


_BLOCK_IDS = text(
    "SELECT CAST(id AS text) AS id FROM blocks "
    "WHERE document_id = CAST(:document_id AS uuid)"
)

_EXISTING_TITLE = text(
    "SELECT title FROM documents "
    "WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text)"
)

# Mirrors `fact_provenance._STILL_SOURCED` exactly: a fact still has a source
# once its own withdrawn rows are gone, regardless of which kind survives.
_STILL_SOURCED = text("""
    SELECT DISTINCT fact_id
    FROM fact_sources
    WHERE fact_id = ANY(CAST(:ids AS uuid[]))
""")

_FACT_ROWS = text("""
    SELECT CAST(id AS text) AS id, project, expired_at
    FROM knowledge_triples
    WHERE id = ANY(CAST(:ids AS uuid[]))
""")

_DELETE_DOCUMENT = text("DELETE FROM documents WHERE id = CAST(:id AS uuid)")


def _unembedded_sql(fingerprint: str):
    child = child_table(PARENT_TABLE, fingerprint)
    return text(
        f"SELECT CAST(b.id AS text) AS id FROM blocks b "
        f"LEFT JOIN {child} e ON e.block_id = b.id "
        f"WHERE b.document_id = CAST(:document_id AS uuid) AND e.block_id IS NULL"
    )


_FIRST_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


async def _resolve_title(
    session: AsyncSession, *, project: str, uri: str, title: str | None, content: str
) -> str | None:
    """The title to file, resolved so a re-file cannot null a stored one.

    `update_document` and the upsert overwrite `title` wholesale, NULLs
    included, so passing the caller's `None` straight through would erase a
    title a previous call established. Order: what the caller said, then what
    the row already holds, then the document's first heading.

    `documents_repo.DocumentRow` carries no `title` field, so the stored
    value is read directly here rather than through the shared resolver.
    """
    if title:
        return title
    existing_title = (
        await session.execute(_EXISTING_TITLE, {"project": project, "uri": uri})
    ).scalar_one_or_none()
    if existing_title:
        return existing_title
    match = _FIRST_HEADING.search(content)
    return match.group(1) if match else None


async def put_document(
    session: AsyncSession,
    llm,
    *,
    project: str,
    uri: str,
    content: str,
    title: str | None = None,
    source_type: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
    source: str | None = None,
) -> PutResult:
    if len(content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(
            f"content is {len(content)} characters; the bound is "
            f"{MAX_CONTENT_CHARS}"
        )

    resolved_title = await _resolve_title(
        session, project=project, uri=uri, title=title, content=content,
    )

    # `ingest_document` (via `file_document`) opens and RELEASES its own
    # SAVEPOINT before returning, and a released savepoint's writes merge
    # into whatever transaction called it rather than staying discardable
    # on their own. So the block-count refusal below needs its own
    # SAVEPOINT around both the filing and the check: raising out of this
    # `async with` rolls the document row, its blocks, and the
    # `document_filed` event back to before this call, which is what makes
    # a refusal actually leave the document as it was rather than staging
    # an oversized, unembedded document for the caller's next commit.
    async with session.begin_nested():
        filed = await ingest_document(
            session,
            project=project,
            content=content,
            uri=uri,
            source_type=source_type,
            title=resolved_title,
            properties=properties,
            actor=actor,
            source=source,
        )
        if filed.blocks_written > MAX_BLOCKS:
            raise DocumentTooLarge(
                f"document parses to {filed.blocks_written} blocks; the "
                f"bound is {MAX_BLOCKS} blocks"
            )

    await session.commit()

    if filed.outcome == UNCHANGED:
        try:
            fingerprint = await resolve_read_fingerprint(session, llm)
        except EmbedderFingerprintUnresolved:
            # Nothing has ever been embedded on this install, so there is no
            # partition to find gaps in. The next real filing registers one.
            return PutResult(
                document_id=str(filed.document_id), outcome=filed.outcome,
                blocks_filed=filed.blocks_written, blocks_embedded=0,
                title_applied=filed.outcome != UNCHANGED,
            )
        rows = await session.execute(
            _unembedded_sql(fingerprint), {"document_id": str(filed.document_id)}
        )
    else:
        rows = await session.execute(
            _BLOCK_IDS, {"document_id": str(filed.document_id)}
        )
    block_ids = [r.id for r in rows]

    written = 0
    if block_ids:
        result = await embed_blocks(session, llm, block_ids=block_ids)
        # `None` means nothing was embedded and no fingerprint was measured.
        # Report it as zero rather than as success: the caller's whole reason
        # for reading this number is to learn whether its document is
        # findable.
        written = result.written if result is not None else 0
        await session.commit()

    return PutResult(
        document_id=str(filed.document_id),
        outcome=filed.outcome,
        blocks_filed=filed.blocks_written,
        blocks_embedded=written,
        title_applied=filed.outcome != UNCHANGED,
    )


async def delete_document(session: AsyncSession, *, document_id: UUID | str) -> bool:
    """Remove a document and close the provenance window it leaves behind.

    `fact_sources.source_ref` carries no foreign key, so deleting the document
    row alone would leave a fact corroborated by its blocks still counting
    that origin and still sitting at whatever verification rung it earned
    with it. Models `fact_provenance._withdraw`, the memory-kind sibling that
    already solves this: withdraw the block sources, expire any fact that
    survival check finds bare (never a fact still sourced some other way, and
    never one already expired — `expire` is COALESCE-idempotent but a fact
    identically expired twice is still one transition, not two), and emit one
    `sources_changed` event per affected fact so the Tier-C recompute's fast
    arm — not its slow, rare-corruption-backstop reconciliation — is what
    ordinarily reaches it. Neither this function nor `withdraw_document`
    writes `verification_status`: the rung stays the ladder's decision.

    Returns whether the document existed. `False` for a missing document
    without having written anything — `withdraw_document` is a no-op on a
    document with no blocks, which a missing document always is.
    """
    withdrawal = await withdraw_document(session, document_id=document_id)

    if withdrawal.facts_enqueued:
        fact_ids = list(withdrawal.facts_enqueued)
        surviving = {
            str(row) for row in (
                await session.execute(_STILL_SOURCED, {"ids": fact_ids})
            ).scalars().all()
        }
        fact_rows = {
            row["id"]: row for row in (
                await session.execute(_FACT_ROWS, {"ids": fact_ids})
            ).mappings().all()
        }
        triples = KnowledgeTripleRepository(session)
        for fact_id in fact_ids:
            row = fact_rows.get(fact_id)
            if row is None:
                # The fact vanished by some other route between the withdrawal
                # and this read; nothing to expire and nothing to enqueue for.
                continue
            if fact_id not in surviving and row["expired_at"] is None:
                await triples.expire(UUID(fact_id))
            await record_event(
                session,
                event_type="sources_changed",
                object_type="fact",
                object_id=UUID(fact_id),
                project=row["project"],
                # The document, not the block: origin for a block source is
                # the document (block_fact_sources.py's own rule), so this is
                # the spelling that names what actually moved. The drain
                # itself reads only `payload["fact_id"]` — see
                # `verification_recompute._drain_sources_changed` — so this
                # key is for a human tracing one fact's evidence history
                # across both spellings, the same role `memory_id` plays on
                # the sibling payload.
                payload={"fact_id": fact_id, "document_id": str(document_id)},
            )

    result = await session.execute(_DELETE_DOCUMENT, {"id": str(document_id)})
    return result.rowcount > 0
