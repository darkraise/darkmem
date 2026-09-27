"""The work-log tables. Their CHECKs are the guarantee behind both doors."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.models.worklog import WorklogEntry, Workstream


async def _workstream(session, *, key="plan-a"):
    wid = uuid.uuid4()
    await session.execute(
        text(
            "INSERT INTO workstreams (id, project, key) "
            "VALUES (CAST(:id AS uuid), 'proj', CAST(:key AS text))"
        ),
        {"id": str(wid), "key": key},
    )
    return wid


async def _entry(session, wid, *, kind="ledger", body="line\n"):
    await session.execute(
        text(
            "INSERT INTO worklog_entries (id, workstream_id, run_key, kind, body) "
            "VALUES (CAST(:id AS uuid), CAST(:w AS uuid), 'run:1', "
            "CAST(:k AS text), CAST(:b AS text))"
        ),
        {"id": str(uuid.uuid4()), "w": str(wid), "k": kind, "b": body},
    )


async def test_an_entry_is_keyword_searchable(session):
    wid = await _workstream(session)
    await _entry(session, wid, body="the gate went red on the alembic check")
    hit = (await session.execute(text(
        "SELECT count(*) FROM worklog_entries "
        "WHERE search_vector @@ plainto_tsquery('english', 'alembic')"
    ))).scalar_one()
    assert hit == 1


async def test_seq_keeps_one_statement_s_rows_in_order(session):
    wid = await _workstream(session)
    await session.execute(
        text(
            "INSERT INTO worklog_entries (id, workstream_id, run_key, kind, body) VALUES "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'a'), "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'b'), "
            "(gen_random_uuid(), CAST(:w AS uuid), 'r', 'ledger', 'c')"
        ),
        {"w": str(wid)},
    )
    bodies = (await session.execute(text(
        "SELECT body FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid) ORDER BY seq"
    ), {"w": str(wid)})).scalars().all()
    assert bodies == ["a", "b", "c"]


@pytest.mark.parametrize("kind,body", [
    ("log", "x"),
    ("ledger", ""),
    ("ledger", "x" * 65_537),
])
async def test_the_entry_checks_refuse(session, kind, body):
    wid = await _workstream(session)
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _entry(session, wid, kind=kind, body=body)


async def test_the_body_bound_is_inclusive(session):
    wid = await _workstream(session)
    await _entry(session, wid, body="x" * 65_536)


@pytest.mark.parametrize("state,closed", [("closed", False), ("open", True), ("done", False)])
async def test_the_state_checks_refuse(session, state, closed):
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await session.execute(
                text(
                    "INSERT INTO workstreams (id, project, key, state, closed_at) VALUES "
                    "(gen_random_uuid(), 'proj', 'k', CAST(:s AS text), "
                    "CASE WHEN CAST(:c AS boolean) THEN now() ELSE NULL END)"
                ),
                {"s": state, "c": closed},
            )


async def _insert_workstream(session, *, key="k", title=None, properties="{}"):
    await session.execute(
        text(
            "INSERT INTO workstreams (id, project, key, title, properties) VALUES "
            "(gen_random_uuid(), 'proj', CAST(:k AS text), CAST(:t AS text), CAST(:p AS jsonb))"
        ),
        {"k": key, "t": title, "p": properties},
    )


async def _insert_entry(session, wid, *, properties):
    await session.execute(
        text(
            "INSERT INTO worklog_entries (id, workstream_id, run_key, kind, body, properties) "
            "VALUES (gen_random_uuid(), CAST(:w AS uuid), 'run:1', 'note', 'n', CAST(:p AS jsonb))"
        ),
        {"w": str(wid), "p": properties},
    )


def _properties(chars):
    return '{"p": "' + "x" * chars + '"}'


@pytest.mark.parametrize("fields,accepted", [
    ({"key": "k" * 200}, True),
    ({"key": "k" * 201}, False),
    ({"key": ""}, False),
    ({"title": "t" * 500}, True),
    ({"title": "t" * 501}, False),
    ({"properties": _properties(16_000)}, True),
    ({"properties": _properties(17_000)}, False),
])
async def test_the_workstream_bounds(session, fields, accepted):
    if accepted:
        await _insert_workstream(session, **fields)
        return
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _insert_workstream(session, **fields)


@pytest.mark.parametrize("chars,accepted", [(16_000, True), (17_000, False)])
async def test_the_entry_properties_bound(session, chars, accepted):
    wid = await _workstream(session)
    if accepted:
        await _insert_entry(session, wid, properties=_properties(chars))
        return
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _insert_entry(session, wid, properties=_properties(chars))


async def test_one_key_per_project(session):
    await _workstream(session, key="dup")
    with pytest.raises(DBAPIError):
        async with session.begin_nested():
            await _workstream(session, key="dup")


async def test_deleting_a_workstream_cascades_its_entries(session):
    wid = await _workstream(session)
    await _entry(session, wid)
    await session.execute(text("DELETE FROM workstreams WHERE id = CAST(:w AS uuid)"), {"w": str(wid)})
    left = (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one()
    assert left == 0


async def test_the_models_map_the_tables(session):
    ws = Workstream(project="proj", key="orm")
    session.add(ws)
    await session.flush()
    entry = WorklogEntry(workstream_id=ws.id, run_key="r", kind="note", body="remember this")
    session.add(entry)
    await session.flush()
    await session.refresh(entry)
    assert entry.seq is not None
    assert entry.search_vector is not None
    await session.refresh(ws)
    assert ws.state == "open" and ws.retain is False and ws.last_entry_at is not None
    found = (await session.execute(select(WorklogEntry).where(WorklogEntry.workstream_id == ws.id))).scalar_one()
    assert found.body == "remember this"


def test_the_vocabulary_carries_the_workstream_lifecycle():
    from app.services.events import EVENT_TYPES, OBJECT_TYPES

    for event_type in (
        "workstream_opened",
        "workstream_closed",
        "workstream_reopened",
        "workstream_purged",
    ):
        assert event_type in EVENT_TYPES
    assert "workstream" in OBJECT_TYPES


def _members(source: str) -> set[str]:
    """The string members of EVENT_TYPES_WITHOUT_TAB in `source`, comments stripped."""
    import re

    block = source.split("const EVENT_TYPES_WITHOUT_TAB = new Set<string>([", 1)[1].split("])", 1)[0]
    code = "\n".join(line.split("//", 1)[0] for line in block.splitlines())
    return set(re.findall(r'"([a-z_]+)"', code))


def _without_tab_members() -> set[str]:
    from pathlib import Path

    return _members((
        Path(__file__).resolve().parents[2]
        / "frontend" / "src" / "features" / "activity" / "event-taxonomy.ts"
    ).read_text(encoding="utf-8"))


def test_the_frontend_map_classifies_the_workstream_lifecycle():
    members = _without_tab_members()
    for event_type in (
        "workstream_opened",
        "workstream_closed",
        "workstream_reopened",
        "workstream_purged",
    ):
        assert event_type in members


def test_the_member_scan_ignores_names_that_only_appear_in_comments():
    block = (
        "const EVENT_TYPES_WITHOUT_TAB = new Set<string>([\n"
        '  "kept",\n'
        '  // "commented_out" is only mentioned\n'
        "])"
    )
    assert _members(block) == {"kept"}
