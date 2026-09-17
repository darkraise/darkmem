"""The page door: create, read, move and rename (spec 2026-09-08, §7).

A page is block-first by construction: `create_page` parses the caller's
content, writes the blocks, and stores the *serialiser's* output as
`content` rather than the caller's text. Nothing else keeps that true --
`block_verbs._PAGE_META` reports every page as already converted, so a page
that carried an authored source would never be reconciled with its blocks
and could never be refused either.

Embedding runs after the filing commits, as on the document door: first
contact with an unknown fingerprint runs child-table DDL through
`embedder_registry.register`, which commits on this session.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_embeddings import PAGE_PARENT_TABLE, embed_blocks
from app.services.block_serializer import TreeBlock, serialize_tree
from app.services.document_ingest import compute_content_hash
from app.services.document_parsers import parse_markdown
from app.services.events import record_event
from app.taxonomy import normalize_block_type

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "PAGE_CREATED_EVENT",
    "PAGE_MOVED_EVENT",
    "PAGE_UPDATED_EVENT",
    "PageCycleError",
    "PageResult",
    "PageTargetUnresolved",
    "PageTooLarge",
    "PageView",
    "create_page",
    "get_page",
    "list_pages",
    "move_page",
    "rename_page",
    "root_lock_key",
]

MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000

PAGE_CREATED_EVENT = "page_created"
PAGE_MOVED_EVENT = "page_moved"
PAGE_UPDATED_EVENT = "page_updated"


class PageTooLarge(ValueError):
    """Refused at the door. The message names which bound was hit."""


class PageTargetUnresolved(ValueError):
    """Nothing a caller named resolves to a live page.

    Its own type rather than the document door's: the two doors address
    separate objects, and a caller catching one must not silently absorb a
    refusal about the other.
    """


class PageCycleError(ValueError):
    """The named parent is the moved page or lies inside its subtree."""


@dataclass(frozen=True)
class PageResult:
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    blocks_written: int
    blocks_embedded: int


@dataclass(frozen=True)
class PageView:
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    properties: dict | None
    blocks: list[dict]
    content: str | None


_LOCK_PARENT = text(
    "SELECT id FROM pages WHERE id = CAST(:id AS uuid) "
    "AND project = :project AND deleted_at IS NULL FOR UPDATE"
)
# Row locks cannot guard a tree walk: a locking clause is illegal inside a
# recursive CTE, and per-row locks taken in walk order deadlock against a
# create holding a parent while it shifts siblings. One transaction-scoped
# advisory lock per project tree, taken before any row lock, serialises every
# sibling-set write instead.
_LOCK_ROOT = text("SELECT pg_advisory_xact_lock(hashtext(:key))")
_NEXT_ORDER = text(
    """
    SELECT COALESCE(MAX(order_index) + 1, 0) FROM pages
    WHERE project = :project
      AND parent_id IS NOT DISTINCT FROM CAST(:parent AS uuid)
    """
)
_SIBLING_ORDER = text(
    """
    SELECT order_index FROM pages
    WHERE id = CAST(:id AS uuid) AND project = :project
      AND parent_id IS NOT DISTINCT FROM CAST(:parent AS uuid)
      AND deleted_at IS NULL
    """
)
_SHIFT_SIBLINGS = text(
    """
    UPDATE pages SET order_index = order_index + 1
    WHERE project = :project
      AND parent_id IS NOT DISTINCT FROM CAST(:parent AS uuid)
      AND order_index >= CAST(:from_index AS integer)
    """
)
_INSERT_PAGE = text(
    """
    INSERT INTO pages (id, project, parent_id, order_index, title, content,
                       content_hash, properties)
    VALUES (CAST(:id AS uuid), :project, CAST(:parent AS uuid),
            CAST(:order_index AS integer), CAST(:title AS text),
            CAST(:content AS text), CAST(:content_hash AS text),
            CAST(:properties AS jsonb))
    """
)
# The `char_span` bind is cast twice for the reason `documents._INSERT_BLOCK`
# records: a single cast makes asyncpg infer int4range and refuse the string.
_INSERT_BLOCK = text(
    """
    INSERT INTO blocks (id, page_id, parent_id, order_index, type, text,
                        properties, char_span)
    VALUES (CAST(:id AS uuid), CAST(:page_id AS uuid), CAST(:parent_id AS uuid),
            CAST(:order_index AS integer), CAST(:type AS text),
            CAST(:text AS text), CAST(:properties AS jsonb),
            CAST(CAST(:char_span AS text) AS int4range))
    """
)
_MOVED_PAGE = text(
    "SELECT project FROM pages WHERE id = CAST(:id AS uuid) "
    "AND deleted_at IS NULL"
)
# `parent_id` is re-read under the lock: the unlocked read above only finds
# which project's tree to lock, and a concurrent move may since have changed it.
_LOCK_MOVED_PAGE = text(
    "SELECT parent_id FROM pages WHERE id = CAST(:id AS uuid) "
    "AND deleted_at IS NULL FOR UPDATE"
)
_ANCESTORS = text(
    """
    WITH RECURSIVE chain(id, parent_id) AS (
        SELECT id, parent_id FROM pages WHERE id = CAST(:parent AS uuid)
        UNION
        SELECT p.id, p.parent_id FROM pages p JOIN chain c ON p.id = c.parent_id
    )
    SELECT EXISTS (SELECT 1 FROM chain WHERE id = CAST(:page AS uuid))
    """
)
# Trashed rows are included: `_NEXT_ORDER` counts them, and a restore lands
# the page back on its own index, which a live sibling must not have taken.
_SIBLING_SET = text(
    """
    SELECT id, order_index, deleted_at IS NULL AS live FROM pages
    WHERE project = :project
      AND parent_id IS NOT DISTINCT FROM CAST(:parent AS uuid)
    ORDER BY order_index, id
    """
)
_RENUMBER = text(
    """
    UPDATE pages p
    SET order_index = v.order_index,
        parent_id = CASE WHEN p.id = CAST(:mover AS uuid)
                         THEN CAST(:parent AS uuid) ELSE p.parent_id END
    FROM unnest(CAST(:ids AS uuid[]), CAST(:orders AS integer[]))
         AS v(id, order_index)
    WHERE p.id = v.id
    """
)
_RENAME = text(
    "UPDATE pages SET title = CAST(:title AS text) "
    "WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL RETURNING project"
)
_GET_PAGE = text(
    """
    SELECT id, project, parent_id, order_index, title, content, content_hash,
           properties
    FROM pages WHERE id = CAST(:id AS uuid) AND deleted_at IS NULL
    """
)
_GET_BLOCKS = text(
    """
    SELECT id, parent_id, order_index, type, text, properties,
           lower(char_span) AS char_start, upper(char_span) AS char_end
    FROM blocks WHERE page_id = CAST(:id AS uuid) ORDER BY order_index
    """
)
_LIST_PAGES = text(
    """
    SELECT id, project, parent_id, order_index, title, content_hash,
           properties, created_at, updated_at
    FROM pages WHERE project = :project AND deleted_at IS NULL
    ORDER BY parent_id, order_index
    """
)


def root_lock_key(project: str) -> str:
    """The advisory-lock key guarding every sibling-set write in `project`.

    Every writer of a page's `parent_id` or `order_index` -- a create at any
    depth, a move -- must take this exact key before any row lock, or two of
    them serialise against nothing and a move's cycle check becomes
    check-then-act.
    """
    return f"pages:{project}:root"


def _json(value) -> str | None:
    return None if value is None else json.dumps(value)


def _parse(content: str) -> list[TreeBlock]:
    drafts = parse_markdown(content)
    ids = [uuid4() for _ in drafts]
    tree: list[TreeBlock] = []
    for position, draft in enumerate(drafts):
        parent_id = None
        if draft.parent is not None:
            if not 0 <= draft.parent < position:
                raise ValueError(
                    f"block {position} names parent {draft.parent}: a parent "
                    "must be an earlier draft in the same sequence"
                )
            parent_id = ids[draft.parent]
        tree.append(TreeBlock(
            id=ids[position],
            parent_id=parent_id,
            order_index=position,
            type=normalize_block_type(draft.type),
            text=draft.text,
            properties=draft.properties,
        ))
    return tree


async def _claim_order_index(
    session: AsyncSession, *, project: str, parent_id: str | None,
    after_id: str | None,
) -> int:
    """The new page's slot, taken under a lock the sibling set shares.

    Without the lock two callers read one `max(order_index)` across an await
    and mint the same index; invariant 13's single worker does not help,
    because the requests interleave rather than run concurrently.
    """
    await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})
    if parent_id is not None:
        locked = (
            await session.execute(
                _LOCK_PARENT, {"id": parent_id, "project": project}
            )
        ).first()
        if locked is None:
            raise PageTargetUnresolved(
                f"no page with id {parent_id} in project {project!r} to "
                "file this page under"
            )

    if after_id is None:
        return (
            await session.execute(
                _NEXT_ORDER, {"project": project, "parent": parent_id}
            )
        ).scalar_one()

    sibling = (
        await session.execute(
            _SIBLING_ORDER,
            {"id": after_id, "project": project, "parent": parent_id},
        )
    ).scalar_one_or_none()
    if sibling is None:
        raise PageTargetUnresolved(
            f"no page with id {after_id} among the siblings this page would "
            "be filed beside"
        )
    order_index = sibling + 1
    await session.execute(_SHIFT_SIBLINGS, {
        "project": project, "parent": parent_id, "from_index": order_index,
    })
    return order_index


async def create_page(
    session: AsyncSession,
    llm,
    *,
    project: str,
    title: str | None,
    parent_id: str | None = None,
    after_id: str | None = None,
    content: str | None = None,
    properties: dict | None = None,
    actor: str | None = None,
) -> PageResult:
    if content is not None and len(content) > MAX_CONTENT_CHARS:
        raise PageTooLarge(
            f"content is {len(content)} characters; the bound is "
            f"{MAX_CONTENT_CHARS}"
        )

    page_id = uuid4()
    tree = _parse(content) if content else []
    serialized = serialize_tree(tree)
    stored_content = serialized.content
    content_hash = compute_content_hash(stored_content)
    placed = {p.block_id: p for p in serialized.placed}

    async with session.begin_nested():
        order_index = await _claim_order_index(
            session, project=project, parent_id=parent_id, after_id=after_id,
        )
        if len(tree) > MAX_BLOCKS:
            raise PageTooLarge(
                f"page parses to {len(tree)} blocks; the bound is "
                f"{MAX_BLOCKS} blocks"
            )
        await session.execute(_INSERT_PAGE, {
            "id": str(page_id),
            "project": project,
            "parent": parent_id,
            "order_index": order_index,
            "title": title,
            "content": stored_content,
            "content_hash": content_hash,
            "properties": _json(properties),
        })
        for block in tree:
            spot = placed[block.id]
            await session.execute(_INSERT_BLOCK, {
                "id": str(block.id),
                "page_id": str(page_id),
                "parent_id": None if block.parent_id is None else str(block.parent_id),
                "order_index": spot.order_index,
                "type": block.type,
                "text": block.text,
                "properties": _json(block.properties),
                "char_span": f"[{spot.char_span[0]},{spot.char_span[1]})",
            })
        # No block or title text in the payload: write-time minimization, and
        # a journal row outlives the page it describes.
        await record_event(
            session,
            event_type=PAGE_CREATED_EVENT,
            object_type="page",
            object_id=page_id,
            project=project,
            actor=actor,
            payload={
                "parent_id": parent_id,
                "order_index": order_index,
                "blocks_total": len(tree),
                "content_hash": content_hash,
            },
        )
    await session.commit()

    written = 0
    if tree:
        result = await embed_blocks(
            session, llm,
            block_ids=[str(block.id) for block in tree],
            parent=PAGE_PARENT_TABLE,
        )
        written = result.written if result else 0
        await session.commit()

    return PageResult(
        id=page_id,
        project=project,
        parent_id=None if parent_id is None else UUID(parent_id),
        order_index=order_index,
        title=title,
        content_hash=content_hash,
        blocks_written=len(tree),
        blocks_embedded=written,
    )


async def get_page(
    session: AsyncSession, page_id: str, *, include_content: bool = False,
) -> PageView:
    """One live page and its blocks in `order_index` order.

    `content` is withheld unless asked for: it duplicates every block's text
    and no reader that renders the tree needs it.
    """
    row = (
        await session.execute(_GET_PAGE, {"id": page_id})
    ).mappings().first()
    if row is None:
        raise PageTargetUnresolved(f"no live page with id {page_id}")
    blocks = (
        await session.execute(_GET_BLOCKS, {"id": page_id})
    ).mappings().all()
    return PageView(
        id=row["id"],
        project=row["project"],
        parent_id=row["parent_id"],
        order_index=row["order_index"],
        title=row["title"],
        content_hash=row["content_hash"],
        properties=row["properties"],
        blocks=[dict(block) for block in blocks],
        content=row["content"] if include_content else None,
    )


async def list_pages(session: AsyncSession, project: str) -> list[dict]:
    """Every live page in `project` as flat rows; the client nests them.

    `content` is excluded rather than trimmed by the caller: a tree read of a
    whole project would otherwise carry every page's full source.
    """
    rows = (
        await session.execute(_LIST_PAGES, {"project": project})
    ).mappings().all()
    return [dict(row) for row in rows]


async def move_page(
    session: AsyncSession,
    page_id: str,
    *,
    parent_id: str | None,
    after_id: str | None = None,
    actor: str | None = None,
) -> None:
    """Reparent and place a page after `after_id`, or first when it is None.

    Takes a sibling rather than an index so a reorder never has to know the
    indices a concurrent writer is about to shift.
    """
    # Membership below is decided by comparing id strings.
    page_id = str(UUID(page_id))
    parent_id = None if parent_id is None else str(UUID(parent_id))
    after_id = None if after_id is None else str(UUID(after_id))
    project = (
        await session.execute(_MOVED_PAGE, {"id": page_id})
    ).scalar_one_or_none()
    if project is None:
        raise PageTargetUnresolved(f"no live page with id {page_id}")

    async with session.begin_nested():
        await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})
        locked = (
            await session.execute(_LOCK_MOVED_PAGE, {"id": page_id})
        ).first()
        if locked is None:
            raise PageTargetUnresolved(f"no live page with id {page_id}")
        from_parent = None if locked.parent_id is None else str(locked.parent_id)

        if parent_id is not None:
            found = (
                await session.execute(
                    _LOCK_PARENT, {"id": parent_id, "project": project}
                )
            ).first()
            if found is None:
                raise PageTargetUnresolved(
                    f"no page with id {parent_id} in project {project!r} to "
                    "move this page under"
                )
            cycle = (
                await session.execute(
                    _ANCESTORS, {"parent": parent_id, "page": page_id}
                )
            ).scalar_one()
            if cycle:
                raise PageCycleError(
                    f"page {parent_id} is page {page_id} or lies inside its "
                    "subtree"
                )

        new_set = [
            row for row in (
                await session.execute(
                    _SIBLING_SET, {"project": project, "parent": parent_id}
                )
            ).all()
            if str(row.id) != page_id
        ]
        if after_id is None:
            slot = 0
        else:
            slot = next(
                (i + 1 for i, row in enumerate(new_set)
                 if str(row.id) == after_id and row.live),
                None,
            )
            if slot is None:
                raise PageTargetUnresolved(
                    f"no live page with id {after_id} among the siblings this "
                    "page would move beside"
                )
        ordered = [str(row.id) for row in new_set]
        ordered.insert(slot, page_id)
        placement = {pid: index for index, pid in enumerate(ordered)}

        if from_parent != parent_id:
            old_set = (
                await session.execute(
                    _SIBLING_SET, {"project": project, "parent": from_parent}
                )
            ).all()
            survivors = [str(row.id) for row in old_set if str(row.id) != page_id]
            placement.update({pid: index for index, pid in enumerate(survivors)})

        await session.execute(_RENUMBER, {
            "mover": page_id,
            "parent": parent_id,
            "ids": list(placement),
            "orders": list(placement.values()),
        })
        await record_event(
            session,
            event_type=PAGE_MOVED_EVENT,
            object_type="page",
            object_id=UUID(page_id),
            project=project,
            actor=actor,
            payload={
                "from_parent_id": from_parent,
                "to_parent_id": parent_id,
                "order_index": slot,
            },
        )
    await session.commit()


async def rename_page(
    session: AsyncSession,
    page_id: str,
    *,
    title: str | None,
    actor: str | None = None,
) -> None:
    """Set a live page's title.

    Last-writer-wins and deliberately without `expected_hash`: the hash covers
    `content`, which a title does not change, so a precondition on it would
    refuse nothing a concurrent rename could lose.
    """
    project = (
        await session.execute(_RENAME, {"id": page_id, "title": title})
    ).scalar_one_or_none()
    if project is None:
        raise PageTargetUnresolved(f"no live page with id {page_id}")
    await record_event(
        session,
        event_type=PAGE_UPDATED_EVENT,
        object_type="page",
        object_id=UUID(page_id),
        project=project,
        actor=actor,
        payload={"fields": ["title"]},
    )
    await session.commit()
