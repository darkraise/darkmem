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
from app.services.block_query import BlockQueryService
from app.services.document_ingest import UNCHANGED
from app.services.embedder_registry import child_table
from app.services.events import record_event

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "BlockRow",
    "DocumentTooLarge",
    "OutlineNode",
    "PutResult",
    "SectionHit",
    "delete_document",
    "document_blocks",
    "document_outline",
    "put_document",
    "search_sections",
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

# Recursive walk from each hit up to its document root, resolved in one
# round trip rather than one query per ancestor. `blocks.parent_id` is a
# plain nullable UUID column with no cycle constraint, and a recursive CTE
# with no depth bound loops forever against a cyclic parent chain -- rather
# than de-duplicate rows (a plain UNION still can't dedupe here, since
# `depth` makes every row of a cycle distinct), the WHERE clause below caps
# the walk. The cap is fetched one hop past the guaranteed range on purpose
# (`up.depth < :limit` lets depth reach exactly `_ANCESTOR_DEPTH_LIMIT`, one
# more than the guaranteed 0..limit-1 range): that sentinel row is how
# `_heading_path` tells "the tree ends here" from "the tree keeps going and
# was cut off", instead of returning a truncated path that looks complete.
_ANCESTOR_DEPTH_LIMIT = 64

_ANCESTORS = text(
    """
    WITH RECURSIVE up AS (
        SELECT id, parent_id, text, type, 0 AS depth
        FROM blocks WHERE id = ANY(CAST(:ids AS uuid[]))
        UNION ALL
        SELECT b.id, b.parent_id, b.text, b.type, up.depth + 1
        FROM blocks b JOIN up ON b.id = up.parent_id
        WHERE up.depth < CAST(:limit AS integer)
    )
    SELECT CAST(id AS text) AS id, CAST(parent_id AS text) AS parent_id,
           text, type, depth
    FROM up
    """
)

_DOCUMENT_TITLES = text(
    "SELECT CAST(id AS text) AS id, title FROM documents "
    "WHERE id = ANY(CAST(:ids AS uuid[]))"
)


@dataclass(frozen=True)
class SectionHit:
    """A ranked block plus where it sits in its document's heading tree.

    Carries every `block_query.BlockHit` field, `id_kind`/`layer` included:
    `block_query.py`'s own docstring says those two labels ride the row
    rather than the envelope specifically so a row that travels alone into
    "a future document surface" — this one — still carries what kind of
    thing it is. On top of that this adds `title` (the owning document's),
    `heading_path` (outermost to innermost, headings only; a hit under no
    heading gets `()`), and `path_truncated` (True when the ancestor walk
    hit its depth cap before reaching a root — the returned path is real as
    far as it goes, never invented, but may be missing outer levels).
    `block_query.py` cannot resolve any of this itself: it is under a
    structural test keeping the block channel out of the memory
    composition, so the ancestry walk lives here instead.
    """

    block_id: str
    document_id: str
    project: str
    uri: str | None
    title: str | None
    heading_path: tuple[str, ...]
    path_truncated: bool
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None
    score: float
    id_kind: str
    layer: str


def _heading_path(block_id: str, by_id: dict) -> tuple[tuple[str, ...], bool]:
    """Walk `by_id` from `block_id` up to the document root.

    Bounded by an explicit iteration count, not only by the `seen` cycle
    guard below: a `for` loop over a fixed `range` terminates on its own
    even if a future edit broke `seen` entirely, where a `while ... not in
    seen` loop alone would not -- it would spin the event loop forever on
    that regression, since nothing here awaits. (Proving the `seen` guard
    load-bearing required an OS-level kill of exactly that hang; the `for`
    bound means a future regression fails as a wrong return value instead.)

    Returns `(path, truncated)`. `truncated` is True when the walk stopped
    without reaching a genuine root: either the sentinel row one hop past
    `_ANCESTOR_DEPTH_LIMIT` (see `_ANCESTORS`), or a repeated id (a cycle in
    `blocks.parent_id`, which carries no constraint against one).
    """
    path: list[str] = []
    seen: set[str] = set()
    node = by_id.get(block_id)
    truncated = False
    for _ in range(_ANCESTOR_DEPTH_LIMIT + 2):
        if node is None:
            break
        if node["id"] in seen or node["depth"] >= _ANCESTOR_DEPTH_LIMIT:
            truncated = True
            break
        seen.add(node["id"])
        if node["type"] == "heading":
            path.append(node["text"] or "")
        parent_id = node["parent_id"]
        node = by_id.get(parent_id) if parent_id else None
    else:
        # Unreachable given the depth check above -- every chain hits either
        # `node is None` or the sentinel's depth check within the bound --
        # but a hard ceiling that could silently pass unnoticed is worse
        # than one that announces it.
        truncated = True
    return tuple(reversed(path)), truncated


