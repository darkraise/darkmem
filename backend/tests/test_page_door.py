"""The page door: create, read, move, rename and trash (spec 2026-09-08, §7)."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.block_embedding_refresh import refresh_block_embeddings
from app.services.block_serializer import serialize_tree
from app.services.document_ingest import compute_content_hash
from app.services.page_door import (
    PageCycleError,
    PageJournalWriteFailed,
    PageNotRepresentable,
    PageParentTrashed,
    PageTargetUnresolved,
    _flatten_headings,
    _parse,
    create_page,
    delete_page,
    get_page,
    list_pages,
    list_trash,
    move_page,
    purge_trash,
    rename_page,
    restore_page,
)


FINGERPRINT = "test-fp-pages|3"


@pytest.fixture(autouse=True)
def _forget_probe_fingerprint():
    """`EmbedderRegistry` caches known fingerprints process-wide while each
    test's writes roll back at teardown, so a later test would skip
    registering a fingerprint whose child table no longer exists."""
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    yield
    embedder_registry.forget(FINGERPRINT)


class StubEmbedder:
    def __init__(self, fingerprint: str = FINGERPRINT):
        self.fingerprint = fingerprint
        self.batches: list[list[str]] = []

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        self.batches.append(list(texts))
        return ([[1.0, 0.0, 0.0] for _ in texts], self.fingerprint)

    async def embed(self, value: str):
        return [1.0, 0.0, 0.0], self.fingerprint

    def llm_fingerprint(self) -> str:
        return self.fingerprint


@pytest.fixture
def llm():
    return StubEmbedder()


async def _blocks_of(session, page_id):
    rows = await session.execute(
        text(
            "SELECT type, text, order_index FROM blocks "
            "WHERE page_id = CAST(:id AS uuid) ORDER BY order_index"
        ),
        {"id": str(page_id)},
    )
    return [dict(r) for r in rows.mappings().all()]


async def _page_row(session, page_id):
    row = await session.execute(
        text("SELECT * FROM pages WHERE id = CAST(:id AS uuid)"),
        {"id": str(page_id)},
    )
    return dict(row.mappings().one())


@pytest.mark.asyncio
async def test_a_child_requires_its_parent_to_exist(session, llm):
    """The Notion invariant, and the reason pages are not documents: a
    document files to any path unconditionally, a page does not."""
    with pytest.raises(PageTargetUnresolved):
        await create_page(session, llm, project="p", title="orphan",
                          parent_id=str(uuid4()))


@pytest.mark.asyncio
async def test_creating_with_content_parses_it_into_blocks(session, llm):
    """Without this path the first caller writes `content` straight onto the
    row and recreates content-first state on an object with no conversion
    pass."""
    page = await create_page(session, llm, project="p", title="n",
                             content="# Title\n\nA paragraph.\n")
    blocks = await _blocks_of(session, page.id)
    assert [b["type"] for b in blocks] == ["heading", "paragraph"]


@pytest.mark.asyncio
async def test_the_stored_content_is_the_serialiser_output(session, llm):
    """`content` is regenerated rather than stored verbatim, which is what
    keeps a page block-first and means no conversion is ever owed."""
    page = await create_page(session, llm, project="p", title="n",
                             content="#   Title\n")
    row = await _page_row(session, page.id)
    assert row["content"] == "# Title"


@pytest.mark.parametrize("content", [
    "See [the spec][ref].\n\n[ref]: https://example.com/spec\n",
    "---\ntitle: x\n---\n\nbody\n",
])
@pytest.mark.asyncio
async def test_content_the_tree_cannot_hold_is_refused(session, llm, content):
    """The stored content is the tree's regeneration, so a link-reference
    definition or a frontmatter fence would vanish behind a success."""
    with pytest.raises(PageNotRepresentable):
        await create_page(session, llm, project="p-unrep", title="n",
                          content=content)
    count = (
        await session.execute(
            text("SELECT count(*) FROM pages WHERE project = 'p-unrep'")
        )
    ).scalar_one()
    assert count == 0


@pytest.mark.asyncio
async def test_create_page_checks_reproduction_off_the_loop(session, llm, monkeypatch):
    import threading

    from app.services import page_door

    loop_thread = threading.current_thread()
    seen: list[threading.Thread] = []
    real = page_door.reproduces_source

    def recording(*args, **kwargs):
        seen.append(threading.current_thread())
        return real(*args, **kwargs)

    monkeypatch.setattr(page_door, "reproduces_source", recording)
    await create_page(session, llm, project="p", title="t", content="# A\n\nBody.\n")

    assert seen and all(thread is not loop_thread for thread in seen)


async def test_siblings_are_appended_in_dense_order(session, llm):
    a = await create_page(session, llm, project="p", title="a")
    b = await create_page(session, llm, project="p", title="b")
    assert [p.order_index for p in (a, b)] == [0, 1]


@pytest.mark.asyncio
async def test_an_empty_page_has_a_hash_to_precondition_against(session, llm):
    """NOT NULL with the create route writing compute_content_hash(''): a NULL
    would leave the first `expected_hash` a client sends nothing to compare
    against."""
    page = await create_page(session, llm, project="p", title="n")
    row = await _page_row(session, page.id)
    assert row["content"] == ""
    assert row["content_hash"] == compute_content_hash("")


@pytest.mark.asyncio
async def test_the_list_excludes_trashed_pages_and_content(session, llm):
    kept = await create_page(session, llm, project="p", title="kept")
    trashed = await create_page(session, llm, project="p", title="trashed")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(trashed.id)},
    )
    rows = await list_pages(session, "p")
    assert [r["title"] for r in rows] == ["kept"]
    assert str(rows[0]["id"]) == str(kept.id)
    assert all("content" not in r for r in rows)


@pytest.mark.asyncio
async def test_the_keyed_read_serves_blocks_and_withholds_content(session, llm):
    page = await create_page(session, llm, project="p", title="n",
                             content="# T\n\nbody\n")
    bare = await get_page(session, str(page.id))
    assert bare.content is None
    assert [b["type"] for b in bare.blocks] == ["heading", "paragraph"]
    full = await get_page(session, str(page.id), include_content=True)
    assert full.content == "# T\n\nbody"


@pytest.mark.asyncio
async def test_the_keyed_read_refuses_a_trashed_page(session, llm):
    page = await create_page(session, llm, project="p", title="n")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(page.id)},
    )
    with pytest.raises(PageTargetUnresolved):
        await get_page(session, str(page.id))


@pytest.mark.asyncio
async def test_a_page_embeds_into_the_page_partition(session, llm):
    """Sharing `block_embeddings__<slug>` would put page vectors in an index
    whose owner filter runs after the scan."""
    from app.services.embedder_registry import child_table

    page = await create_page(session, llm, project="p", title="n",
                             content="# T\n\nbody\n")
    outcome = await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    assert outcome.embedded == 2
    table = child_table("page_embeddings", FINGERPRINT)
    count = (
        await session.execute(
            text(
                f"SELECT count(*) FROM {table} e JOIN blocks b ON b.id = e.block_id "
                "WHERE b.page_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert count == 2
    shared = child_table("block_embeddings", FINGERPRINT)
    leaked = (
        await session.execute(
            text(
                f"SELECT count(*) FROM {shared} e JOIN blocks b ON b.id = e.block_id "
                "WHERE b.page_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert leaked == 0


@pytest.mark.asyncio
async def test_after_id_inserts_between_its_siblings(session, llm):
    a = await create_page(session, llm, project="p", title="a")
    c = await create_page(session, llm, project="p", title="c")
    b = await create_page(session, llm, project="p", title="b",
                          after_id=str(a.id))
    rows = await list_pages(session, "p")
    assert [r["title"] for r in rows] == ["a", "b", "c"]
    assert b.order_index == 1
    assert [r["order_index"] for r in rows] == [0, 1, 2]
    assert str(c.id) == str(rows[2]["id"])


@pytest.mark.asyncio
async def test_a_child_is_ordered_within_its_own_parent(session, llm):
    """`order_index` is dense per `(project, parent_id)`, not per project, so
    a first child sits at 0 beside roots that already reach 1."""
    first = await create_page(session, llm, project="p", title="first")
    second = await create_page(session, llm, project="p", title="second")
    child = await create_page(session, llm, project="p", title="child",
                              parent_id=str(first.id))
    assert [first.order_index, second.order_index] == [0, 1]
    assert child.order_index == 0
    assert str(child.parent_id) == str(first.id)

    row = await _page_row(session, child.id)
    assert str(row["parent_id"]) == str(first.id)
    assert row["order_index"] == 0

    rows = await list_pages(session, "p")
    by_title = {r["title"]: r for r in rows}
    assert by_title["child"]["order_index"] == 0
    assert str(by_title["child"]["parent_id"]) == str(first.id)
    assert by_title["first"]["parent_id"] is None
    # NULLs sort last under Postgres' default ASC ordering, so the two roots
    # follow the child rather than leading it.
    assert [r["title"] for r in rows] == ["child", "first", "second"]

    sibling = await create_page(session, llm, project="p", title="sibling",
                                parent_id=str(first.id))
    assert sibling.order_index == 1


async def _children(session, project, parent_id):
    rows = await session.execute(
        text(
            "SELECT id, title, order_index FROM pages WHERE project = :project "
            "AND parent_id IS NOT DISTINCT FROM CAST(:parent AS uuid) "
            "ORDER BY order_index"
        ),
        {"project": project,
         "parent": None if parent_id is None else str(parent_id)},
    )
    return [dict(r) for r in rows.mappings().all()]


@pytest.mark.asyncio
async def test_a_page_cannot_be_moved_into_its_own_subtree(session, llm):
    root = await create_page(session, llm, project="p", title="root")
    child = await create_page(session, llm, project="p", title="child",
                              parent_id=str(root.id))
    grandchild = await create_page(session, llm, project="p", title="gc",
                                   parent_id=str(child.id))
    with pytest.raises(PageCycleError):
        await move_page(session, str(root.id), parent_id=str(child.id))
    with pytest.raises(PageCycleError):
        await move_page(session, str(root.id), parent_id=str(grandchild.id))
    with pytest.raises(PageCycleError):
        await move_page(session, str(root.id), parent_id=str(root.id))


@pytest.mark.asyncio
async def test_two_concurrent_moves_cannot_orphan_a_subtree(monkeypatch, llm):
    """Each move walks ancestors against the committed tree, so without a lock
    both pass their own check and both commit, leaving A under B and B under A
    -- unreachable from every root. Invariant 13's single worker does not help:
    the two requests interleave across awaits."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services import page_door
    from tests.conftest import test_engine

    async def _journal(*args, **kwargs):
        return True

    monkeypatch.setattr("app.services.page_door.record_event", _journal)
    project = f"concurrent-move-{uuid4()}"
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    try:
        async with factory() as setup:
            a = await create_page(setup, llm, project=project, title="a")
            b = await create_page(setup, llm, project=project, title="b")

        async with factory() as first, factory() as second:
            # Asyncio scheduling alone does not interleave the two moves
            # reliably, so each holds at the parent lookup -- after locking its
            # own page -- until the other arrives. Under the tree lock the
            # other is parked in Postgres and never arrives; the timeout lets
            # the holder go on alone, which is the serial order the lock buys.
            arrived = {first: asyncio.Event(), second: asyncio.Event()}
            for mine, theirs in ((first, second), (second, first)):
                original = mine.execute

                async def execute(statement, *args, _original=original,
                                  _mine=mine, _theirs=theirs, **kwargs):
                    if statement is page_door._LOCK_PARENT:
                        arrived[_mine].set()
                        try:
                            await asyncio.wait_for(arrived[_theirs].wait(), 2)
                        except asyncio.TimeoutError:
                            pass
                    return await _original(statement, *args, **kwargs)

                mine.execute = execute
            results = await asyncio.gather(
                move_page(first, str(a.id), parent_id=str(b.id)),
                move_page(second, str(b.id), parent_id=str(a.id)),
                return_exceptions=True,
            )

        # Without this the barrier can stop matching unnoticed, and the
        # timing-only version passes with the tree lock removed.
        assert any(e.is_set() for e in arrived.values()), "barrier never fired"
        refused = [r for r in results if isinstance(r, PageCycleError)]
        others = [r for r in results if not isinstance(r, PageCycleError)]
        assert len(refused) == 1, results
        assert len(others) == 1 and not isinstance(others[0], BaseException), results

        async with factory() as check:
            rows = (
                await check.execute(
                    text("SELECT id, parent_id FROM pages WHERE project = :p"),
                    {"p": project},
                )
            ).mappings().all()
        parents = {str(r["id"]): r["parent_id"] for r in rows}
        roots = [pid for pid, parent in parents.items() if parent is None]
        assert len(roots) == 1, parents
        (other,) = [pid for pid in parents if pid != roots[0]]
        assert str(parents[other]) == roots[0]
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM pages WHERE project = :p"), {"p": project}
            )
            await cleanup.commit()


