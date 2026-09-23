"""The work-log service: the one implementation behind both doors."""
from __future__ import annotations

import asyncio
import secrets
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.models.worklog import WorklogEntry, Workstream
from app.services import worklog


async def _events(session, workstream_id):
    rows = await session.execute(
        text(
            "SELECT event_type, payload FROM events "
            "WHERE object_type = 'workstream' AND object_id = CAST(:w AS uuid) "
            "ORDER BY id"
        ),
        {"w": str(workstream_id)},
    )
    return [(r.event_type, r.payload) for r in rows]


async def _append(session, key="plan-a", entries=None, **kwargs):
    return await worklog.append(
        session,
        project="proj",
        key=key,
        run_key="claude:run-1",
        entries=entries if entries is not None else [{"kind": "ledger", "body": "Task 1: complete\n"}],
        **kwargs,
    )


async def test_append_creates_the_workstream_and_journals_it(session):
    result = await _append(
        session,
        entries=[
            {"kind": "checkpoint", "body": "## State\nplan saved"},
            {"kind": "ledger", "body": "Task 1: complete\n", "properties": {"task": 1}},
        ],
        title="Plan A",
        client="dr-superpowers",
        properties={"plan_uri": "superpowers/plans/a.md"},
    )
    ws = result.workstream
    assert (ws.project, ws.key, ws.title, ws.client, ws.state) == (
        "proj", "plan-a", "Plan A", "dr-superpowers", "open",
    )
    assert ws.properties == {"plan_uri": "superpowers/plans/a.md"}
    rows = (await session.execute(
        select(WorklogEntry).where(WorklogEntry.workstream_id == ws.id).order_by(WorklogEntry.seq)
    )).scalars().all()
    assert [r.id for r in rows] == result.entry_ids
    assert [r.kind for r in rows] == ["checkpoint", "ledger"]
    assert rows[1].properties == {"task": 1}
    assert all(r.run_key == "claude:run-1" for r in rows)
    assert await _events(session, ws.id) == [("workstream_opened", {"key": "plan-a"})]


async def test_a_full_batch_of_one_hundred_lands_in_order(session):
    result = await _append(session, entries=[{"kind": "ledger", "body": f"{i}\n"} for i in range(100)])
    bodies = (await session.execute(
        select(WorklogEntry.body).where(WorklogEntry.workstream_id == result.workstream.id)
        .order_by(WorklogEntry.seq)
    )).scalars().all()
    assert bodies == [f"{i}\n" for i in range(100)]


