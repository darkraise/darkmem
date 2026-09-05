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

from app.repositories.documents import resolve_by_id, resolve_by_uri
from app.services.block_embeddings import (
    PARENT_TABLE, ensure_partition, embed_blocks, resolve_active_fingerprint,
)
from app.services.block_pipeline import ingest_document
from app.services.block_query import BlockQueryService
from app.services.document_ingest import UNCHANGED
from app.services.embedder_registry import child_table

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "SEARCH_DEFAULT_LIMIT",
    "SEARCH_MAX_LIMIT",
    "BlockRow",
    "DocumentTargetUnresolved",
    "DocumentTooLarge",
    "OutlineNode",
    "PutResult",
    "SectionHit",
    "delete_document",
    "document_blocks",
    "document_content",
    "document_outline",
    "put_document",
    "resolve_document_id",
    "resolve_document_target",
    "search_sections",
]

# An order of magnitude above any plan or ledger. These exist to refuse a
# pathological input, not to shape usage: an unbounded document drives a
# synchronous parse and embed before the call returns, with no analogue of
# `buffer_wait_timeout_seconds` to degrade against.
MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000

# The section-search page, named here rather than on either door: the REST
# body model and the MCP tool's clamp are two enforcement sites for one bound,
# and two copies of one tuning constant drift apart exactly as the RRF constant
# already did.
SEARCH_DEFAULT_LIMIT = 20
SEARCH_MAX_LIMIT = 100


class DocumentTooLarge(ValueError):
    """Refused at the door. The message names which bound was hit."""


class DocumentTargetUnresolved(ValueError):
    """Nothing a caller named resolves to a document that exists."""


async def resolve_document_id(
    session: AsyncSession, *, project: str, uri: str
) -> str | None:
    """The id of the document filed at `(project, uri)`, or `None`.

    Read-only: commits nothing and opens no savepoint, same posture as
    `search_sections`.
    """
    row = await resolve_by_uri(session, project=project, uri=uri)
    return None if row is None else str(row.id)


async def resolve_document_target(
    session: AsyncSession,
    *,
    document_id: str | UUID | None = None,
    project: str | None = None,
    uri: str | None = None,
) -> str:
    """The document a caller named, by id or by `(project, uri)`.

    One producer for both doors and for both addressing forms, because the
    refusals are the part that must not drift. Naming nothing, naming a uri
    nobody filed and naming an id no document carries are the same answer to
    a caller, and a verb that met any of them with an empty outline or an
    empty block list would be reporting a document that does not exist as one
    that exists and is empty -- a distinction this door's siblings already
    draw (`get_document_summary`, and every 404 below it).

    Raises `DocumentTargetUnresolved` rather than returning `None` so no read
    can run against an id nothing confirmed. Read-only: commits nothing and
    opens no savepoint.
    """
    if document_id is not None:
        try:
            resolved = UUID(str(document_id))
        except (ValueError, AttributeError):
            raise DocumentTargetUnresolved(
                f"not a document id: {document_id}"
            ) from None
        if await resolve_by_id(session, resolved) is None:
            raise DocumentTargetUnresolved("document not found")
        return str(resolved)

    if project and uri:
        found = await resolve_document_id(session, project=project, uri=uri)
        if found is None:
            raise DocumentTargetUnresolved(
                f"no document is filed at uri {uri!r} in project {project!r}"
            )
        return found

    raise DocumentTargetUnresolved(
        "name a document: pass document_id, or both project and uri"
    )


# documents.properties key recording which ingest direction owns the row
# (spec §8.2). Absent, or any other value, means content-first -- every
# document ever filed through put. "blocks" means the block verbs are
# authoritative and `content` is a serialisation of their tree.
#
# Server-owned: neither door accepts caller properties on put, and the block
# verbs merge this key with jsonb `||` rather than writing properties
# wholesale, so a caller can neither set nor clear it.
DIRECTION_KEY = "ingest_direction"
BLOCK_FIRST = "blocks"