@pytest.mark.asyncio
async def test_a_move_renumbers_both_sibling_sets_densely(session, llm):
    x = await create_page(session, llm, project="p", title="x")
    y = await create_page(session, llm, project="p", title="y")
    x0 = await create_page(session, llm, project="p", title="x0", parent_id=str(x.id))
    mover = await create_page(session, llm, project="p", title="x1",
                              parent_id=str(x.id))
    await create_page(session, llm, project="p", title="x2", parent_id=str(x.id))
    y0 = await create_page(session, llm, project="p", title="y0", parent_id=str(y.id))
    await create_page(session, llm, project="p", title="y1", parent_id=str(y.id))

    await move_page(session, str(mover.id), parent_id=str(y.id),
                    after_id=str(y0.id))

    xs = await _children(session, "p", x.id)
    assert [(r["title"], r["order_index"]) for r in xs] == [("x0", 0), ("x2", 1)]
    ys = await _children(session, "p", y.id)
    assert [(r["title"], r["order_index"]) for r in ys] == [
        ("y0", 0), ("x1", 1), ("y1", 2),
    ]
    assert str(x0.id) == str(xs[0]["id"])


@pytest.mark.asyncio
async def test_a_move_within_one_parent_reorders_one_set(session, llm):
    a = await create_page(session, llm, project="p", title="a")
    await create_page(session, llm, project="p", title="b")
    c = await create_page(session, llm, project="p", title="c")
    await move_page(session, str(a.id).upper(), parent_id=None,
                    after_id=str(c.id).upper())
    roots = await _children(session, "p", None)
    assert [(r["title"], r["order_index"]) for r in roots] == [
        ("b", 0), ("c", 1), ("a", 2),
    ]


