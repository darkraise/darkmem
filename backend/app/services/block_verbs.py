"""The block verbs -- block-first ingest's write half (spec §8, increment 8).

Four verbs, both doors, one service layer (invariant 17). The client holds
block ids because it fetched the blocks, so every verb addresses a real id:
there is no diffing and no matching heuristic anywhere in this module.

Every verb runs the same pass: lock the document, load its tree, apply one
mutation in memory, serialise, write the placement and the document row in a
SAVEPOINT, journal, commit, then embed only the block that changed. The
serialiser is the only thing that knows where each block landed, so
``char_span`` is recomputed on every mutation rather than drifting.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import embed_blocks
from app.services.block_fact_sources import withdraw_blocks
from app.services.block_serializer import (
    TreeBlock,
    derive_markers,
    reproduces_source,
    serialize_tree,
)
from app.services.document_door import (
    BLOCK_FIRST,
    MAX_BLOCKS,
    MAX_CONTENT_CHARS,
    DocumentNotConvertible,
    DocumentTooLarge,
    expire_facts_left_bare,
)
from app.services.document_ingest import compute_content_hash
from app.services.events import record_event
from app.taxonomy import normalize_block_type
from app.utils.ids import new_id

__all__ = [
    "BLOCKS_EDITED_EVENT",
    "BlockCycleError",
    "BlockTargetUnresolved",
    "BlockWriteResult",
    "delete_block",
    "insert_block",
    "move_block",
    "update_block",
]

BLOCKS_EDITED_EVENT = "blocks_edited"


class BlockTargetUnresolved(ValueError):
    """The named block or document does not exist, or is not where the caller
    said it was. Refused rather than resolved by nearest match: this door is
    id-addressed precisely so it never has to guess."""


class BlockCycleError(ValueError):
    """A move would put a block inside its own subtree."""


@dataclass(frozen=True)
class BlockWriteResult:
    document_id: str
    block_id: str | None
    outcome: str            # updated | inserted | moved | deleted
    content_hash: str
    blocks_total: int
    blocks_embedded: int


_LOCK_DOCUMENT = text(
    "SELECT id FROM documents WHERE id = CAST(:id AS uuid) FOR UPDATE"
)
_RESOLVE_BLOCK = text(
    "SELECT CAST(document_id AS text) AS document_id FROM blocks "
    "WHERE id = CAST(:id AS uuid)"
)
_DOC_META = text(
    "SELECT project, content, properties->>'ingest_direction' AS direction, "
    "       properties->>'frontmatter' AS frontmatter "
    "FROM documents WHERE id = CAST(:id AS uuid)"
)
_LOAD_TREE = text(
    "SELECT id, parent_id, order_index, type, text, properties, "
    "       lower(char_span) AS lo, upper(char_span) AS hi "
    "FROM blocks WHERE document_id = CAST(:id AS uuid) ORDER BY order_index"
)
# `parent_id` is the fourth unnest and it is not optional (review M-8).
# Without it the only statement writing parentage is _UPDATE_BLOCK, which runs
# only for `updated` -- so move_block reordered its target without ever
# reparenting it, silently doing half its job. The placement pass already
# rewrites the whole document's order and spans, so carrying parentage in the
# same statement is both correct and free.
_PLACE = text(
    """
    UPDATE blocks b
    SET order_index = u.ord,
        char_span = CAST(CAST(u.span AS text) AS int4range),
        properties = CAST(u.props AS jsonb),
        parent_id = CAST(u.parent AS uuid)
    FROM (SELECT unnest(CAST(:ids AS uuid[])) AS id,
                 unnest(CAST(:ords AS integer[])) AS ord,
                 unnest(CAST(:spans AS text[])) AS span,
                 unnest(CAST(:props AS text[])) AS props,
                 unnest(CAST(:parents AS text[])) AS parent) u
    WHERE b.id = u.id
    """
)
_INSERT_BLOCK = text(
    "INSERT INTO blocks (id, document_id, parent_id, order_index, type, text, properties) "
    "VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), CAST(:parent AS uuid), "
    "        :ord, CAST(:type AS text), CAST(:text AS text), CAST(:props AS jsonb))"
)
_UPDATE_BLOCK = text(
    "UPDATE blocks SET type = CAST(:type AS text), text = CAST(:text AS text), "
    "parent_id = CAST(:parent AS uuid) WHERE id = CAST(:id AS uuid)"
)
_DELETE_BLOCK = text("DELETE FROM blocks WHERE id = CAST(:id AS uuid)")
# `properties` is merged with `||`, never written wholesale: the direction flag
# is server-owned and a wholesale write would erase a document's frontmatter.
_WRITE_DOC = text(
    """
    UPDATE documents
    SET content = CAST(:content AS text),
        content_hash = CAST(:hash AS text),
        properties = COALESCE(properties, '{}'::jsonb)
                     || jsonb_build_object('ingest_direction', 'blocks')
    WHERE id = CAST(:id AS uuid)
    """
)


def _subtree(tree: list[TreeBlock], root: UUID) -> list[UUID]:
    """`root` and every descendant, root first."""
    children: dict[UUID | None, list[TreeBlock]] = {}
    for block in tree:
        children.setdefault(block.parent_id, []).append(block)
    out: list[UUID] = []
    stack = [root]
    while stack:
        node = stack.pop()
        out.append(node)
        stack.extend(child.id for child in children.get(node, []))
    return out


async def _mutate(session, llm, *, document_id, apply, touched_embed, verb, block_id):
    """Lock, load, mutate in memory, serialise, write, journal, embed.

    Review M-3: the lock is the first statement, before anything is read off
    the row. The whole pass is a read-modify-write that crosses several
    awaits, and `put_document` takes the same lock, so the two serialise
    instead of interleaving into a tree whose blocks were stripped underneath
    it.
    """
    await session.execute(_LOCK_DOCUMENT, {"id": document_id})

    meta = (await session.execute(_DOC_META, {"id": document_id})).mappings().first()
    if meta is None:
        raise BlockTargetUnresolved(f"no document with id {document_id}")
    rows = (await session.execute(_LOAD_TREE, {"id": document_id})).mappings().all()
    tree = [
        TreeBlock(r["id"], r["parent_id"], r["order_index"], r["type"],
                  r["text"] or "", r["properties"])
        for r in rows
    ]
    spans = {
        r["id"]: (r["lo"], r["hi"])
        for r in rows
        if r["lo"] is not None and r["hi"] is not None
    }

    if meta["direction"] != BLOCK_FIRST and meta["content"]:
        # The conversion pass. Review M-2: refuse rather than convert when the
        # serialiser cannot reproduce the stored source -- regenerating content
        # without a construct the parser dropped is silent loss on exactly the
        # corpus this programme exists to hold.
        if not reproduces_source(
            tree, meta["content"], spans, frontmatter=meta["frontmatter"]
        ):
            raise DocumentNotConvertible(
                "this document contains source the block editor cannot "
                "represent (a raw HTML block, or a link-reference "
                "definition). Editing it as blocks would rewrite the file "
                "without it. Edit it with document_put instead."
            )
        tree = derive_markers(tree, meta["content"], spans)

    tree, inserted, deleted_subtree = apply(tree)

    # Frontmatter rides every serialisation, not only the conversion: an
    # ordinary edit of an already-block-first document would otherwise drop
    # the fence on the first save.
    result = serialize_tree(tree, frontmatter=meta["frontmatter"])
    if len(result.content) > MAX_CONTENT_CHARS:
        raise DocumentTooLarge(
            f"the edited document serialises to {len(result.content)} "
            f"characters; the bound is {MAX_CONTENT_CHARS}"
        )
    if len(tree) > MAX_BLOCKS:
        raise DocumentTooLarge(
            f"the edited document holds {len(tree)} blocks; the bound is "
            f"{MAX_BLOCKS}"
        )
    content_hash = compute_content_hash(result.content)
    by_id = {b.id: b for b in tree}

    async with session.begin_nested():
        if deleted_subtree:
            withdrawal = await withdraw_blocks(
                session,
                block_ids=[str(b) for b in deleted_subtree],
                document_id=document_id,
            )
            await expire_facts_left_bare(
                session, withdrawal, document_id=document_id
            )
            # The subtree's root only: parent_id ON DELETE CASCADE takes the
            # rest, and block_embeddings__<slug> cascades in every partition.
            await session.execute(
                _DELETE_BLOCK, {"id": str(deleted_subtree[0])}
            )
        if inserted is not None:
            await session.execute(_INSERT_BLOCK, {
                "id": str(inserted.id),
                "doc": document_id,
                "parent": None if inserted.parent_id is None else str(inserted.parent_id),
                "ord": inserted.order_index,
                "type": inserted.type,
                "text": inserted.text,
                "props": _json(inserted.properties),
            })
        if verb == "updated":
            target = by_id[UUID(block_id)]
            await session.execute(_UPDATE_BLOCK, {
                "id": block_id,
                "type": target.type,
                "text": target.text,
                "parent": None if target.parent_id is None else str(target.parent_id),
            })

        placed = {p.block_id: p for p in result.placed}
        ids, ords, spans_out, props_out, parents = [], [], [], [], []
        for block in tree:
            p = placed[block.id]
            ids.append(str(block.id))
            ords.append(p.order_index)
            spans_out.append(f"[{p.char_span[0]},{p.char_span[1]})")
            props_out.append(_json(block.properties))
            parents.append(None if block.parent_id is None else str(block.parent_id))
        if ids:
            await session.execute(_PLACE, {
                "ids": ids, "ords": ords, "spans": spans_out,
                "props": props_out, "parents": parents,
            })

        await session.execute(_WRITE_DOC, {
            "id": document_id, "content": result.content, "hash": content_hash,
        })
        # No block text in the payload: write-time minimization, and a journal
        # row outlives the document it describes.
        await record_event(
            session,
            event_type=BLOCKS_EDITED_EVENT,
            object_type="document",
            object_id=UUID(document_id),
            project=meta["project"],
            payload={"verb": verb, "block_id": block_id,
                     "blocks_total": len(tree), "content_hash": content_hash},
        )
    await session.commit()

    written = 0
    if touched_embed is not None:
        embed = await embed_blocks(session, llm, block_ids=[touched_embed])
        written = embed.written if embed else 0
        await session.commit()

    return BlockWriteResult(document_id, block_id, verb, content_hash,
                            len(tree), written)


def _json(value):
    import json

    return None if value is None else json.dumps(value)


async def _document_of(session: AsyncSession, block_id: str) -> str:
    row = (await session.execute(_RESOLVE_BLOCK, {"id": block_id})).mappings().first()
    if row is None:
        raise BlockTargetUnresolved(f"no block with id {block_id}")
    return row["document_id"]


async def update_block(
    session: AsyncSession, llm, *, block_id: str,
    text: str, type: str | None = None, properties: dict | None = None,
) -> BlockWriteResult:
    document_id = await _document_of(session, block_id)
    target = UUID(block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(f"block {block_id} is not in this document")
        out = []
        for block in tree:
            if block.id != target:
                out.append(block)
                continue
            merged = {**(block.properties or {}), **(properties or {})} or None
            out.append(TreeBlock(
                block.id, block.parent_id, block.order_index,
                normalize_block_type(type) if type else block.type,
                text, merged,
            ))
        return out, None, []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=block_id, verb="updated", block_id=block_id)


async def insert_block(
    session: AsyncSession, llm, *, document_id: str, type: str, text: str,
    parent_id: str | None = None, after_block_id: str | None = None,
    properties: dict | None = None,
) -> BlockWriteResult:
    minted = new_id()
    parent = None if parent_id is None else UUID(parent_id)
    after = None if after_block_id is None else UUID(after_block_id)

    def apply(tree: list[TreeBlock]):
        if parent is not None and not any(b.id == parent for b in tree):
            raise BlockTargetUnresolved(f"no parent block {parent_id} in this document")
        siblings = [b for b in tree if b.parent_id == parent]
        if after is None:
            position = 0
        else:
            index = next((i for i, b in enumerate(siblings) if b.id == after), None)
            if index is None:
                raise BlockTargetUnresolved(
                    f"after_block_id {after_block_id} is not a child of the "
                    "target parent"
                )
            position = index + 1
        block = TreeBlock(minted, parent, 0, normalize_block_type(type), text,
                          properties or None)
        reordered = siblings[:position] + [block] + siblings[position:]
        others = [b for b in tree if b.parent_id != parent]
        renumbered = [
            TreeBlock(b.id, b.parent_id, i, b.type, b.text, b.properties)
            for i, b in enumerate(reordered)
        ]
        return others + renumbered, next(b for b in renumbered if b.id == minted), []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=str(minted), verb="inserted",
                         block_id=str(minted))


async def move_block(
    session: AsyncSession, llm, *, block_id: str,
    new_parent_id: str | None = None, after_block_id: str | None = None,
) -> BlockWriteResult:
    document_id = await _document_of(session, block_id)
    target = UUID(block_id)
    parent = None if new_parent_id is None else UUID(new_parent_id)
    after = None if after_block_id is None else UUID(after_block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(f"block {block_id} is not in this document")
        if parent is not None:
            if parent in _subtree(tree, target):
                raise BlockCycleError(
                    "a block cannot be moved inside its own subtree"
                )
            if not any(b.id == parent for b in tree):
                raise BlockTargetUnresolved(f"no parent block {new_parent_id}")
        moved = next(b for b in tree if b.id == target)
        rest = [b for b in tree if b.id != target]
        siblings = [b for b in rest if b.parent_id == parent]
        if after is None:
            position = 0
        else:
            index = next((i for i, b in enumerate(siblings) if b.id == after), None)
            if index is None:
                raise BlockTargetUnresolved(
                    f"after_block_id {after_block_id} is not a child of the "
                    "target parent"
                )
            position = index + 1
        placed = TreeBlock(moved.id, parent, 0, moved.type, moved.text,
                           moved.properties)
        reordered = siblings[:position] + [placed] + siblings[position:]
        others = [b for b in rest if b.parent_id != parent]
        renumbered = [
            TreeBlock(b.id, b.parent_id, i, b.type, b.text, b.properties)
            for i, b in enumerate(reordered)
        ]
        return others + renumbered, None, []

    # No embed: a move changes position, never text.
    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=None, verb="moved", block_id=block_id)


async def delete_block(
    session: AsyncSession, llm, *, block_id: str,
) -> BlockWriteResult:
    document_id = await _document_of(session, block_id)
    target = UUID(block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(f"block {block_id} is not in this document")
        doomed = _subtree(tree, target)
        remaining = [b for b in tree if b.id not in set(doomed)]
        return remaining, None, doomed

    # No embed: the rows and their vectors go with the cascade.
    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=None, verb="deleted", block_id=block_id)