_DIRECTION_SQL = text(
    "SELECT properties->>'ingest_direction' FROM documents "
    "WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text)"
)

_LOCK_DOCUMENT_BY_URI = text(
    "SELECT id FROM documents "
    "WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text) "
    "FOR UPDATE"
)


class DocumentIsBlockFirst(ValueError):
    """put refused: this document is owned by the block verbs (spec §8.2).

    A content push over an editing session is a silent overwrite -- the put
    would strip every block the editor placed and rewrite the content it was
    serialising from.
    """


class DocumentNotConvertible(ValueError):
    """block verb refused: this content-first document contains source the
    block model does not represent, so converting it would regenerate
    `content` without it (review M-2).

    Spec §4.5 promises generated-region markers survive in the stored raw
    content and §8.2 promises a content-first document's content is never
    regenerated. Converting lossily would break both silently, on the corpus
    this programme exists to hold. Refusing is the honest outcome until the
    parser represents those shapes.
    """


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
    # None only when `outcome == UNCHANGED`: the change gate short-circuits
    # before any parse, so nothing was measured this filing (see
    # `DocumentIngest`). Counts, not refusals -- an oversized block embeds
    # truncated, and this is the loud report invariant 14 asks for in place
    # of a degradation the filing would otherwise hide behind a 201.
    oversized_blocks: int | None = None
    largest_block_chars: int | None = None
    # The hash the document now holds, echoed so a caller can precondition
    # its next edit on it. Without this no wire surface served one, and
    # expected_hash would ship unusable -- a caller would have to sha256 the
    # content itself and know the algorithm.
    content_hash: str | None = None


_BLOCK_IDS = text(
    "SELECT CAST(id AS text) AS id FROM blocks "
    "WHERE document_id = CAST(:document_id AS uuid)"
)

_EXISTING_TITLE = text(
    "SELECT title FROM documents "
    "WHERE project = CAST(:project AS text) AND uri = CAST(:uri AS text)"
)

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
    without reaching a genuine root, on any of three routes: the sentinel row
    one hop past `_ANCESTOR_DEPTH_LIMIT` (see `_ANCESTORS`), a repeated id (a
    cycle in `blocks.parent_id`, which carries no constraint against one), or
    the iteration bound running out with neither of those having fired -- see
    the `else` below, which is reachable rather than defensive.
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
        # Reached whenever the depth check cannot fire: every hit block is a
        # seed of the ancestors CTE at depth 0 and `by_id` keeps the
        # shallowest occurrence, so a parent chain whose every block is
        # itself a search hit carries depth 0 throughout. A chain longer than
        # the bound then exhausts the range with no root and no sentinel, and
        # a hard ceiling that passed unnoticed would serve a cut-off path
        # looking complete.
        truncated = True
    return tuple(reversed(path)), truncated