@pytest.mark.asyncio
async def test_a_trashed_sibling_stays_in_the_renumber(session, llm):
    """A trashed page is renumbered with its live siblings rather than skipped,
    so no live sibling can be handed the index it will reclaim on restore. Its
    index may move -- here 1 to 2 -- but never collides."""
    a = await create_page(session, llm, project="p", title="a")
    trashed = await create_page(session, llm, project="p", title="t")
    c = await create_page(session, llm, project="p", title="c")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(trashed.id)},
    )
    await move_page(session, str(c.id), parent_id=None, after_id=str(a.id))
    roots = await _children(session, "p", None)
    assert [(r["title"], r["order_index"]) for r in roots] == [
        ("a", 0), ("c", 1), ("t", 2),
    ]


@pytest.mark.asyncio
async def test_after_id_null_places_first(session, llm):
    parent = await create_page(session, llm, project="p", title="parent")
    await create_page(session, llm, project="p", title="c0", parent_id=str(parent.id))
    await create_page(session, llm, project="p", title="c1", parent_id=str(parent.id))
    mover = await create_page(session, llm, project="p", title="m")
    await move_page(session, str(mover.id), parent_id=str(parent.id))
    children = await _children(session, "p", parent.id)
    assert [(r["title"], r["order_index"]) for r in children] == [
        ("m", 0), ("c0", 1), ("c1", 2),
    ]
    roots = await _children(session, "p", None)
    assert [(r["title"], r["order_index"]) for r in roots] == [("parent", 0)]


