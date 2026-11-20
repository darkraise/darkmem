"""The document door's write half (spec 2026-08-23).

**Embed after commit, never inside the filing.** First contact with an unknown
fingerprint runs child-table DDL through `embedder_registry.ensure_registered`,
which commits on this session; embedding inside the filing transaction would make the
filing non-rollback-able. So: file, commit, then embed.

**The `unchanged` path still embeds.** `ingest_document` returns UNCHANGED
before touching any block, so a re-push of an identical file files nothing —
which is exactly the state a caller is in after an embed failed post-commit.
Stopping there would make the agent's one natural repair a no-op, so this path
finds blocks of the document that carry no vector under the active fingerprint
and embeds those.

**A re-file embeds only changed text.** Inside the filing, each new block whose
text matches an old block's takes that block's vector under the active
fingerprint, so the embed after commit sends only the blocks that changed.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.memory import document_tags
from app.repositories.documents import (
    DocumentIsBlockFirst,
    resolve_by_id,
    resolve_by_uri,
)
from app.repositories.relational import PostgresTagRepository
from app.services.block_embeddings import (
    PARENT_TABLE, active_fingerprint, embed_blocks,
)
from app.services.block_pipeline import ingest_document
from app.services.block_query import BlockQueryService
from app.services.block_serializer import slice_source
from app.services.document_ingest import (
    UNCHANGED, DocumentHashConflict, DocumentTooLarge, DocumentUriConflict,
)
from app.services.embedder_registry import child_table, ensure_registered
from app.services.events import record_event

logger = logging.getLogger(__name__)

__all__ = [
    "DOCUMENTS_DELETED_EVENT",
    "DOCUMENT_UPDATED_EVENT",
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "SEARCH_DEFAULT_LIMIT",
    "SEARCH_MAX_LIMIT",
    "BlockRow",
    "DocumentIsBlockFirst",
    "DocumentJournalWriteFailed",
    "DocumentMirrorOwned",
    "DocumentNothingToChange",
    "DocumentTargetUnresolved",
    "DocumentTooLarge",
    "DocumentUriConflict",
    "OutlineNode",
    "PutResult",
    "SectionHit",
    "delete_document",
    "delete_documents",
    "document_blocks",
    "document_content",
    "document_hash",
    "document_outline",
    "put_document",
    "rename_documents",
    "resolve_document_id",
    "resolve_document_target",
    "search_sections",
    "update_document_metadata",
]

# An order of magnitude above any plan or ledger. These exist to refuse a
# pathological input, not to shape usage: an unbounded document drives a
# synchronous parse and embed before the call returns, with no analogue of
# `wait_process`'s ten-second bound to degrade against.
MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000

DOCUMENT_UPDATED_EVENT = "document_updated"
DOCUMENTS_DELETED_EVENT = "documents_deleted"

# Only the two constants below are ever interpolated into the UPDATE; every
# caller-supplied value is bound.
_PIN_ASSIGNMENT = {True: "pinned_at = now()", False: "pinned_at = NULL"}

# The section-search page, named here rather than on either door: the REST
# body model and the MCP tool's clamp are two enforcement sites for one bound,
# and two copies of one tuning constant drift apart exactly as the RRF constant
# already did.
SEARCH_DEFAULT_LIMIT = 20
SEARCH_MAX_LIMIT = 100


class DocumentTargetUnresolved(ValueError):
    """Nothing a caller named resolves to a document that exists."""


class DocumentJournalWriteFailed(RuntimeError):
    """A bulk delete could not be journalled, so it must not happen.

    `record_event` degrades loudly and never raises, which is right for a
    capture: a lost log line must not fail an ingest that can simply be
    repeated. It returns whether the row landed so that a caller for whom the
    row is not a log line but *is* the record can take the opposite contract
    and make the write and its row atomic -- see the strict-caller paragraph
    of CLAUDE.md's "Events journal" section for that contract and who holds
    it.

    A subtree delete is that case with more force than a capture. It is
    unrecoverable, it cascades blocks and their vectors, and over MCP the
    event's `api_key_id` is the only thing that says who ran it. Failing
    closed costs the caller a retry; failing open loses the audit for good.

    A type of its own rather than the vault's `JournalWriteFailed`, which the
    other holders raise: that name lives on the knowledge-triple repository,
    and this module is a block-channel one firewalled from the vault, so
    sharing it would mean importing that module for an exception and nothing
    else. The contract those callers hold is the shape, not the type.
    """


class DocumentNothingToChange(ValueError):
    """The call named no change, so writing it would journal an empty edit.

    `events` is append-only, so a metadata call naming no field and a subtree
    rename whose new prefix equals the old one leave a permanent row saying an
    edit happened when none did. Refusing is what keeps the journal a record
    of edits rather than of calls.
    """


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


class DocumentMirrorOwned(DocumentNotConvertible):
    """Block verb refused: the dr-forge mirror owns this document.

    Registers and plans (`superpowers/registers/`, `superpowers/plans/`) reach
    darkmem as content puts from the mirror, and the progress board edits
    registers the same way. Converting one to block-first would refuse every
    later put and strand the mirror (spec 2026-10-13 §2.5). A subclass, so
    both doors already map it: REST to 422, MCP to `not_convertible`.
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
    api_key_id: UUID | None = None,
    source: str | None = None,
    expected_hash: str | None = None,
    force_reparse: bool = False,
    embed_inline: bool = True,
) -> PutResult:
    """File a document, commit, then embed its blocks.

    With `embed_inline=False` it returns once the filing commits and embeds
    nothing, so `llm` may be None: `block_embedding_refresh` embeds the new
    blocks on its next pass, as it does for page writes (spec 2026-10-13
    §2.4). An embedder failure then cannot fail an edit that already landed.
    """
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

    carry_fingerprint = None
    if embed_inline:
        try:
            carry_fingerprint = await active_fingerprint(llm)
        except Exception:  # noqa: BLE001 - the embed after commit reports it
            logger.warning(
                "document_door: no active fingerprint before filing %s; "
                "re-embedding every block", uri, exc_info=True,
            )

    # The block-count refusal is raised inside the filing's own SAVEPOINT,
    # before any block insert, so it rolls the row and its journal back
    # rather than staging an oversized document for the caller's next commit.
    filed = await ingest_document(
        session,
        project=project,
        content=content,
        uri=uri,
        source_type=source_type,
        title=resolved_title,
        properties=properties,
        actor=actor,
        api_key_id=api_key_id,
        source=source,
        expected_hash=expected_hash,
        force_reparse=force_reparse,
        carry_fingerprint=carry_fingerprint,
        max_blocks=MAX_BLOCKS,
    )

    await session.commit()

    if not embed_inline:
        return PutResult(
            document_id=str(filed.document_id),
            outcome=filed.outcome,
            blocks_filed=filed.blocks_written,
            blocks_embedded=0,
            title_applied=filed.outcome != UNCHANGED,
            oversized_blocks=filed.oversized_blocks,
            largest_block_chars=filed.largest_block_chars,
            content_hash=filed.content_hash,
        )

    fingerprint = carry_fingerprint
    if fingerprint is None and filed.outcome == UNCHANGED:
        fingerprint = await active_fingerprint(llm)
    if fingerprint is not None:
        # Never a data probe: after a rotation a probe answers the stale,
        # complete partition rather than the empty one retrieval reads.
        await ensure_registered(session, fingerprint)
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
            # The gaps were listed under `fingerprint`; a rotation between
            # that and the embed wrote the repair under another partition, so
            # the repair count would describe a partition it never verified.
            # A changed filing has already landed and the sweep fills what a
            # rotation stranded, so only the repair refuses.
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


