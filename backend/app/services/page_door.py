"""The page door: create, read, move, rename and trash (spec 2026-09-08, §7).

A page is block-first by construction: `create_page` parses the caller's
content, writes the blocks, and stores the *serialiser's* output as
`content` rather than the caller's text. Nothing else keeps that true --
`block_verbs._PAGE_META` reports every page as already converted, so a page
that carried an authored source would never be reconciled with its blocks
and could never be refused either.

Nothing here embeds. A new page block has no vector, and the hourly
`block_embedding_refresh` sweep's page arm fills it, so a create costs no
embedder call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, replace
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.block_serializer import TreeBlock, reproduces_source, serialize_tree
from app.services.document_ingest import compute_content_hash
from app.services.document_parsers import parse_markdown, split_frontmatter
from app.services.events import record_event
from app.taxonomy import normalize_block_type

__all__ = [
    "MAX_BLOCKS",
    "MAX_CONTENT_CHARS",
    "PAGE_CREATED_EVENT",
    "PAGE_DELETED_EVENT",
    "PAGE_MOVED_EVENT",
    "PAGE_PURGED_EVENT",
    "PAGE_RESTORED_EVENT",
    "PAGE_UPDATED_EVENT",
    "PageCycleError",
    "PageJournalWriteFailed",
    "PageNotRepresentable",
    "PageParentTrashed",
    "PageResult",
    "PageTargetUnresolved",
    "PageTooLarge",
    "PageView",
    "create_page",
    "delete_page",
    "get_page",
    "list_pages",
    "list_trash",
    "move_page",
    "purge_trash",
    "rename_page",
    "restore_page",
    "root_lock_key",
]

MAX_CONTENT_CHARS = 1_000_000
MAX_BLOCKS = 5_000

PAGE_CREATED_EVENT = "page_created"
PAGE_MOVED_EVENT = "page_moved"
PAGE_UPDATED_EVENT = "page_updated"
PAGE_DELETED_EVENT = "page_deleted"
PAGE_RESTORED_EVENT = "page_restored"
PAGE_PURGED_EVENT = "page_purged"


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


class PageNotRepresentable(ValueError):
    """The content carries source the block tree cannot hold.

    A page stores the serialiser's regeneration, so accepting a frontmatter
    fence or a link-reference definition would drop it with a success.
    """


class PageParentTrashed(ValueError):
    """A restore named a page whose parent is still in the trash."""


class PageJournalWriteFailed(RuntimeError):
    """A trash or purge journal row did not land, so nothing was written.

    Local rather than the vault repository's `JournalWriteFailed`: the page
    door reads block rows, and the block channel stays off the vault's
    modules.
    """


@dataclass(frozen=True)
class PageResult:
    id: UUID
    project: str
    parent_id: UUID | None
    order_index: int
    title: str | None
    content_hash: str
    blocks_written: int


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
# `source` is sliced server-side the way `document_door._BLOCKS` slices it, so
# an editor reading one page does not also fetch and slice `content` itself.
_GET_BLOCKS = text(
    """
    SELECT b.id, b.parent_id, b.order_index, b.type, b.text, b.properties,
           lower(b.char_span) AS char_start, upper(b.char_span) AS char_end,
           substring(p.content
                     FROM lower(b.char_span) + 1
                     FOR upper(b.char_span) - lower(b.char_span)) AS source
    FROM blocks b
    JOIN pages p ON p.id = b.page_id
    WHERE b.page_id = CAST(:id AS uuid)
    ORDER BY b.order_index
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

# A trashed page whose parent is also trashed is shown through that parent:
# restoring it alone is refused while the parent stays in the trash.
_TRASH_ROOTS = text(
    """
    SELECT p.id, p.title, p.parent_id, p.deleted_at
    FROM pages p
    LEFT JOIN pages parent ON parent.id = p.parent_id
    WHERE p.project = :project
      AND p.deleted_at IS NOT NULL
      AND (p.parent_id IS NULL OR parent.deleted_at IS NULL)
    ORDER BY p.deleted_at DESC, p.id
    """
)