@pytest.mark.asyncio
async def test_a_move_refuses_a_trashed_or_foreign_parent(session, llm):
    mover = await create_page(session, llm, project="p", title="m")
    foreign = await create_page(session, llm, project="other", title="f")
    trashed = await create_page(session, llm, project="p", title="t")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(trashed.id)},
    )
    with pytest.raises(PageTargetUnresolved):
        await move_page(session, str(mover.id), parent_id=str(foreign.id))
    with pytest.raises(PageTargetUnresolved):
        await move_page(session, str(mover.id), parent_id=str(trashed.id))


@pytest.mark.asyncio
async def test_a_move_refuses_an_after_id_outside_the_new_set(session, llm):
    parent = await create_page(session, llm, project="p", title="parent")
    mover = await create_page(session, llm, project="p", title="m")
    stranger = await create_page(session, llm, project="p", title="s")
    with pytest.raises(PageTargetUnresolved):
        await move_page(session, str(mover.id), parent_id=str(parent.id),
                        after_id=str(stranger.id))
    with pytest.raises(PageTargetUnresolved):
        await move_page(session, str(mover.id), parent_id=None,
                        after_id=str(mover.id))


@pytest.mark.asyncio
async def test_a_move_journals_placement_without_text(session, llm):
    parent = await create_page(session, llm, project="p", title="parent")
    mover = await create_page(session, llm, project="p", title="secret title")
    await move_page(session, str(mover.id), parent_id=str(parent.id))
    payload = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'page_moved' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": str(mover.id)},
        )
    ).scalar_one()
    assert payload == {
        "from_parent_id": None,
        "to_parent_id": str(parent.id),
        "order_index": 0,
    }


