"""The page door's create, get and list halves (spec 2026-09-08, §7)."""
from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.document_ingest import compute_content_hash
from app.services.page_door import (
    PageCycleError,
    PageTargetUnresolved,
    create_page,
    get_page,
    list_pages,
    move_page,
    rename_page,
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


@pytest.mark.asyncio
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
async def test_a_trashed_sibling_keeps_its_slot_in_the_renumber(session, llm):
    """A restore puts a trashed page back at its own index, so dropping it from
    the renumber would let a live sibling take that index first."""
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