async def _set_document_tags(
    session: AsyncSession, document_id: UUID | str, names: list[str],
) -> None:
    """Replace the document's tag set with `names`.

    Private, and deliberately so: it takes no lock of its own. The `FOR
    UPDATE` on the document row that makes a concurrent replacement serialise
    lives in `update_document_metadata`, its one caller, so a second caller
    reaching this directly would reopen that race.

    A present list replaces rather than merges, because a merge-only verb
    cannot remove a tag. Names resolve through the shared tag repository so
    `tag_category` and the name bound apply identically on both doors, and so
    a document links the same `tags` row a memory carrying that name would.
    """
    doc_id = document_id if isinstance(document_id, UUID) else UUID(str(document_id))
    repo = PostgresTagRepository(session)
    tag_ids: list[int] = []
    for name in dict.fromkeys(names):
        tag = await repo.get_or_create(name)
        tag_ids.append(tag.id)

    await session.execute(
        document_tags.delete().where(document_tags.c.document_id == doc_id)
    )
    if tag_ids:
        await session.execute(
            document_tags.insert(),
            [{"document_id": doc_id, "tag_id": tag_id} for tag_id in tag_ids],
        )
    await session.flush()


async def _refuse_unmatched_update(
    session: AsyncSession, doc_id: UUID, expected_hash: str | None
) -> None:
    """An UPDATE that matched no row named a missing document or lost its hash
    precondition; one read tells which. The hash it reports may have moved
    again since, which only makes the refusal name the newer winner."""
    current = (await session.execute(
        text("SELECT content_hash FROM documents WHERE id = CAST(:id AS uuid)"),
        {"id": str(doc_id)},
    )).first()
    if current is None or expected_hash is None:
        raise DocumentTargetUnresolved(f"document not found: {doc_id}")
    raise DocumentHashConflict(
        document_id=doc_id, expected_hash=expected_hash, current_hash=current[0],
    )


