from __future__ import annotations

import inspect
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.services.page_door import _insert_page, create_page


@pytest.fixture
def llm():
    """`create_page` accepts an `llm` and never uses it (page_door.py:449 is
    its only occurrence). There is no conftest fixture for it -- the page tests
    each define their own -- so this file defines the same stand-in."""
    return None


def test_create_page_keeps_its_signature():
    params = list(inspect.signature(create_page).parameters)
    assert params[:2] == ["session", "llm"]
    for name in ("project", "title", "parent_id", "after_id", "content",
                 "properties", "actor"):
        assert name in params


@pytest.mark.asyncio
async def test_insert_page_does_not_commit(session, monkeypatch):
    calls: list[int] = []
    original = session.commit

    async def spy() -> None:
        calls.append(1)
        await original()

    monkeypatch.setattr(session, "commit", spy)
    await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="A", tree=[], properties=None, actor=None,
    )
    assert calls == []


@pytest.mark.asyncio
async def test_insert_page_honours_a_caller_supplied_id(session):
    page_id = uuid4()
    result = await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="Pinned", tree=[], properties=None, actor=None, page_id=page_id,
    )
    assert result.id == page_id
    found = (
        await session.execute(
            text("SELECT title FROM pages WHERE id = CAST(:id AS uuid)"),
            {"id": str(page_id)},
        )
    ).scalar_one()
    assert found == "Pinned"


@pytest.mark.asyncio
async def test_insert_page_mints_an_id_when_none_is_given(session):
    result = await _insert_page(
        session, project="notes", parent_id=None, after_id=None,
        title="Minted", tree=[], properties=None, actor=None,
    )
    assert result.id is not None


@pytest.mark.asyncio
async def test_insert_page_refuses_too_many_blocks(session, llm):
    from app.services.page_door import MAX_BLOCKS, PageTooLarge, _parse

    content = "\n\n".join(f"p{i}" for i in range(MAX_BLOCKS + 5))
    with pytest.raises(PageTooLarge):
        await _insert_page(
            session, project="notes", parent_id=None, after_id=None,
            title="Huge", tree=_parse(content), properties=None, actor=None,
        )


@pytest.mark.asyncio
async def test_blocks_are_written_in_one_statement(session, llm, monkeypatch):
    from app.services import page_door

    content = "\n\n".join(f"para {i}" for i in range(40))
    executed: list[str] = []
    original = session.execute

    async def spy(statement, *args, **kwargs):
        executed.append(str(statement))
        return await original(statement, *args, **kwargs)

    monkeypatch.setattr(session, "execute", spy)
    await create_page(session, llm, project="notes", title="Many", content=content)

    inserts = [s for s in executed if "INSERT INTO blocks" in s]
    assert len(inserts) == 1, f"{len(inserts)} block inserts; one unnest was expected"


@pytest.mark.asyncio
async def test_create_page_still_journals_the_same_payload(session, llm):
    result = await create_page(
        session, llm, project="notes", title="Journalled", content="Body."
    )
    payload = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE object_id = CAST(:id AS uuid) "
                "AND event_type = 'page_created'"
            ),
            {"id": str(result.id)},
        )
    ).scalar_one()
    assert set(payload) == {"parent_id", "order_index", "blocks_total", "content_hash"}
    assert payload["blocks_total"] == result.blocks_written