async def search_sections(
    session: AsyncSession,
    llm,
    *,
    query: str,
    project: str,
    limit: int = SEARCH_DEFAULT_LIMIT,
    document_id: str | None = None,
) -> list[SectionHit]:
    """Rank blocks, then resolve each hit's heading path.

    `document_id` confines the search to one document and is resolved
    through `resolve_document_target` before the probe, so an id naming no
    document refuses instead of ranking an empty corpus. Passing it straight
    into the SQL filter -- which is what this did until the two doors' verbs
    were reconciled -- makes "that document is gone" and "nothing in it
    matched" the same empty list, the distinction every other verb keyed on
    a document already draws, and sends a malformed id to asyncpg's uuid
    cast as an unhandled database error besides.

    Read-only: this function commits nothing and never opens a savepoint,
    unlike `put_document` (commits internally) or `delete_document` (relies
    on its caller). It runs entirely inside whatever transaction the caller
    already holds.
    """
    if document_id is not None:
        document_id = await resolve_document_target(
            session, document_id=document_id,
        )

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
    expected_hash: str | None = None,
    force_reparse: bool = False,
) -> PutResult:
    if len(content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(
            f"content is {len(content)} characters; the bound is "
            f"{MAX_CONTENT_CHARS}"
        )

    # Review M-3: the refusal is taken under a row lock, not before one. A
    # SELECT ahead of the savepoint is check-then-act -- the block verbs can
    # convert the document between the read and this put's own UPDATE, which
    # writes properties wholesale and would erase `ingest_direction` while
    # strip_blocks deletes the rows an editing session just placed. That is
    # the same race increment 3's compare-and-set closed, and "unconditional"
    # is weaker here rather than stronger: a CAS at least fails loudly.
    #
    # A brand-new document has no row to lock, and that is correct rather
    # than a hole: there is nothing to convert and nothing to overwrite.
    await session.execute(_LOCK_DOCUMENT_BY_URI, {"project": project, "uri": uri})
    direction = (
        await session.execute(_DIRECTION_SQL, {"project": project, "uri": uri})
    ).scalar_one_or_none()
    if direction == BLOCK_FIRST:
        raise DocumentIsBlockFirst(
            f"the document at uri {uri!r} in project {project!r} is "
            "block-first: its content is owned by the block verbs, and a "
            "content push would silently overwrite an editing session. "
            "Edit it through the block verbs, or delete and re-file it."
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
            expected_hash=expected_hash,
            force_reparse=force_reparse,
        )
        if filed.blocks_written > MAX_BLOCKS:
            raise DocumentTooLarge(
                f"document parses to {filed.blocks_written} blocks; the "
                f"bound is {MAX_BLOCKS} blocks"
            )

    await session.commit()

    if filed.outcome == UNCHANGED:
        # Resolved from a real embed call, never a data probe (T-doc-door.6
        # review, round 3): this is the identical chicken-and-egg the sweep
        # had — finding which blocks still need embedding requires already
        # knowing the fingerprint, and a data probe answers "which live
        # fingerprint holds data", which is biased toward a stale, already-
        # complete partition after a rotation rather than the active-but-
        # still-empty one retrieval actually reads. See
        # `block_embeddings.resolve_active_fingerprint`'s docstring.
        #
        # Cost, stated plainly (round 4): this spends one embed call on
        # EVERY `unchanged` re-push, unconditionally — including a document
        # that is already fully embedded and has nothing to repair, where
        # this used to spend a cheap database probe instead. A caller
        # re-pushing N unchanged documents in a pass now makes N embedding
        # calls. The sweep pays this once an hour; this door pays it once
        # per request.
        fingerprint = await resolve_active_fingerprint(llm)
        await ensure_partition(session, fingerprint)
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
        if result is not None and filed.outcome == UNCHANGED and result.fingerprint != fingerprint:
            # Mirrors `block_embedding_refresh`'s own guard (T-doc-door.6
            # review, round 4): `fingerprint` above and `result.fingerprint`
            # here are two separate real embed calls, and the unembedded-
            # blocks count in `rows` was computed against the FIRST one. A
            # rotation landing between them would silently write the batch
            # under a second partition while reporting a count that was
            # never actually verified against it. Refusing is the same
            # asymmetry closed on the sweep's side; only the `unchanged`
            # branch resolves a fingerprint ahead of the write, so only it
            # can race this way.
            raise RuntimeError(
                f"document_door: resolved fingerprint {fingerprint!r} for "
                f"this unchanged repair but the batch embed call wrote "
                f"under {result.fingerprint!r} instead — the active "
                "embedder's configuration changed between the two calls "
                "within this one request. Refusing rather than reporting a "
                "repair count computed against one partition and written "
                "into another."
            )
        written = result.written if result is not None else 0
        await session.commit()

    return PutResult(
        document_id=str(filed.document_id),
        outcome=filed.outcome,
        blocks_filed=filed.blocks_written,
        blocks_embedded=written,
        title_applied=filed.outcome != UNCHANGED,
        oversized_blocks=filed.oversized_blocks,
        largest_block_chars=filed.largest_block_chars,
        content_hash=filed.content_hash,
    )


async def delete_document(session: AsyncSession, *, document_id: UUID | str) -> bool:
    """Remove a document and, by cascade, its blocks and their vectors.

    There is no provenance to close behind it: nothing mints a `fact_sources`
    row from a block, so a document's blocks corroborate no fact and deleting
    one cannot leave a fact standing on evidence that no longer exists. The
    withdraw-then-expire pass this function used to run was the withdrawal
    half of a bridge whose attaching half never had a caller, which made it a
    permanent no-op; it went with the bridge.

    Returns whether the document existed. `False` for a missing document
    without having written anything.
    """
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
    # The enclosing block, or None at the document's top level. The parser
    # makes a nested list item's parent the enclosing *item* -- the list
    # wrapper is transparent and mints no block -- so a renderer rebuilds the
    # tree from this column alone rather than inferring depth from anything.
    parent_id: str | None = None
    # A heading's level, a table's header and column alignments. Served
    # because `text` alone cannot render a table through a real table
    # component, and cannot tell a level-2 heading from a level-4. It does
    # NOT carry a list item's marker: `parse_markdown` writes `None` for
    # every list block, so ordered-vs-bullet is not on this surface at all.
    properties: dict | None = None
    # The block's own markdown source, sliced server-side from the document's
    # stored content by this block's span. `text` is marker-stripped, so it is
    # NOT the source: a heading's text is "Foo" where its source is "## Foo".
    # An editor holding `text` is editing a different string from the one
    # stored, which is the conversion step the block editor exists to avoid.
    # None when the document has no stored content or the block has no span.
    source: str | None = None


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


_DOCUMENT_CONTENT = text(
    "SELECT content FROM documents WHERE id = CAST(:document_id AS uuid)"
)


async def document_content(session: AsyncSession, *, document_id: str) -> str | None:
    """The document's verbatim source of record.

    The exact text ``put`` filed -- frontmatter and fences included -- which is
    also what every block's ``char_span`` indexes into. None for a document
    filed from a non-text source, which has no text form to return.

    Read-only, the same posture as ``document_blocks``: commits nothing and
    opens no savepoint. Deliberately its own statement rather than a column on
    the list or resolve reads: the source can be a megabyte, and only this
    caller asked for it.
    """
    return (await session.execute(
        _DOCUMENT_CONTENT, {"document_id": document_id}
    )).scalar_one_or_none()


# The join carries the document's content so `source` is sliced server-side.
# Without it every caller would fetch the whole document and slice it itself,
# which makes an editor's per-block read depend on a second, much larger one.
_BLOCKS = """
    SELECT CAST(b.id AS text) AS id, b.type, b.text, b.order_index,
           CAST(b.parent_id AS text) AS parent_id,
           b.properties,
           lower(b.char_span) AS span_start, upper(b.char_span) AS span_end,
           substring(d.content
                     FROM lower(b.char_span) + 1
                     FOR upper(b.char_span) - lower(b.char_span)) AS source
    FROM blocks b
    JOIN documents d ON d.id = b.document_id
    WHERE b.document_id = CAST(:document_id AS uuid)
      {clause}
    ORDER BY b.order_index
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
    # Qualified now that the statement joins: a bare `id` is ambiguous.
    clause = "AND b.id = ANY(CAST(:ids AS uuid[]))" if block_ids is not None else ""
    params: dict = {"document_id": document_id}
    if block_ids is not None:
        params["ids"] = block_ids
    rows = (await session.execute(
        text(_BLOCKS.format(clause=clause)), params
    )).mappings().all()
    return [
        BlockRow(
            block_id=r["id"], type=r["type"], text=r["text"] or "",
            order_index=r["order_index"], parent_id=r["parent_id"],
            char_span=(
                (r["span_start"], r["span_end"])
                if r["span_start"] is not None and r["span_end"] is not None
                else None
            ),
            properties=r["properties"],
            source=r["source"],
        )
        for r in rows
    ]
