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

from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import PAGE_PARENT_TABLE, PARENT_TABLE, embed_blocks
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
)
from app.services.document_ingest import DocumentHashConflict, compute_content_hash
from app.services.events import record_event
from app.taxonomy import normalize_block_type, normalize_page_block_type
from app.utils.ids import new_id

__all__ = [
    "BLOCKS_EDITED_EVENT",
    "DOCUMENT_OWNER",
    "PAGE_OWNER",
    "BlockOwner",
    "BlockCycleError",
    "BlockTargetUnresolved",
    "BlockWriteResult",
    "PageBlockInvalid",
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


class PageBlockInvalid(ValueError):
    """A page block the page rules refuse: a missing or malformed required
    property, or a parent that holds no children on a page."""


@dataclass(frozen=True)
class BlockWriteResult:
    document_id: str | None
    owner_kind: str
    owner_id: str
    block_id: str | None
    outcome: str            # updated | inserted | moved | deleted
    content_hash: str
    blocks_total: int
    blocks_embedded: int


@dataclass(frozen=True)
class BlockOwner:
    """What `_mutate` needs to know about the thing a block belongs to.

    The five statements below are the complete set that names `documents`;
    `_PLACE`, `_UPDATE_BLOCK` and `_DELETE_BLOCK` key on `blocks.id` and are
    owner-agnostic already. `object_type` is here because it was a hardcoded
    literal at the journal call, which would have filed a page edit as a
    document. `noun` is separate from it rather than reused: `object_type` is
    a member of the closed `OBJECT_TYPES` vocabulary and answers to the events
    journal, while `noun` is prose in a refusal a human reads, and the two are
    free to diverge.

    `normalize_type`, `validate` and `check_nesting` are where the two owners'
    block rules differ. The document instance carries today's behaviour -- the
    document normaliser, no property rules, any parent -- so a document verb
    naming a page-only type still stores `paragraph`.
    """
    kind: str
    object_type: str
    noun: str
    lock: Any
    meta: Any
    load_tree: Any
    insert_block: Any
    write_owner: Any
    embed_parent: str
    normalize_type: Callable[[str | None], str]
    validate: Callable[[TreeBlock, str | None], TreeBlock]
    check_nesting: Callable[[TreeBlock | None, TreeBlock], None]


_LOCK_DOCUMENT = text(
    "SELECT id FROM documents WHERE id = CAST(:id AS uuid) FOR UPDATE"
)
_RESOLVE_BLOCK = text(
    "SELECT CAST(document_id AS text) AS document_id, "
    "       CAST(page_id AS text) AS page_id "
    "FROM blocks WHERE id = CAST(:id AS uuid)"
)
_DOC_META = text(
    "SELECT project, content, content_hash, "
    "       properties->>'ingest_direction' AS direction, "
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
    f"""
    UPDATE documents
    SET content = CAST(:content AS text),
        content_hash = CAST(:hash AS text),
        properties = COALESCE(properties, '{{}}'::jsonb)
                     || jsonb_build_object('ingest_direction', '{BLOCK_FIRST}')
    WHERE id = CAST(:id AS uuid)
    """
)


def _keep_block(block: TreeBlock, previous_type: str | None) -> TreeBlock:
    return block


def _any_parent(parent: TreeBlock | None, child: TreeBlock) -> None:
    return None


DOCUMENT_OWNER = BlockOwner(
    kind="document",
    object_type="document",
    noun="document",
    lock=_LOCK_DOCUMENT,
    meta=_DOC_META,
    load_tree=_LOAD_TREE,
    insert_block=_INSERT_BLOCK,
    write_owner=_WRITE_DOC,
    embed_parent=PARENT_TABLE,
    normalize_type=normalize_block_type,
    validate=_keep_block,
    check_nesting=_any_parent,
)

_LOCK_PAGE = text(
    "SELECT id FROM pages WHERE id = CAST(:id AS uuid) "
    "AND deleted_at IS NULL FOR UPDATE"
)
# A page is block-first by construction: it has no authored source, so there
# is nothing for the conversion pass to reproduce and the refusal it can raise
# names a remedy (`document_put`) a page has no door for. Selecting the
# BLOCK_FIRST literal is what keeps `_mutate` on one code path.
_PAGE_META = text(
    "SELECT project, content, content_hash, "
    f"       '{BLOCK_FIRST}' AS direction, NULL AS frontmatter "
    "FROM pages WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL"
)
_LOAD_PAGE_TREE = text(
    "SELECT id, parent_id, order_index, type, text, properties, "
    "       lower(char_span) AS lo, upper(char_span) AS hi "
    "FROM blocks WHERE page_id = CAST(:id AS uuid) ORDER BY order_index"
)
_INSERT_PAGE_BLOCK = text(
    "INSERT INTO blocks (id, page_id, parent_id, order_index, type, text, properties) "
    "VALUES (CAST(:id AS uuid), CAST(:doc AS uuid), CAST(:parent AS uuid), "
    "        :ord, CAST(:type AS text), CAST(:text AS text), CAST(:props AS jsonb))"
)
_WRITE_PAGE = text(
    "UPDATE pages SET content = CAST(:content AS text), "
    "content_hash = CAST(:hash AS text) WHERE id = CAST(:id AS uuid)"
)


# The keys each type defines. A page type change drops every other key, so
# `checked` never rides onto a paragraph and a list's `marker` never rides onto
# a to-do.
_PAGE_TYPE_PROPERTIES: dict[str, frozenset[str]] = {
    "paragraph": frozenset(),
    "heading": frozenset({"level"}),
    "list": frozenset({"ordered", "marker", "number"}),
    "code": frozenset({"language"}),
    "quote": frozenset(),
    "table": frozenset({"header", "alignments"}),
    "table_row": frozenset({"cells"}),
    "divider": frozenset(),
    "html": frozenset(),
    "todo": frozenset({"checked"}),
    "toggle": frozenset(),
    "callout": frozenset({"variant"}),
}
_CALLOUT_VARIANTS = frozenset({"info", "warning", "error", "success"})
# Headings are absent on purpose: an editor renders a heading's children as
# indentation, which is not what a heading means.
_PAGE_CONTAINERS = frozenset({"list", "todo", "toggle"})


def _validate_page_block(block: TreeBlock, previous_type: str | None) -> TreeBlock:
    if (
        previous_type is not None
        and previous_type != block.type
        and block.properties
    ):
        defined = _PAGE_TYPE_PROPERTIES.get(block.type, frozenset())
        kept = {k: v for k, v in block.properties.items() if k in defined}
        block = replace(block, properties=kept or None)
    properties = block.properties or {}
    if block.type == "todo" and not isinstance(properties.get("checked"), bool):
        raise PageBlockInvalid("a todo block needs a boolean `checked` property")
    variant = properties.get("variant")
    if block.type == "callout" and (
        not isinstance(variant, str) or variant not in _CALLOUT_VARIANTS
    ):
        raise PageBlockInvalid(
            "a callout block needs `variant` set to one of "
            f"{', '.join(sorted(_CALLOUT_VARIANTS))}"
        )
    return block


def _check_page_nesting(parent: TreeBlock | None, child: TreeBlock) -> None:
    if parent is None or parent.type in _PAGE_CONTAINERS:
        return
    if parent.type == "table" and child.type == "table_row":
        return
    raise PageBlockInvalid(
        f"a {parent.type} block cannot hold a {child.type} block on a page: "
        "only list, todo and toggle blocks hold children, and a table holds "
        "its table_row blocks"
    )


PAGE_OWNER = BlockOwner(
    kind="page",
    object_type="page",
    noun="page",
    lock=_LOCK_PAGE,
    meta=_PAGE_META,
    load_tree=_LOAD_PAGE_TREE,
    insert_block=_INSERT_PAGE_BLOCK,
    write_owner=_WRITE_PAGE,
    embed_parent=PAGE_PARENT_TABLE,
    normalize_type=normalize_page_block_type,
    validate=_validate_page_block,
    check_nesting=_check_page_nesting,
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


async def _mutate(session, llm, *, document_id, apply, touched_embed, verb,
                  block_id, expected_hash=None, owner: BlockOwner = DOCUMENT_OWNER):
    """Lock, load, mutate in memory, serialise, write, journal, embed.

    Review M-3: the lock is the first statement, before anything is read off
    the row. The whole pass is a read-modify-write that crosses several
    awaits, and `put_document` takes the same lock, so the two serialise
    instead of interleaving into a tree whose blocks were stripped underneath
    it.
    """
    await session.execute(owner.lock, {"id": document_id})

    meta = (await session.execute(owner.meta, {"id": document_id})).mappings().first()
    if meta is None:
        raise BlockTargetUnresolved(f"no {owner.noun} with id {document_id}")
    # After the lock, which is what makes this a compare-and-set rather than a
    # check-then-act: no writer can move content_hash between this read and
    # the write below, because both are inside one held row lock.
    if expected_hash is not None and meta["content_hash"] != expected_hash:
        raise DocumentHashConflict(
            document_id=document_id,
            expected_hash=expected_hash,
            current_hash=meta["content_hash"],
        )
    rows = (await session.execute(owner.load_tree, {"id": document_id})).mappings().all()
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
            # The subtree's root only: parent_id ON DELETE CASCADE takes the
            # rest, and block_embeddings__<slug> cascades in every partition.
            await session.execute(
                _DELETE_BLOCK, {"id": str(deleted_subtree[0])}
            )
        if inserted is not None:
            await session.execute(owner.insert_block, {
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

        await session.execute(owner.write_owner, {
            "id": document_id, "content": result.content, "hash": content_hash,
        })
        # No block text in the payload: write-time minimization, and a journal
        # row outlives the document it describes.
        await record_event(
            session,
            event_type=BLOCKS_EDITED_EVENT,
            object_type=owner.object_type,
            object_id=UUID(document_id),
            project=meta["project"],
            payload={"verb": verb, "block_id": block_id,
                     "blocks_total": len(tree), "content_hash": content_hash},
        )
    await session.commit()

    written = 0
    if touched_embed is not None:
        embed = await embed_blocks(session, llm, block_ids=[touched_embed],
                                   parent=owner.embed_parent)
        written = embed.written if embed else 0
        await session.commit()

    return BlockWriteResult(
        document_id=document_id if owner.kind == "document" else None,
        owner_kind=owner.kind,
        owner_id=document_id,
        block_id=block_id,
        outcome=verb,
        content_hash=content_hash,
        blocks_total=len(tree),
        blocks_embedded=written,
    )


def _json(value):
    import json

    return None if value is None else json.dumps(value)


async def _owner_of(
    session: AsyncSession, block_id: str, owner: BlockOwner = DOCUMENT_OWNER,
) -> tuple[BlockOwner, str]:
    """The owner the caller named is verified, never discovered: a door that
    has not been given pages must refuse a page block rather than edit it
    because the block id happened to resolve.

    `blocks_exactly_one_owner` guarantees exactly one column is set, so the
    named owner's column being NULL means the block belongs to the other.
    """
    row = (await session.execute(_RESOLVE_BLOCK, {"id": block_id})).mappings().first()
    if row is None:
        raise BlockTargetUnresolved(f"no block with id {block_id}")
    owner_id = row["document_id"] if owner.kind == DOCUMENT_OWNER.kind else row["page_id"]
    if owner_id is None:
        raise BlockTargetUnresolved(
            f"block {block_id} does not belong to any {owner.noun}"
        )
    return owner, owner_id


def _insert_into(
    tree: list[TreeBlock], owner: BlockOwner, *, block_id: UUID, type: str,
    text: str, properties: dict | None, parent_id: str | None,
    after_block_id: str | None,
) -> tuple[list[TreeBlock], TreeBlock]:
    """Place one new block in the in-memory tree; returns the tree and the
    placed block."""
    parent = None if parent_id is None else UUID(parent_id)
    after = None if after_block_id is None else UUID(after_block_id)
    parent_block = None
    if parent is not None:
        parent_block = next((b for b in tree if b.id == parent), None)
        if parent_block is None:
            raise BlockTargetUnresolved(
                f"no parent block {parent_id} in this {owner.noun}")
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
    block = owner.validate(
        TreeBlock(block_id, parent, 0, owner.normalize_type(type), text,
                  properties or None),
        None,
    )
    owner.check_nesting(parent_block, block)
    reordered = siblings[:position] + [block] + siblings[position:]
    others = [b for b in tree if b.parent_id != parent]
    renumbered = [
        TreeBlock(b.id, b.parent_id, i, b.type, b.text, b.properties)
        for i, b in enumerate(reordered)
    ]
    return others + renumbered, next(b for b in renumbered if b.id == block_id)


async def update_block(
    session: AsyncSession, llm, *, block_id: str,
    text: str, type: str | None = None, properties: dict | None = None,
    expected_hash: str | None = None, owner: BlockOwner = DOCUMENT_OWNER,
) -> BlockWriteResult:
    owner, document_id = await _owner_of(session, block_id, owner)
    target = UUID(block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(
                f"block {block_id} is not in this {owner.noun}")
        out = []
        for block in tree:
            if block.id != target:
                out.append(block)
                continue
            merged = {**(block.properties or {}), **(properties or {})} or None
            out.append(owner.validate(
                TreeBlock(
                    block.id, block.parent_id, block.order_index,
                    owner.normalize_type(type) if type else block.type,
                    text, merged,
                ),
                block.type,
            ))
        return out, None, []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=block_id, verb="updated",
                         block_id=block_id, expected_hash=expected_hash,
                         owner=owner)


async def insert_block(
    session: AsyncSession, llm, *, document_id: str, type: str, text: str,
    parent_id: str | None = None, after_block_id: str | None = None,
    properties: dict | None = None, expected_hash: str | None = None,
    owner: BlockOwner = DOCUMENT_OWNER,
) -> BlockWriteResult:
    minted = new_id()

    def apply(tree: list[TreeBlock]):
        tree, placed = _insert_into(
            tree, owner, block_id=minted, type=type, text=text,
            properties=properties, parent_id=parent_id,
            after_block_id=after_block_id,
        )
        return tree, placed, []

    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=str(minted), verb="inserted",
                         block_id=str(minted), expected_hash=expected_hash,
                         owner=owner)


async def move_block(
    session: AsyncSession, llm, *, block_id: str,
    new_parent_id: str | None = None, after_block_id: str | None = None,
    expected_hash: str | None = None, owner: BlockOwner = DOCUMENT_OWNER,
) -> BlockWriteResult:
    owner, document_id = await _owner_of(session, block_id, owner)
    target = UUID(block_id)
    parent = None if new_parent_id is None else UUID(new_parent_id)
    after = None if after_block_id is None else UUID(after_block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(
                f"block {block_id} is not in this {owner.noun}")
        parent_block = None
        if parent is not None:
            if parent in _subtree(tree, target):
                raise BlockCycleError(
                    "a block cannot be moved inside its own subtree"
                )
            parent_block = next((b for b in tree if b.id == parent), None)
            if parent_block is None:
                raise BlockTargetUnresolved(f"no parent block {new_parent_id}")
        moved = next(b for b in tree if b.id == target)
        owner.check_nesting(parent_block, moved)
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
                         touched_embed=None, verb="moved", block_id=block_id,
                         expected_hash=expected_hash, owner=owner)


async def delete_block(
    session: AsyncSession, llm, *, block_id: str,
    expected_hash: str | None = None, owner: BlockOwner = DOCUMENT_OWNER,
) -> BlockWriteResult:
    owner, document_id = await _owner_of(session, block_id, owner)
    target = UUID(block_id)

    def apply(tree: list[TreeBlock]):
        if not any(b.id == target for b in tree):
            raise BlockTargetUnresolved(
                f"block {block_id} is not in this {owner.noun}")
        doomed = _subtree(tree, target)
        remaining = [b for b in tree if b.id not in set(doomed)]
        return remaining, None, doomed

    # No embed: the rows and their vectors go with the cascade.
    return await _mutate(session, llm, document_id=document_id, apply=apply,
                         touched_embed=None, verb="deleted", block_id=block_id,
                         expected_hash=expected_hash, owner=owner)