@pytest.mark.asyncio
async def test_rename_updates_the_title_and_journals(session, llm):
    page = await create_page(session, llm, project="p", title="old")
    await rename_page(session, str(page.id), title="new")
    assert (await _page_row(session, page.id))["title"] == "new"
    count = (
        await session.execute(
            text(
                "SELECT count(*) FROM events WHERE event_type = 'page_updated' "
                "AND object_id = CAST(:id AS uuid)"
            ),
            {"id": str(page.id)},
        )
    ).scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_rename_refuses_a_trashed_page(session, llm):
    page = await create_page(session, llm, project="p", title="old")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(page.id)},
    )
    with pytest.raises(PageTargetUnresolved):
        await rename_page(session, str(page.id), title="new")


async def _stamps(session, page_ids):
    rows = await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, deleted_at FROM pages "
            "WHERE id = ANY(CAST(:ids AS uuid[]))"
        ),
        {"ids": [str(i) for i in page_ids]},
    )
    return {r["id"]: r["deleted_at"] for r in rows.mappings().all()}


async def _journalled(session, event_type):
    rows = await session.execute(
        text(
            "SELECT CAST(object_id AS text) AS id FROM events "
            "WHERE event_type = :t AND object_type = 'page'"
        ),
        {"t": event_type},
    )
    return sorted(r["id"] for r in rows.mappings().all())


async def _tree(session, llm, project="p"):
    root = await create_page(session, llm, project=project, title="root")
    child = await create_page(session, llm, project=project, title="child",
                              parent_id=str(root.id))
    grandchild = await create_page(session, llm, project=project, title="gc",
                                   parent_id=str(child.id))
    sibling = await create_page(session, llm, project=project, title="sibling")
    return root, child, grandchild, sibling