async def update_document_metadata(
    session: AsyncSession,
    *,
    document_id: UUID | str,
    title: str | None = None,
    uri: str | None = None,
    pinned: bool | None = None,
    tags: list[str] | None = None,
    expected_hash: str | None = None,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> None:
    """Write only the fields the caller named.

    An unnamed field emits no assignment at all rather than writing NULL over
    its column, so renaming a document cannot silently unpin it or strip its
    tags.

    `project` is deliberately not a field: moving a document between spaces is
    not a rename, and allowing it here would let one call cross the boundary
    the personal space rests on.

    A call naming no field at all is refused rather than journalled: `events`
    is append-only, so it would leave a permanent `{"fields": []}` row saying
    an edit happened when none did. `expected_hash` is a precondition, not a
    field, so a call naming only it is refused the same way.

    `expected_hash` is a compare-and-set on `content_hash`, carried in the
    writer's own statement (the UPDATE's WHERE, or the tags-only path's
    locked read), never read and compared first: a filing landing between a
    separate check and the move would be silently carried along.
    """
    if title is None and uri is None and pinned is None and tags is None:
        raise DocumentNothingToChange(
            "name at least one of title, uri, pinned or tags"
        )
    doc_id = document_id if isinstance(document_id, UUID) else UUID(str(document_id))
    assignments: list[str] = []
    params: dict = {"id": str(doc_id)}
    if title is not None:
        assignments.append("title = CAST(:title AS text)")
        params["title"] = title
    if uri is not None:
        assignments.append("uri = CAST(:uri AS text)")
        params["uri"] = uri
    if pinned is not None:
        assignments.append(_PIN_ASSIGNMENT[pinned])

    if assignments:
        hash_guard = ""
        if expected_hash is not None:
            hash_guard = (
                " AND content_hash IS NOT DISTINCT FROM CAST(:expected_hash AS text)"
            )
            params["expected_hash"] = expected_hash
        try:
            # ux_documents_project_uri is what refuses a collision, and a
            # failed statement aborts the transaction it runs in -- so this
            # runs in a SAVEPOINT, leaving the caller's transaction usable
            # after the refusal rather than poisoned by it. RETURNING folds
            # the rowcount check and the project lookup into the same round
            # trip, and the UPDATE's own row lock is what serialises this
            # against a concurrent _set_document_tags on the same document.
            async with session.begin_nested():
                project = (await session.execute(
                    text(
                        f"UPDATE documents SET {', '.join(assignments)} "
                        f"WHERE id = CAST(:id AS uuid){hash_guard} RETURNING project"
                    ),
                    params,
                )).scalar_one_or_none()
        except IntegrityError as exc:
            raise DocumentUriConflict(uri) from exc
        if project is None:
            await _refuse_unmatched_update(session, doc_id, expected_hash)
    else:
        # No column assignment means a tags-only or entirely empty call, so
        # nothing above confirmed the row exists or locked it. Both matter
        # here: the lock is what makes a concurrent _set_document_tags
        # replace rather than race (`put_document` and `block_verbs._mutate`
        # already serialise on this row the same way), and the existence
        # check is what stops a phantom `document_updated` event for an id
        # nobody ever filed -- `events` is append-only, so that row would
        # never be undone.
        row = (await session.execute(
            text(
                "SELECT project, content_hash FROM documents "
                "WHERE id = CAST(:id AS uuid) FOR UPDATE"
            ),
            {"id": str(doc_id)},
        )).first()
        if row is None:
            raise DocumentTargetUnresolved(f"document not found: {doc_id}")
        project = row.project
        if expected_hash is not None and row.content_hash != expected_hash:
            raise DocumentHashConflict(
                document_id=doc_id, expected_hash=expected_hash,
                current_hash=row.content_hash,
            )

    if tags is not None:
        await _set_document_tags(session, doc_id, tags)

    # The payload names which fields moved and carries none of their values:
    # write-time minimization, and a journal row outlives the document it
    # describes.
    await record_event(
        session,
        event_type=DOCUMENT_UPDATED_EVENT,
        object_type="document",
        object_id=doc_id,
        project=project,
        actor=actor,
        api_key_id=api_key_id,
        payload={
            "fields": sorted(
                name for name, value in (
                    ("title", title), ("uri", uri),
                    ("pinned", pinned), ("tags", tags),
                )
                if value is not None
            )
        },
    )


async def rename_documents(
    session: AsyncSession,
    *,
    project: str,
    uri_prefix: str,
    new_uri_prefix: str,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> int:
    """Rewrite a uri prefix across a subtree in one transaction.

    Rows are locked in id order -- the same lock `update_document_metadata`
    takes -- so two concurrent subtree renames cannot deadlock against each
    other. The match avoids LIKE because `_` and `%` are metacharacters there
    and a prefix of `notes/a_b` would over-match `notes/axb`; comparing a
    fixed-length slice of the uri has no metacharacter class at all.

    **Locking order and iteration order are deliberately different.** The rows
    move one at a time through a unique index, so a row whose target is
    another row's current uri must move second -- and in id order that is a
    coin flip on UUID sort, which is how `notes/a -> notes/a/x` came out as a
    `DocumentUriConflict` or as a correct rewrite depending on which id
    happened to be smaller. The mapping is injective, so the collision is
    always transient and always between two rows of this set, and depth
    orders it: moving a subtree *into* itself, the colliding row is the
    deeper one, so the deepest moves first; moving one *out* to an ancestor
    prefix, the colliding row is the shallower one, so the shallowest moves
    first. Anything else -- disjoint prefixes -- has no intra-set collision at
    all and takes either order. A collision with a document outside the set is
    a real conflict and still raises.

    Every row goes through `update_document_metadata` rather than one bulk
    UPDATE, so each renamed document gets its own `document_updated` row and
    the same `DocumentUriConflict` mapping instead of a second write path
    reproducing both.
    """
    if new_uri_prefix == uri_prefix:
        raise DocumentNothingToChange(
            f"new_uri_prefix equals uri_prefix ({uri_prefix!r}); nothing moves"
        )

    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, uri FROM documents "
            "WHERE project = CAST(:p AS text) "
            "  AND (uri = CAST(:u AS text) "
            "       OR left(uri, length(CAST(:u AS text)) + 1) "
            "          = CAST(:u AS text) || '/') "
            "ORDER BY id FOR UPDATE"
        ),
        {"p": project, "u": uri_prefix},
    )).mappings().all()

    # Deepest-first when the new prefix sits under the old one, shallowest-
    # first when the old sits under the new; see the docstring. `sorted` is
    # stable, so rows of equal depth keep the id order they were locked in.
    descend = new_uri_prefix.startswith(uri_prefix + "/")
    for row in sorted(rows, key=lambda r: len(r["uri"]), reverse=descend):
        await update_document_metadata(
            session,
            document_id=row["id"],
            uri=new_uri_prefix + row["uri"][len(uri_prefix):],
            actor=actor,
            api_key_id=api_key_id,
        )

    if rows:
        moved = [row["id"] for row in rows]
        # A resolved link holds the target's id, so its denormalised
        # `target_uri` is stale the moment the target moves; carrying the id
        # means the repair needs no string surgery on the link side.
        await session.execute(
            text(
                "UPDATE document_links l SET target_uri = d.uri "
                "FROM documents d WHERE d.id = l.target_document_id "
                "  AND l.target_document_id = ANY(CAST(:ids AS uuid[])) "
                "  AND l.target_uri IS DISTINCT FROM d.uri"
            ),
            {"ids": moved},
        )
        # A stub points at a uri nobody had filed, and a rename can land a
        # document on exactly that uri -- so this pass is over unresolved
        # links rather than over the moved set. The source document is joined
        # to require that both ends sit in one project: `(project, uri)` is
        # the identity, so an unscoped match resolves a stub against whichever
        # project happens to hold the path, and a link crossing that boundary
        # is what the personal space rests on not happening.
        await session.execute(
            text(
                "UPDATE document_links l SET target_document_id = d.id "
                "FROM documents s, documents d "
                "WHERE s.id = l.source_document_id "
                "  AND l.target_document_id IS NULL "
                "  AND d.id = ANY(CAST(:ids AS uuid[])) "
                "  AND d.project = s.project "
                "  AND d.uri = l.target_uri"
            ),
            {"ids": moved},
        )

    return len(rows)