_TRASH_TARGET = text(
    "SELECT project FROM pages WHERE id = CAST(:id AS uuid) "
    "AND (deleted_at IS NULL) = CAST(:live AS boolean)"
)
_LOCK_TRASH_TARGET = text(
    "SELECT parent_id, deleted_at FROM pages WHERE id = CAST(:id AS uuid) "
    "AND (deleted_at IS NULL) = CAST(:live AS boolean) FOR UPDATE"
)
_LIVE_SUBTREE = text(
    """
    WITH RECURSIVE subtree(id) AS (
        SELECT id FROM pages WHERE id = CAST(:id AS uuid)
        UNION
        SELECT p.id FROM pages p JOIN subtree s ON p.parent_id = s.id
        WHERE p.deleted_at IS NULL
    )
    SELECT CAST(id AS text) AS id FROM subtree ORDER BY id
    """
)
# Only rows carrying the restored page's own stamp: a descendant trashed on
# its own earlier, and everything under it, stays in the trash.
_STAMPED_SUBTREE = text(
    """
    WITH RECURSIVE subtree(id) AS (
        SELECT id FROM pages WHERE id = CAST(:id AS uuid)
        UNION
        SELECT p.id FROM pages p JOIN subtree s ON p.parent_id = s.id
        WHERE p.deleted_at = CAST(:stamp AS timestamptz)
    )
    SELECT CAST(id AS text) AS id FROM subtree ORDER BY id
    """
)
_PARENT_TRASHED = text(
    "SELECT deleted_at IS NOT NULL FROM pages WHERE id = CAST(:id AS uuid)"
)
_STAMP = text(
    "UPDATE pages SET deleted_at = now() WHERE id = ANY(CAST(:ids AS uuid[]))"
)
_UNSTAMP = text(
    "UPDATE pages SET deleted_at = NULL WHERE id = ANY(CAST(:ids AS uuid[]))"
)
_TRASHED_IN_PROJECT = text(
    "SELECT CAST(id AS text) AS id FROM pages "
    "WHERE project = :project AND deleted_at IS NOT NULL ORDER BY id FOR UPDATE"
)
_PURGE = text(
    "DELETE FROM pages WHERE project = :project AND deleted_at IS NOT NULL"
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


def _flatten_headings(tree: list[TreeBlock]) -> list[TreeBlock]:
    """Re-parent each heading's children onto its nearest non-heading
    ancestor, keeping reading order.

    The parser nests everything under the nearest open heading, but a page
    holds children only under list, todo and toggle blocks. A heading adds no
    child prefix, so the serialisation is unchanged for headings at the root
    or inside a quote -- except where a heading inside a list item adopts a
    later sibling item, which flattening turns into a tight nested item.
    """
    by_id = {block.id: block for block in tree}
    children: dict[UUID | None, list[TreeBlock]] = {}
    for block in tree:
        children.setdefault(block.parent_id, []).append(block)
    for siblings in children.values():
        siblings.sort(key=lambda b: (b.order_index, str(b.id)))

    reading_order: list[TreeBlock] = []
    stack = list(reversed(children.get(None, [])))
    while stack:
        block = stack.pop()
        reading_order.append(block)
        stack.extend(reversed(children.get(block.id, [])))

    flat: list[TreeBlock] = []
    for position, block in enumerate(reading_order):
        parent = block.parent_id
        while parent is not None and by_id[parent].type == "heading":
            parent = by_id[parent].parent_id
        flat.append(replace(block, parent_id=parent, order_index=position))
    return flat


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
    tree = _flatten_headings(_parse(content)) if content else []
    if content and (
        split_frontmatter(content)[0] is not None
        or not reproduces_source(tree, content, {})
    ):
        raise PageNotRepresentable(
            "this content carries source a page cannot represent (a leading "
            "frontmatter fence or a link-reference definition); a page stores "
            "its blocks' serialisation, so filing it would drop that source"
        )
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

    return PageResult(
        id=page_id,
        project=project,
        parent_id=None if parent_id is None else UUID(parent_id),
        order_index=order_index,
        title=title,
        content_hash=content_hash,
        blocks_written=len(tree),
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


async def list_trash(session: AsyncSession, project: str) -> list[dict]:
    """The roots of `project`'s trashed subtrees, most recently trashed first.

    A read: it takes no lock, so the read-only worker can serve it.
    """
    rows = (
        await session.execute(_TRASH_ROOTS, {"project": project})
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
    page_id = str(UUID(page_id))
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


async def _journal_each(
    session: AsyncSession, ids: list[str], *, event_type: str, project: str,
    actor: str | None, payload: dict,
) -> None:
    for page_id in ids:
        landed = await record_event(
            session,
            event_type=event_type,
            object_type="page",
            object_id=UUID(page_id),
            project=project,
            actor=actor,
            payload=dict(payload),
        )
        if not landed:
            raise PageJournalWriteFailed(
                f"{event_type} did not land for page {page_id}; refusing to "
                "write unaudited"
            )


async def _lock_trash_target(
    session: AsyncSession, page_id: str, *, live: bool,
):
    """The target's project tree lock, then the target row under it.

    The tree lock comes first so a move cannot add a page to the subtree
    between its enumeration and its write, which would leave a page stamped
    or restored with no journal row.
    """
    missing = PageTargetUnresolved(
        f"no {'live' if live else 'trashed'} page with id {page_id}"
    )
    project = (
        await session.execute(_TRASH_TARGET, {"id": page_id, "live": live})
    ).scalar_one_or_none()
    if project is None:
        raise missing
    await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})
    locked = (
        await session.execute(_LOCK_TRASH_TARGET, {"id": page_id, "live": live})
    ).first()
    if locked is None:
        raise missing
    return project, locked


async def delete_page(
    session: AsyncSession, page_id: str, *, actor: str | None = None,
) -> int:
    """Move a live page and its live subtree to the trash; returns the count.

    A stamp rather than a `DELETE`: a page's row is its only copy, where a
    document can be re-filed by the agent that filed it.
    """
    page_id = str(UUID(page_id))
    async with session.begin_nested():
        project, _ = await _lock_trash_target(session, page_id, live=True)
        ids = [
            row.id for row in
            (await session.execute(_LIVE_SUBTREE, {"id": page_id})).all()
        ]
        await _journal_each(
            session, ids, event_type=PAGE_DELETED_EVENT, project=project,
            actor=actor, payload={"root_id": page_id},
        )
        # One statement, so every row of the subtree carries one stamp value;
        # the restore matches on that value.
        await session.execute(_STAMP, {"ids": ids})
    await session.commit()
    return len(ids)


async def restore_page(
    session: AsyncSession, page_id: str, *, actor: str | None = None,
) -> int:
    """Take a trashed page, and what was trashed with it, out of the trash.

    Refused while the parent is trashed: the restored page would be live but
    unreachable from `list_pages`, and the next purge's cascade would erase it.
    """
    page_id = str(UUID(page_id))
    async with session.begin_nested():
        project, locked = await _lock_trash_target(session, page_id, live=False)
        if locked.parent_id is not None:
            trashed = (
                await session.execute(
                    _PARENT_TRASHED, {"id": str(locked.parent_id)}
                )
            ).scalar_one()
            if trashed:
                raise PageParentTrashed(
                    f"page {page_id} sits under trashed page "
                    f"{locked.parent_id}; restore that page first"
                )
        ids = [
            row.id for row in (
                await session.execute(
                    _STAMPED_SUBTREE,
                    {"id": page_id, "stamp": locked.deleted_at},
                )
            ).all()
        ]
        await _journal_each(
            session, ids, event_type=PAGE_RESTORED_EVENT, project=project,
            actor=actor, payload={"root_id": page_id},
        )
        await session.execute(_UNSTAMP, {"ids": ids})
    await session.commit()
    return len(ids)


async def purge_trash(
    session: AsyncSession, project: str, *, actor: str | None = None,
) -> int:
    """Erase every trashed page in `project`; returns the rows deleted.

    Blocks and their vectors go with the rows through `blocks.page_id`'s
    cascade. Irrecoverable, so a journal row that does not land refuses the
    whole purge before the `DELETE` runs.
    """
    async with session.begin_nested():
        await session.execute(_LOCK_ROOT, {"key": root_lock_key(project)})
        ids = [
            row.id for row in (
                await session.execute(_TRASHED_IN_PROJECT, {"project": project})
            ).all()
        ]
        await _journal_each(
            session, ids, event_type=PAGE_PURGED_EVENT, project=project,
            actor=actor, payload={},
        )
        deleted = (await session.execute(_PURGE, {"project": project})).rowcount
    await session.commit()
    return deleted