async def test_a_refused_batch_leaves_no_workstream_and_no_entry(session):
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, entries=[
            {"kind": "ledger", "body": "fine\n"},
            {"kind": "ledger", "body": "x" * 65_537},
        ])
    assert (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one() == 0
    assert (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one() == 0


async def test_merged_properties_over_the_database_bound_are_rejected(session):
    first = await _append(session, properties={"a": secrets.token_hex(4500)})
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream(session, project="proj", key="plan-a")
    assert set(kept.properties) == {"a"}
    assert kept.id == first.workstream.id


async def test_an_update_over_the_database_bound_is_rejected_and_the_session_survives(session):
    ws = (await _append(session, properties={"a": secrets.token_hex(4500)})).workstream
    # The rolled-back savepoint expires the instance, and an async session
    # cannot lazy-load `ws.id` back.
    workstream_id = ws.id
    with pytest.raises(worklog.WorklogRejected):
        await worklog.update_workstream(session, workstream_id, properties={"b": secrets.token_hex(4500)})
    kept = await worklog.get_workstream_by_id(session, workstream_id, for_update=True)
    assert set(kept.properties) == {"a"}


async def test_a_second_append_reuses_and_merges(session):
    first = await _append(session, properties={"plan_uri": "a"})
    second = await _append(session, properties={"spec_uri": "b"}, title="Titled later")
    assert second.workstream.id == first.workstream.id
    assert second.workstream.properties == {"plan_uri": "a", "spec_uri": "b"}
    assert second.workstream.title == "Titled later"
    count = (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one()
    assert count == 1
    assert [e for e, _ in await _events(session, first.workstream.id)] == ["workstream_opened"]


async def test_append_registers_the_project(session):
    await _append(session)
    found = (await session.execute(
        text("SELECT count(*) FROM projects WHERE name = 'proj'")
    )).scalar_one()
    assert found == 1


async def test_append_to_a_closed_workstream_reopens_it(session):
    first = await _append(session)
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    again = await _append(session)
    assert again.workstream.state == "open"
    assert again.workstream.closed_at is None
    assert [e for e, _ in await _events(session, first.workstream.id)] == [
        "workstream_opened", "workstream_closed", "workstream_reopened",
    ]


@pytest.mark.parametrize("count", [0, 101])
async def test_append_refuses_a_batch_outside_1_to_100(session, count):
    with pytest.raises(ValueError):
        await _append(session, entries=[{"kind": "note", "body": "n"}] * count)


async def test_close_sets_closed_at_and_reopen_clears_it(session):
    ws = (await _append(session)).workstream
    closed = await worklog.update_workstream(session, ws.id, state="closed")
    assert closed.state == "closed" and closed.closed_at is not None
    reopened = await worklog.update_workstream(session, ws.id, state="open")
    assert reopened.state == "open" and reopened.closed_at is None


async def test_update_moves_retain_title_and_merges_properties(session):
    ws = (await _append(session, properties={"a": 1})).workstream
    updated = await worklog.update_workstream(
        session, ws.id, retain=True, title="T", properties={"b": 2}
    )
    assert updated.retain is True
    assert updated.title == "T"
    assert updated.properties == {"a": 1, "b": 2}
    assert [e for e, _ in await _events(session, ws.id)] == ["workstream_opened"]


async def test_the_lock_refreshes_a_stale_loaded_row(session):
    ws = (await _append(session)).workstream
    await session.execute(
        text("UPDATE workstreams SET state = 'closed', closed_at = now() WHERE id = CAST(:w AS uuid)"),
        {"w": str(ws.id)},
    )
    assert ws.state == "open"
    reopened = await worklog.update_workstream(session, ws.id, state="open")
    assert reopened.state == "open" and reopened.closed_at is None
    assert [e for e, _ in await _events(session, ws.id)][-1] == "workstream_reopened"


async def test_update_and_purge_refuse_an_unknown_workstream(session):
    with pytest.raises(worklog.WorkstreamNotFound):
        await worklog.update_workstream(session, uuid.uuid4(), state="closed")
    with pytest.raises(worklog.WorkstreamNotFound):
        await worklog.purge_workstream(session, uuid.uuid4())


async def test_purge_journals_then_deletes_everything(session):
    ws = (await _append(session, entries=[
        {"kind": "ledger", "body": "a\n"}, {"kind": "note", "body": "b"},
    ])).workstream
    workstream_id = ws.id
    removed = await worklog.purge_workstream(session, workstream_id, actor="admin")
    assert removed == 2
    assert (await session.execute(text("SELECT count(*) FROM workstreams"))).scalar_one() == 0
    assert (await session.execute(text("SELECT count(*) FROM worklog_entries"))).scalar_one() == 0
    assert (await _events(session, workstream_id))[-1] == (
        "workstream_purged", {"key": "plan-a", "entries": 2},
    )


@pytest.mark.parametrize("reported", [False, True])
async def test_purge_refuses_unless_the_journal_row_is_really_there(session, monkeypatch, reported):
    ws = (await _append(session)).workstream

    async def writes_nothing(*args, **kwargs):
        return reported

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await worklog.purge_workstream(session, ws.id)
    still = (await session.execute(select(Workstream).where(Workstream.id == ws.id))).scalar_one_or_none()
    assert still is not None
    entries = (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(ws.id)},
    )).scalar_one()
    assert entries == 1


async def test_no_entry_text_reaches_the_journal(session):
    secret = "body text that must never be journaled"
    ws = (await _append(session, entries=[{"kind": "note", "body": secret, "properties": {"x": secret}}])).workstream
    await worklog.update_workstream(session, ws.id, state="closed")
    for _, payload in await _events(session, ws.id):
        assert secret not in str(payload)


def test_serializers_are_json_safe():
    import json
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    ws = Workstream(
        id=uuid.uuid4(), project="p", key="k", title=None, client=None, state="open",
        closed_at=None, retain=False, properties={}, last_entry_at=now,
        created_at=now, updated_at=now,
    )
    entry = WorklogEntry(
        id=uuid.uuid4(), seq=7, workstream_id=ws.id, run_key="r", kind="note",
        body="b", properties={}, created_at=now,
    )
    json.dumps(worklog.serialize_workstream(ws))
    json.dumps(worklog.serialize_entry(entry))
    assert worklog.serialize_entry(entry)["seq"] == 7


# ── Races, on independent committed connections ──────────────────────────
#
# The `session` fixture shares one connection, so it cannot show two
# transactions waiting on each other. These use the test engine directly,
# commit for real, and delete their own rows afterwards. The events rows they
# journal cannot be deleted (the journal is append-only) and are left under
# the `worklog-race` project.

RACE_PROJECT = "worklog-race"
_RETENTION_DELETE = text(
    "DELETE FROM workstreams WHERE id = CAST(:id AS uuid) "
    "AND state = 'closed' AND NOT retain RETURNING id"
)


@pytest_asyncio.fixture
async def committed(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    yield factory
    async with factory() as cleanup:
        await cleanup.execute(text("DELETE FROM workstreams WHERE project = :p"), {"p": RACE_PROJECT})
        await cleanup.execute(text("DELETE FROM projects WHERE name = :p"), {"p": RACE_PROJECT})
        await cleanup.commit()


async def _closed_race_workstream(factory) -> uuid.UUID:
    async with factory() as setup:
        result = await worklog.append(
            setup, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "n"}],
        )
        await worklog.update_workstream(setup, result.workstream.id, state="closed")
        await setup.commit()
        return result.workstream.id


async def test_an_append_holding_the_lock_survives_a_retention_delete(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as appender, committed() as deleter:
        await worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        )
        delete_task = asyncio.create_task(deleter.execute(_RETENTION_DELETE, {"id": str(ws_id)}))
        await asyncio.sleep(0.3)
        assert not delete_task.done(), "the delete must wait on the append's row lock"
        await appender.commit()
        deleted = (await delete_task).fetchall()
        await deleter.commit()
    assert deleted == []
    async with committed() as check:
        state = (await check.execute(
            text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"), {"id": str(ws_id)}
        )).scalar_one()
    assert state == "open"


async def test_an_append_behind_a_committed_delete_recreates_the_workstream(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as deleter, committed() as appender:
        removed = (await deleter.execute(_RETENTION_DELETE, {"id": str(ws_id)})).fetchall()
        assert len(removed) == 1
        append_task = asyncio.create_task(worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        ))
        await asyncio.sleep(0.3)
        assert not append_task.done(), "the append must wait on the delete's row lock"
        await deleter.commit()
        result = await append_task
        await appender.commit()
    assert result.workstream.id != ws_id
    async with committed() as check:
        counts = [
            (await check.execute(
                text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:id AS uuid)"),
                {"id": str(workstream_id)},
            )).scalar_one()
            for workstream_id in (ws_id, result.workstream.id)
        ]
    assert counts == [0, 1]