@pytest.mark.asyncio
async def test_deleting_a_page_stamps_its_whole_subtree(session, llm):
    """A page's only copy is the row -- unlike a document, which the agent
    that filed it can re-file. That asymmetry is why this is a stamp."""
    root, child, grandchild, sibling = await _tree(session, llm)
    await delete_page(session, str(root.id))

    stamps = await _stamps(session, [root.id, child.id, grandchild.id, sibling.id])
    assert stamps[str(sibling.id)] is None
    subtree = {stamps[str(p.id)] for p in (root, child, grandchild)}
    assert None not in subtree and len(subtree) == 1
    assert [r["title"] for r in await list_pages(session, "p")] == ["sibling"]
    with pytest.raises(PageTargetUnresolved):
        await delete_page(session, str(root.id))
    with pytest.raises(PageTargetUnresolved):
        await delete_page(session, str(uuid4()))


@pytest.mark.asyncio
async def test_a_trashed_subtree_restores_whole(session, llm):
    root, child, grandchild, _ = await _tree(session, llm)
    solo = await create_page(session, llm, project="p", title="solo",
                             parent_id=str(child.id))
    # Every statement in a test shares one transaction and therefore one
    # now(), so an earlier, separate trashing is stamped by hand.
    await session.execute(
        text(
            "UPDATE pages SET deleted_at = now() - interval '1 hour' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(solo.id)},
    )
    await delete_page(session, str(root.id))
    await restore_page(session, str(root.id))

    stamps = await _stamps(session, [root.id, child.id, grandchild.id, solo.id])
    assert [stamps[str(p.id)] for p in (root, child, grandchild)] == [None] * 3
    assert stamps[str(solo.id)] is not None
    assert sorted(await _journalled(session, "page_restored")) == sorted(
        str(p.id) for p in (root, child, grandchild)
    )
    with pytest.raises(PageTargetUnresolved):
        await restore_page(session, str(root.id))


@pytest.mark.asyncio
async def test_a_restore_refuses_while_the_parent_is_trashed(session, llm):
    """Restoring a child under a trashed parent would make a live page the
    purge cascade destroys; the parent is restored first, or not at all."""
    root, child, grandchild, _ = await _tree(session, llm)
    await delete_page(session, str(root.id))

    with pytest.raises(PageParentTrashed):
        await restore_page(session, str(child.id))
    stamps = await _stamps(session, [root.id, child.id, grandchild.id])
    assert None not in stamps.values()
    assert await _journalled(session, "page_restored") == []


@pytest.mark.asyncio
async def test_a_delete_journals_one_row_per_page_before_it_writes(session, llm, monkeypatch):
    """The strict journal contract `delete_documents` already holds: an erase
    with no audit trail is worse than a refused one."""
    from app.services import page_door

    root, child, grandchild, _ = await _tree(session, llm)
    real = page_door.record_event
    stamped_at_journal = []

    async def _journal(session_, **kwargs):
        stamp = (await _stamps(session_, [kwargs["object_id"]]))[str(kwargs["object_id"])]
        stamped_at_journal.append(stamp)
        return await real(session_, **kwargs)

    monkeypatch.setattr("app.services.page_door.record_event", _journal)
    await delete_page(session, str(root.id))

    assert stamped_at_journal == [None, None, None]
    assert await _journalled(session, "page_deleted") == sorted(
        str(p.id) for p in (root, child, grandchild)
    )


@pytest.mark.asyncio
async def test_a_delete_refuses_when_a_journal_row_does_not_land(session, llm, monkeypatch):
    root, child, grandchild, _ = await _tree(session, llm)
    calls = []

    async def _journal(session_, **kwargs):
        calls.append(kwargs["object_id"])
        return len(calls) < 3

    monkeypatch.setattr("app.services.page_door.record_event", _journal)
    with pytest.raises(PageJournalWriteFailed):
        await delete_page(session, str(root.id))

    assert len(calls) == 3
    stamps = await _stamps(session, [root.id, child.id, grandchild.id])
    assert set(stamps.values()) == {None}


@pytest.mark.asyncio
async def test_a_refused_delete_rolls_back_the_rows_already_journalled(
    session, llm, monkeypatch,
):
    """The first two rows land for real; the third refuses. Rows that landed
    must go with the savepoint, or the journal records a trash that never
    happened."""
    from app.services import events

    root, child, grandchild, _ = await _tree(session, llm)
    real = events.record_event
    calls = []

    async def _journal(session_, **kwargs):
        calls.append(kwargs["object_id"])
        if len(calls) < 3:
            return await real(session_, **kwargs)
        return False

    monkeypatch.setattr("app.services.page_door.record_event", _journal)
    with pytest.raises(PageJournalWriteFailed):
        await delete_page(session, str(root.id))

    assert len(calls) == 3
    assert await _journalled(session, "page_deleted") == []
    stamps = await _stamps(session, [root.id, child.id, grandchild.id])
    assert set(stamps.values()) == {None}


@pytest.mark.asyncio
async def test_purge_journals_every_page_before_it_deletes(session, llm, monkeypatch):
    root, child, grandchild, _ = await _tree(session, llm)
    await delete_page(session, str(root.id))
    calls = []

    async def _journal(session_, **kwargs):
        calls.append(kwargs["object_id"])
        return len(calls) < 3

    monkeypatch.setattr("app.services.page_door.record_event", _journal)
    with pytest.raises(PageJournalWriteFailed):
        await purge_trash(session, "p")

    assert len(calls) == 3
    stamps = await _stamps(session, [root.id, child.id, grandchild.id])
    assert len(stamps) == 3 and None not in stamps.values()


@pytest.mark.asyncio
async def test_purge_removes_rows_blocks_and_vectors(session, llm):
    from app.services.embedder_registry import child_table

    root = await create_page(session, llm, project="p", title="root",
                             content="# T\n\nbody\n")
    child = await create_page(session, llm, project="p", title="child",
                              parent_id=str(root.id), content="child body\n")
    block_ids = [
        str(r[0]) for r in (
            await session.execute(
                text(
                    "SELECT id FROM blocks "
                    "WHERE page_id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": [str(root.id), str(child.id)]},
            )
        ).all()
    ]
    assert len(block_ids) == 3
    await refresh_block_embeddings(session, llm, batch=0, page_batch=100)
    table = child_table("page_embeddings", FINGERPRINT)
    vectors = text(
        f"SELECT count(*) FROM {table} WHERE block_id = ANY(CAST(:ids AS uuid[]))"
    )
    assert (await session.execute(vectors, {"ids": block_ids})).scalar_one() == 3

    await delete_page(session, str(root.id))
    assert await purge_trash(session, "p") == 2

    assert await _stamps(session, [root.id, child.id]) == {}
    remaining = (
        await session.execute(
            text("SELECT count(*) FROM blocks WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": block_ids},
        )
    ).scalar_one()
    assert remaining == 0
    assert (await session.execute(vectors, {"ids": block_ids})).scalar_one() == 0
    assert await _journalled(session, "page_purged") == sorted(
        [str(root.id), str(child.id)]
    )


@pytest.mark.asyncio
async def test_purge_leaves_live_pages_alone(session, llm):
    """The positive control. A purge that deleted everything would pass the
    test above."""
    root, child, grandchild, sibling = await _tree(session, llm)
    elsewhere = await create_page(session, llm, project="other", title="x")
    await session.execute(
        text("UPDATE pages SET deleted_at = now() WHERE id = CAST(:id AS uuid)"),
        {"id": str(elsewhere.id)},
    )
    await delete_page(session, str(child.id))

    assert await purge_trash(session, "p") == 2
    stamps = await _stamps(
        session, [root.id, child.id, grandchild.id, sibling.id, elsewhere.id]
    )
    assert stamps.keys() == {str(root.id), str(sibling.id), str(elsewhere.id)}
    assert stamps[str(root.id)] is None and stamps[str(sibling.id)] is None
    assert stamps[str(elsewhere.id)] is not None


NESTED_HEADINGS = (
    "# A\n\npara\n\n## B\n\n- x\n- y\n\n1. o\n2. p\n\n"
    "### C\n\n```py\ncode\n```\n\n# D\n\n> q\n\n---\n"
)


def _heading_parented(tree):
    by_id = {block.id: block for block in tree}
    return [
        block for block in tree
        if block.parent_id is not None and by_id[block.parent_id].type == "heading"
    ]


@pytest.mark.asyncio
async def test_create_flattens_heading_nesting_losslessly(session, llm):
    """On a page only list, todo and toggle blocks hold children, so a
    heading-nested tree could not be extended by the editor. Flattening must
    not change a byte of the stored content."""
    unflattened = _parse(NESTED_HEADINGS)
    assert _heading_parented(unflattened), "fixture precondition: nested headings"

    page = await create_page(session, llm, project="p", title="n",
                             content=NESTED_HEADINGS)

    nested = (await session.execute(
        text(
            "SELECT count(*) FROM blocks b JOIN blocks parent ON parent.id = b.parent_id "
            "WHERE b.page_id = CAST(:id AS uuid) AND parent.type = 'heading'"
        ),
        {"id": str(page.id)},
    )).scalar_one()
    assert nested == 0
    row = await _page_row(session, page.id)
    assert row["content"] == serialize_tree(unflattened).content


def test_flattening_a_heading_inside_a_quote_keeps_the_quote_as_parent():
    tree = _parse("> # H\n\n- a\n- b\n")
    flat = _flatten_headings(tree)

    assert not _heading_parented(flat)
    quote = next(block for block in flat if block.type == "quote")
    assert {b.parent_id for b in flat if b.type == "list"} == {quote.id}
    assert serialize_tree(flat).content == serialize_tree(tree).content


@pytest.mark.asyncio
async def test_creating_a_page_embeds_nothing_inline(session, llm):
    await create_page(session, llm, project="p", title="n", content="# T\n\nbody\n")
    assert llm.batches == []


@pytest.mark.asyncio
async def test_the_keyed_read_serves_each_blocks_source(session, llm):
    """`text` is marker-stripped; an editor edits the block's own markdown."""
    page = await create_page(session, llm, project="p", title="n",
                             content="## Sub\n\n- item\n")

    view = await get_page(session, str(page.id))

    assert [block["source"] for block in view.blocks] == ["## Sub", "- item"]
    assert view.content is None


async def _stamp(session, page_id, at: datetime):
    # A datetime, not an ISO string: asyncpg refuses a str bound to
    # CAST(:at AS timestamptz) with "invalid input for query argument".
    await session.execute(
        text(
            "UPDATE pages SET deleted_at = CAST(:at AS timestamptz) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(page_id), "at": at},
    )


@pytest.mark.asyncio
async def test_the_trash_lists_only_the_roots_of_trashed_subtrees(session, llm):
    root = await create_page(session, llm, project="p", title="root")
    child = await create_page(session, llm, project="p", title="child",
                              parent_id=str(root.id))
    lone = await create_page(session, llm, project="p", title="lone")
    live = await create_page(session, llm, project="p", title="live")
    kid = await create_page(session, llm, project="p", title="kid",
                            parent_id=str(live.id))
    elsewhere = await create_page(session, llm, project="q", title="other")
    for page in (root, lone, kid, elsewhere):
        await delete_page(session, str(page.id))
    # One transaction means one `now()`; distinct stamps make the order real.
    await _stamp(session, root.id, datetime(2026, 9, 1, tzinfo=timezone.utc))
    await _stamp(session, child.id, datetime(2026, 9, 1, tzinfo=timezone.utc))
    await _stamp(session, lone.id, datetime(2026, 9, 2, tzinfo=timezone.utc))
    await _stamp(session, kid.id, datetime(2026, 9, 3, tzinfo=timezone.utc))

    rows = await list_trash(session, "p")

    assert [str(row["id"]) for row in rows] == [str(kid.id), str(lone.id), str(root.id)]
    assert set(rows[0]) == {"id", "title", "parent_id", "deleted_at"}
    assert str(rows[0]["parent_id"]) == str(live.id)
    assert rows[2]["title"] == "root"