async def search_sections(
    session: AsyncSession,
    llm,
    *,
    query: str,
    project: str,
    limit: int = 20,
    document_id: str | None = None,
) -> list[SectionHit]:
    """Rank blocks, then resolve each hit's heading path.

    Read-only: this function commits nothing and never opens a savepoint,
    unlike `put_document` (commits internally) or `delete_document` (relies
    on its caller). It runs entirely inside whatever transaction the caller
    already holds.
    """
    hits = await BlockQueryService(session, llm).search(
        query, project=project, limit=limit, document_id=document_id,
    )
    if not hits:
        return []

    rows = (await session.execute(
        _ANCESTORS, {"ids": [h.block_id for h in hits], "limit": _ANCESTOR_DEPTH_LIMIT}
    )).mappings().all()
    # A cycle in `blocks.parent_id` makes the recursive CTE revisit the same
    # id at ever-increasing depths (UNION ALL does not dedupe, and `depth`
    # makes every visit a distinct row), so a plain `{r["id"]: r for r in
    # rows}` would keep whichever occurrence Postgres happens to emit last --
    # an implementation-defined order this file must not depend on. Keeping
    # the shallowest occurrence per id instead is deterministic and is also
    # the only one that means anything: it is the nearest ancestor actually
    # reachable from the hit, the same single answer a non-cyclic tree would
    # have given regardless of row order.
    by_id: dict = {}
    for row in rows:
        existing = by_id.get(row["id"])
        if existing is None or row["depth"] < existing["depth"]:
            by_id[row["id"]] = row

    titles = {
        r["id"]: r["title"]
        for r in (await session.execute(
            _DOCUMENT_TITLES, {"ids": list({h.document_id for h in hits})},
        )).mappings().all()
    }

    results = []
    for h in hits:
        heading_path, truncated = _heading_path(h.block_id, by_id)
        results.append(SectionHit(
            block_id=h.block_id,
            document_id=h.document_id,
            project=h.project,
            uri=h.uri,
            title=titles.get(h.document_id),
            heading_path=heading_path,
            path_truncated=truncated,
            type=h.type,
            text=h.text,
            order_index=h.order_index,
            char_span=h.char_span,
            score=h.score,
            id_kind=h.id_kind,
            layer=h.layer,
        ))
    return results


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


@dataclass(frozen=True)
class OutlineNode:
    block_id: str
    level: int
    text: str
    order_index: int | None


@dataclass(frozen=True)
class BlockRow:
    block_id: str
    type: str | None
    text: str
    order_index: int | None
    char_span: tuple[int, int] | None


_OUTLINE = text(
    """
    SELECT CAST(id AS text) AS id, order_index, text,
           COALESCE((properties->>'level')::int, 1) AS level
    FROM blocks
    WHERE document_id = CAST(:document_id AS uuid) AND type = 'heading'
    ORDER BY order_index
    """
)


async def document_outline(
    session: AsyncSession, *, document_id: str
) -> list[OutlineNode]:
    """The heading tree for a document: block id, level and heading text —
    never a paragraph, list, code or quote block's text.

    A query over the block tree the parser already built. No model call, and
    deliberately not `document_summary`, which stays on-demand and unbadged
    where it is. Read-only: commits nothing and opens no savepoint, same
    posture as `search_sections`; it runs entirely inside whatever
    transaction the caller already holds.
    """
    rows = (await session.execute(
        _OUTLINE, {"document_id": document_id}
    )).mappings().all()
    return [
        OutlineNode(
            block_id=r["id"], level=r["level"], text=r["text"] or "",
            order_index=r["order_index"],
        )
        for r in rows
    ]


_BLOCKS = """
    SELECT CAST(id AS text) AS id, type, text, order_index,
           lower(char_span) AS span_start, upper(char_span) AS span_end
    FROM blocks
    WHERE document_id = CAST(:document_id AS uuid)
      {clause}
    ORDER BY order_index
"""


async def document_blocks(
    session: AsyncSession, *, document_id: str, block_ids: list[str] | None = None
) -> list[BlockRow]:
    """The document's blocks, in document order — every one when
    `block_ids` is `None`, or only the ids named in `block_ids` (the
    drill-down after an outline) when it is not — including an explicit `[]`,
    which names zero blocks and returns zero, never "no filter". `block_ids`
    scopes strictly: a row not in the list is excluded even if it belongs to
    this document, and a listed id from another document never appears
    because the `document_id` predicate applies either way.

    Read-only: commits nothing and opens no savepoint, same posture as
    `search_sections` and `document_outline`; it runs entirely inside
    whatever transaction the caller already holds.
    """
    clause = "AND id = ANY(CAST(:ids AS uuid[]))" if block_ids is not None else ""
    params: dict = {"document_id": document_id}
    if block_ids is not None:
        params["ids"] = block_ids
    rows = (await session.execute(
        text(_BLOCKS.format(clause=clause)), params
    )).mappings().all()
    return [
        BlockRow(
            block_id=r["id"], type=r["type"], text=r["text"] or "",
            order_index=r["order_index"],
            char_span=(
                (r["span_start"], r["span_end"])
                if r["span_start"] is not None and r["span_end"] is not None
                else None
            ),
        )
        for r in rows
    ]