async def delete_documents(
    session: AsyncSession,
    *,
    project: str,
    uri_prefix: str,
    actor: str | None = None,
    api_key_id: UUID | None = None,
) -> int:
    """Delete a whole uri subtree in one transaction, journaling each row.

    Shaped after `rename_documents` on purpose: the same prefix match, which
    avoids LIKE because `_` and `%` are metacharacters there and a prefix of
    `notes/a_b` would over-match `notes/axb`, and the same `ORDER BY id FOR
    UPDATE` lock order, so a subtree delete and a concurrent subtree rename
    take the rows in one order and cannot deadlock against each other.

    Unlike the rename this needs no depth ordering: deletes cannot collide
    through `ux_documents_project_uri`, so the order rows leave in is free.
    The lock is still taken in id order for the cross-verb reason above.

    Journals one `documents_deleted` row per deleted document rather than one
    row for "a subtree", which would need an object type no vocabulary has.
    `delete_document` journals nothing and that is right for a single note;
    a bulk delete is unrecoverable, cascades blocks and their vectors, and
    over MCP the event's `api_key_id` is the only record of who ran it.

    `actor` and `api_key_id` are what make that last clause true rather than
    aspirational, so they are threaded here rather than left to the doors:
    a door cannot supply an identity this signature does not take, and a
    later task widening it is how the journal-before-delete ordering gets
    re-derived by someone who did not write it. Both are optional because
    REST does not have them to give -- it authenticates its own way and its
    sibling journal writers pass neither -- while MCP fills both from
    `current_key_name()` / `current_api_key_id()`.
    """
    if not uri_prefix:
        # `left(uri, 0 + 1) = '/'` matches nothing, so an unrefused empty
        # prefix reports a successful delete of zero rows.
        raise DocumentNothingToChange("uri_prefix must not be empty")

    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, uri, project FROM documents "
            "WHERE project = CAST(:p AS text) "
            "  AND (uri = CAST(:u AS text) "
            "       OR left(uri, length(CAST(:u AS text)) + 1) "
            "          = CAST(:u AS text) || '/') "
            "ORDER BY id FOR UPDATE"
        ),
        {"p": project, "u": uri_prefix},
    )).mappings().all()

    if not rows:
        return 0

    # Journal BEFORE the delete: `record_event` takes the document id as its
    # object id, and writing after the row is gone would journal against an
    # id nothing resolves. The events table holds no foreign key to
    # `documents`, so the rows outlive their subject by design -- that is
    # what makes this an audit trail rather than a cache.
    for row in rows:
        landed = await record_event(
            session,
            event_type=DOCUMENTS_DELETED_EVENT,
            object_type="document",
            object_id=UUID(row["id"]),
            project=row["project"],
            actor=actor,
            api_key_id=api_key_id,
            payload={"uri": row["uri"], "uri_prefix": uri_prefix},
        )
        if not landed:
            # Raising here rather than after the loop is what makes the
            # refusal free: the `DELETE` below never runs, so the caller is
            # left with a transaction to roll back rather than an unaudited
            # delete to explain. Same posture `update_document_metadata`
            # takes on its own refusals.
            raise DocumentJournalWriteFailed(
                f"documents_deleted did not land for {row['uri']!r}; "
                "refusing to delete unaudited"
            )

    await session.execute(
        text("DELETE FROM documents WHERE id = ANY(CAST(:ids AS uuid[]))"),
        {"ids": [row["id"] for row in rows]},
    )
    return len(rows)


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


_DOCUMENT_HASH = text(
    "SELECT content_hash FROM documents WHERE id = CAST(:document_id AS uuid)"
)


async def document_hash(session: AsyncSession, *, document_id: str) -> str | None:
    """The document's current `content_hash` -- what a caller preconditions
    its next edit on.

    Its own statement, separate from `document_content`: the hash is one
    short string, so unlike the verbatim source it is served unconditionally
    and must not ride that function's `include_content` gate.
    """
    return (await session.execute(
        _DOCUMENT_HASH, {"document_id": document_id}
    )).scalar_one_or_none()


# `source` is sliced here from one fetch of `content`, not per row in SQL: a
# per-row `substring` decompresses the TOASTed content once for every block.
_BLOCKS = """
    SELECT CAST(b.id AS text) AS id, b.type, b.text, b.order_index,
           CAST(b.parent_id AS text) AS parent_id,
           b.properties,
           lower(b.char_span) AS span_start, upper(b.char_span) AS span_end
    FROM blocks b
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
    clause = "AND b.id = ANY(CAST(:ids AS uuid[]))" if block_ids is not None else ""
    params: dict = {"document_id": document_id}
    if block_ids is not None:
        params["ids"] = block_ids
    rows = (await session.execute(
        text(_BLOCKS.format(clause=clause)), params
    )).mappings().all()
    content = (await session.execute(
        _DOCUMENT_CONTENT, {"document_id": document_id}
    )).scalar_one_or_none() if rows else None
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
            source=slice_source(content, r["span_start"], r["span_end"]),
        )
        for r in rows
    ]
