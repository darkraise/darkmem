"""The work-log service: the one implementation behind both doors."""
from __future__ import annotations

import asyncio
import secrets
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import event, func, select, text

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


async def test_a_refused_batch_leaves_a_closed_workstream_closed(session):
    first = await _append(session)
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    with pytest.raises(worklog.WorklogRejected):
        await _append(session, entries=[{"kind": "ledger", "body": "x" * 65_537}])
    kept = await worklog.get_workstream_by_id(session, first.workstream.id, for_update=True)
    assert kept.state == "closed" and kept.closed_at is not None
    assert [e for e, _ in await _events(session, first.workstream.id)] == [
        "workstream_opened", "workstream_closed",
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


async def _close(session, workstream_id, *, days_ago, retain=False):
    await worklog.update_workstream(session, workstream_id, state="closed", retain=retain)
    await session.execute(
        text(
            "UPDATE workstreams SET closed_at = now() - make_interval(days => CAST(:d AS integer)) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"d": days_ago, "id": str(workstream_id)},
    )


async def test_expire_next_erases_the_longest_closed_first_and_journals_it(session):
    older_id = (await _append(session, key="older", entries=[
        {"kind": "note", "body": "a"}, {"kind": "note", "body": "b"},
    ])).workstream.id
    newer_id = (await _append(session, key="newer")).workstream.id
    # Both rows share one transaction's now(), and uuid4 order is random. Give
    # "newer" the smaller id and the earlier created_at, so an ordering by id or
    # created_at alone erases it first; only closed_at order reaches "older".
    while newer_id > older_id:
        await session.execute(text("DELETE FROM workstreams WHERE id = CAST(:id AS uuid)"), {"id": str(newer_id)})
        newer_id = (await _append(session, key="newer")).workstream.id
    for ws_id, days in ((newer_id, 30), (older_id, 20)):
        await session.execute(
            text(
                "UPDATE workstreams SET created_at = now() - make_interval(days => CAST(:d AS integer)) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"d": days, "id": str(ws_id)},
        )
    await _close(session, newer_id, days_ago=5)
    await _close(session, older_id, days_ago=10)

    assert await worklog.expire_next(session, retention_days=1, actor="worklog_cleanup") == 2
    assert (await session.execute(text("SELECT key FROM workstreams"))).scalars().all() == ["newer"]
    assert (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(older_id)},
    )).scalar_one() == 0
    row = (await session.execute(
        text(
            "SELECT actor, payload FROM events WHERE event_type = 'workstream_purged' "
            "AND object_type = 'workstream' AND object_id = CAST(:w AS uuid)"
        ),
        {"w": str(older_id)},
    )).one()
    assert row.actor == "worklog_cleanup"
    assert row.payload == {"key": "older", "entries": 2, "retention_days": 1}

    assert await worklog.expire_next(session, retention_days=1) == 1
    assert await worklog.expire_next(session, retention_days=1) is None


async def test_expire_next_keeps_open_retained_and_recent_workstreams(session):
    open_id = (await _append(session, key="open")).workstream.id
    retained_id = (await _append(session, key="retained")).workstream.id
    recent_id = (await _append(session, key="recent")).workstream.id
    await session.execute(
        text(
            "UPDATE workstreams SET created_at = now() - interval '400 days', "
            "last_entry_at = now() - interval '400 days' WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(open_id)},
    )
    await _close(session, retained_id, days_ago=400, retain=True)
    await _close(session, recent_id, days_ago=1)

    assert await worklog.expire_next(session, retention_days=2) is None
    assert sorted((await session.execute(text("SELECT key FROM workstreams"))).scalars().all()) == [
        "open", "recent", "retained",
    ]


@pytest.mark.parametrize("reported", [False, True])
async def test_expire_next_refuses_unless_the_journal_row_is_really_there(session, monkeypatch, reported):
    ws_id = (await _append(session)).workstream.id
    await _close(session, ws_id, days_ago=10)

    async def writes_nothing(*args, **kwargs):
        return reported

    monkeypatch.setattr(worklog, "record_event", writes_nothing)
    with pytest.raises(worklog.WorklogJournalWriteFailed):
        await worklog.expire_next(session, retention_days=1)
    still = (await session.execute(select(Workstream).where(Workstream.id == ws_id))).scalar_one_or_none()
    assert still is not None
    entries = (await session.execute(
        text("SELECT count(*) FROM worklog_entries WHERE workstream_id = CAST(:w AS uuid)"),
        {"w": str(ws_id)},
    )).scalar_one()
    assert entries == 1


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
    served_ws = json.loads(json.dumps(worklog.serialize_workstream(ws)))
    served_entry = json.loads(json.dumps(worklog.serialize_entry(entry)))
    assert set(served_ws) == {
        "id", "project", "key", "title", "client", "state", "closed_at", "retain",
        "properties", "last_entry_at", "created_at", "updated_at",
    }
    assert set(served_entry) == {
        "id", "workstream_id", "seq", "run_key", "kind", "body", "properties", "created_at",
    }
    assert served_entry["seq"] == 7
    for stamp in (served_ws["last_entry_at"], served_ws["created_at"], served_entry["created_at"]):
        assert datetime.fromisoformat(stamp) == now


# ── Races, on independent committed connections ──────────────────────────
#
# The `session` fixture shares one connection, so it cannot show two
# transactions waiting on each other. These use the test engine directly,
# commit for real, and delete their own rows afterwards. The events rows they
# journal cannot be deleted (the journal is append-only) and are left under
# the `worklog-race` project.

RACE_PROJECT = "worklog-race"


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
        await setup.execute(
            text("UPDATE workstreams SET closed_at = now() - interval '2 days' WHERE id = CAST(:id AS uuid)"),
            {"id": str(result.workstream.id)},
        )
        await setup.commit()
        return result.workstream.id


async def test_the_sweep_passes_over_a_workstream_an_append_holds(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as appender, committed() as sweeper:
        await worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        )
        swept = await asyncio.wait_for(worklog.expire_next(sweeper, retention_days=1), timeout=5)
        assert swept is None, "the sweep must skip a row an append holds, neither waiting nor deleting"
        await sweeper.rollback()
        await appender.commit()
    async with committed() as check:
        state = (await check.execute(
            text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"), {"id": str(ws_id)}
        )).scalar_one()
    assert state == "open"


async def test_an_append_behind_a_committed_sweep_recreates_the_workstream(committed):
    ws_id = await _closed_race_workstream(committed)
    async with committed() as sweeper, committed() as appender:
        assert await worklog.expire_next(sweeper, retention_days=1) == 1
        append_task = asyncio.create_task(worklog.append(
            appender, project=RACE_PROJECT, key="race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        ))
        await asyncio.sleep(0.3)
        assert not append_task.done(), "the append must wait on the sweep's row lock"
        await sweeper.commit()
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


async def test_resume_is_none_for_an_unknown_workstream(session):
    assert await worklog.resume(session, project="proj", key="nope") is None


async def test_resume_answers_latest_checkpoint_notes_and_ledger_tail(session):
    await _append(session, entries=[{"kind": "checkpoint", "body": "old"}])
    await _append(session, entries=[{"kind": "ledger", "body": f"line {i}\n"} for i in range(25)])
    await _append(session, entries=[
        {"kind": "note", "body": "gotcha"},
        {"kind": "checkpoint", "body": "new"},
    ])
    answer = await worklog.resume(session, project="proj", key="plan-a")
    assert answer["workstream"]["key"] == "plan-a"
    assert answer["checkpoint"]["body"] == "new"
    assert [n["body"] for n in answer["notes"]] == ["gotcha"]
    assert answer["notes_truncated"] is False
    assert [e["body"] for e in answer["ledger"]] == [f"line {i}\n" for i in range(5, 25)]


async def test_resume_caps_notes_at_fifty_newest(session):
    await _append(session, entries=[{"kind": "note", "body": f"n{i}"} for i in range(51)])
    answer = await worklog.resume(session, project="proj", key="plan-a")
    assert len(answer["notes"]) == 50
    assert answer["notes"][0]["body"] == "n1"
    assert answer["notes"][-1]["body"] == "n50"
    assert answer["notes_truncated"] is True


async def test_resume_is_one_statement(session):
    # Under READ COMMITTED each statement takes its own snapshot, so a resume
    # spread over several could pair one commit's properties with another's
    # checkpoint. One statement is what makes the answer a single snapshot.
    from tests.conftest import test_engine

    appended = await _append(session, entries=[
        {"kind": "checkpoint", "body": "state", "properties": {"task": 3}},
        {"kind": "note", "body": "gotcha"},
        {"kind": "ledger", "body": "Task 1: complete\n"},
    ], properties={"plan_uri": "plans/a.md"})
    statements: list[str] = []

    def count(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    target = test_engine.sync_engine
    event.listen(target, "before_cursor_execute", count)
    try:
        answer = await worklog.resume(session, project="proj", key="plan-a")
    finally:
        event.remove(target, "before_cursor_execute", count)

    assert len(statements) == 1, "\n".join(statements)
    assert answer["workstream"] == worklog.serialize_workstream(appended.workstream)
    assert answer["checkpoint"]["body"] == "state"
    assert answer["checkpoint"]["properties"] == {"task": 3}
    assert answer["checkpoint"]["id"] == str(appended.entry_ids[0])
    assert [n["body"] for n in answer["notes"]] == ["gotcha"]
    assert [e["body"] for e in answer["ledger"]] == ["Task 1: complete\n"]


async def test_ledger_chunks_concatenate_back_to_the_appended_text(session):
    chunks = ["# Ledger\n\n", "Task 1: complete\n", "| a | b |\n|---|---|\n\n", "Task 2: complete\n"]
    for chunk in chunks:
        await _append(session, entries=[{"kind": "ledger", "body": chunk}])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    page = await worklog.list_entries(session, workstream_id=ws.id, kind="ledger")
    assert "".join(e["body"] for e in page["items"]) == "".join(chunks)


async def test_list_workstreams_pages_by_creation_and_ignores_later_appends(session):
    for key in ("w1", "w2", "w3"):
        await _append(session, key=key)
    # w1 was created most recently, w3 longest ago; activity starts in the same order.
    await session.execute(text(
        "UPDATE workstreams SET "
        "created_at = now() - CAST(substr(key, 2) AS int) * interval '1 hour', "
        "last_entry_at = now() - CAST(substr(key, 2) AS int) * interval '1 hour'"
    ))
    session.expire_all()
    first = await worklog.list_workstreams(session, project="proj", limit=2)
    assert [w["key"] for w in first["items"]] == ["w1", "w2"]
    # w3 becomes the most active; a list keyed on activity would now repeat or skip.
    await session.execute(text(
        "UPDATE workstreams SET last_entry_at = now() + interval '1 hour' WHERE key = 'w3'"
    ))
    session.expire_all()
    rest = await worklog.list_workstreams(session, project="proj", before=first["next_before"], limit=2)
    assert [w["key"] for w in rest["items"]] == ["w3"]
    assert rest["next_before"] is None


async def test_list_workstreams_breaks_a_created_at_tie_on_id(session):
    for key in ("t1", "t2", "t3"):
        await _append(session, key=key)
    await session.execute(text("UPDATE workstreams SET created_at = '2026-09-01T00:00:00+00:00'"))
    session.expire_all()
    ids = (await session.execute(
        select(Workstream.id).order_by(Workstream.id.desc())
    )).scalars().all()
    first = await worklog.list_workstreams(session, project="proj", limit=2)
    rest = await worklog.list_workstreams(session, project="proj", before=first["next_before"], limit=2)
    assert [w["id"] for w in first["items"] + rest["items"]] == [str(i) for i in ids]


async def test_list_workstreams_filters_by_state_and_project(session):
    await _append(session, key="open-one")
    closing = (await _append(session, key="closed-one")).workstream
    await worklog.update_workstream(session, closing.id, state="closed")
    closed = await worklog.list_workstreams(session, project="proj", state="closed")
    assert [w["key"] for w in closed["items"]] == ["closed-one"]
    other = await worklog.list_workstreams(session, project="elsewhere")
    assert other == {"items": [], "next_before": None}


async def test_list_workstreams_refuses_a_malformed_cursor(session):
    with pytest.raises(ValueError):
        await worklog.list_workstreams(session, project="proj", before="not-a-cursor")


async def test_list_entries_pages_forward_by_seq(session):
    await _append(session, entries=[{"kind": "ledger", "body": f"{i}\n"} for i in range(5)])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    first = await worklog.list_entries(session, workstream_id=ws.id, limit=2)
    assert [e["body"] for e in first["items"]] == ["0\n", "1\n"]
    assert first["next_after"] == first["items"][-1]["seq"]
    second = await worklog.list_entries(session, workstream_id=ws.id, after=first["next_after"], limit=2)
    assert [e["body"] for e in second["items"]] == ["2\n", "3\n"]
    last = await worklog.list_entries(session, workstream_id=ws.id, after=second["next_after"], limit=2)
    assert [e["body"] for e in last["items"]] == ["4\n"]
    assert last["next_after"] is None


async def test_list_entries_filters_by_kind(session):
    await _append(session, entries=[
        {"kind": "ledger", "body": "l\n"},
        {"kind": "note", "body": "n"},
        {"kind": "checkpoint", "body": "c"},
    ])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    notes = await worklog.list_entries(session, workstream_id=ws.id, kind="note")
    assert [(e["kind"], e["body"]) for e in notes["items"]] == [("note", "n")]


async def test_list_entries_filters_by_since(session):
    from datetime import UTC, datetime, timedelta

    await _append(session, entries=[{"kind": "note", "body": "n"}])
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    past = await worklog.list_entries(session, workstream_id=ws.id, since=datetime.now(UTC) - timedelta(days=1))
    future = await worklog.list_entries(session, workstream_id=ws.id, since=datetime.now(UTC) + timedelta(days=1))
    assert [e["body"] for e in past["items"]] == ["n"]
    assert future["items"] == []


async def test_list_workstreams_refuses_an_unknown_state(session):
    with pytest.raises(ValueError):
        await worklog.list_workstreams(session, project="proj", state="archived")


async def test_list_entries_refuses_an_unknown_kind(session):
    await _append(session)
    ws = await worklog.get_workstream(session, project="proj", key="plan-a")
    with pytest.raises(ValueError):
        await worklog.list_entries(session, workstream_id=ws.id, kind="memo")


async def _ledger(session, workstream_id):
    return (await session.execute(
        select(WorklogEntry.id, WorklogEntry.body, WorklogEntry.seq)
        .where(WorklogEntry.workstream_id == workstream_id, WorklogEntry.kind == "ledger")
        .order_by(WorklogEntry.seq)
    )).all()


async def test_append_reports_the_last_seq_it_wrote(session):
    result = await _append(session, entries=[
        {"kind": "ledger", "body": "a\n"}, {"kind": "ledger", "body": "b\n"},
    ])
    seqs = (await session.execute(
        select(WorklogEntry.seq).where(WorklogEntry.workstream_id == result.workstream.id)
    )).scalars().all()
    assert result.last_seq == max(seqs)


async def test_expected_last_seq_zero_opens_a_new_workstream(session):
    result = await _append(session, expected_last_seq=0)
    assert result.workstream.key == "plan-a"
    rows = await _ledger(session, result.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (result.entry_ids[0], "Task 1: complete\n", result.last_seq),
    ]


async def test_a_matching_expected_last_seq_appends(session):
    first = await _append(session)
    second = await _append(
        session, entries=[{"kind": "ledger", "body": "Task 2: complete\n"}],
        expected_last_seq=first.last_seq,
    )
    rows = await _ledger(session, first.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (first.entry_ids[0], "Task 1: complete\n", first.last_seq),
        (second.entry_ids[0], "Task 2: complete\n", second.last_seq),
    ]


async def test_a_stale_expected_last_seq_writes_nothing(session):
    first = await _append(session)
    with pytest.raises(worklog.WorklogSeqConflict) as caught:
        await _append(session, entries=[{"kind": "ledger", "body": "again\n"}], expected_last_seq=0)
    assert (caught.value.kind, caught.value.expected, caught.value.current) == (
        "ledger", 0, first.last_seq,
    )
    count = (await session.execute(
        select(func.count()).select_from(WorklogEntry)
        .where(WorklogEntry.workstream_id == first.workstream.id)
    )).scalar_one()
    assert count == 1


async def test_a_refused_precondition_creates_no_workstream(session):
    with pytest.raises(worklog.WorklogSeqConflict):
        await _append(session, expected_last_seq=5)
    assert await worklog.get_workstream(session, project="proj", key="plan-a") is None


async def test_a_refused_precondition_leaves_a_closed_workstream_closed(session):
    first = await _append(session)
    await worklog.update_workstream(session, first.workstream.id, state="closed")
    with pytest.raises(worklog.WorklogSeqConflict):
        await _append(session, expected_last_seq=first.last_seq + 1000)
    state = (await session.execute(
        text("SELECT state FROM workstreams WHERE id = CAST(:id AS uuid)"),
        {"id": str(first.workstream.id)},
    )).scalar_one()
    assert state == "closed"


async def test_the_precondition_counts_only_its_own_kind(session):
    ledger = await _append(session)
    await _append(session, entries=[{"kind": "checkpoint", "body": "## State\nx"}])
    result = await _append(
        session, entries=[{"kind": "ledger", "body": "Task 2\n"}],
        expected_last_seq=ledger.last_seq,
    )
    rows = await _ledger(session, ledger.workstream.id)
    assert [(r.id, r.body, r.seq) for r in rows] == [
        (ledger.entry_ids[0], "Task 1: complete\n", ledger.last_seq),
        (result.entry_ids[0], "Task 2\n", result.last_seq),
    ]


async def test_the_precondition_refuses_a_mixed_kind_append(session):
    with pytest.raises(ValueError, match="one kind"):
        await _append(
            session,
            entries=[{"kind": "ledger", "body": "a\n"}, {"kind": "note", "body": "n"}],
            expected_last_seq=0,
        )


async def test_two_appends_expecting_the_same_seq_admit_exactly_one(committed):
    async with committed() as first, committed() as second:
        await worklog.append(
            first, project=RACE_PROJECT, key="cas", run_key="r",
            entries=[{"kind": "ledger", "body": "one\n"}], expected_last_seq=0,
        )
        racing = asyncio.create_task(worklog.append(
            second, project=RACE_PROJECT, key="cas", run_key="r",
            entries=[{"kind": "ledger", "body": "two\n"}], expected_last_seq=0,
        ))
        await asyncio.sleep(0.3)
        assert not racing.done(), "the second append must wait on the first's lock"
        await first.commit()
        with pytest.raises(worklog.WorklogSeqConflict):
            await racing
        await second.rollback()
    async with committed() as check:
        bodies = (await check.execute(
            text(
                "SELECT e.body FROM worklog_entries e JOIN workstreams w ON w.id = e.workstream_id "
                "WHERE w.project = :p AND w.key = 'cas'"
            ),
            {"p": RACE_PROJECT},
        )).scalars().all()
    assert bodies == ["one\n"]


async def _open_race_workstream(factory, key) -> tuple[uuid.UUID, int]:
    async with factory() as setup:
        result = await worklog.append(
            setup, project=RACE_PROJECT, key=key, run_key="r",
            entries=[{"kind": "ledger", "body": "zero\n"}],
        )
        await setup.commit()
        return result.workstream.id, result.last_seq


async def test_an_append_waiting_on_a_close_reads_the_closed_row(committed):
    # The reopen UPDATE takes the same row lock, so only the transition shows
    # the SELECT's own lock: read before the close commits, the append would
    # see an open row, continue it, and journal no reopening.
    ws_id, _ = await _open_race_workstream(committed, "close-race")
    async with committed() as closer, committed() as appender:
        await worklog.update_workstream(closer, ws_id, state="closed")
        racing = asyncio.create_task(worklog.append(
            appender, project=RACE_PROJECT, key="close-race", run_key="r",
            entries=[{"kind": "note", "body": "late"}],
        ))
        await asyncio.sleep(0.3)
        assert not racing.done(), "the append must wait on the close's row lock"
        await closer.commit()
        result = await racing
        await appender.commit()
    assert result.workstream.state == "open"
    async with committed() as check:
        journalled = [e for e, _ in await _events(check, ws_id)]
    assert journalled[-2:] == ["workstream_closed", "workstream_reopened"]


async def test_two_appends_to_an_existing_workstream_expecting_one_seq_admit_one(committed):
    ws_id, seq = await _open_race_workstream(committed, "cas-existing")
    async with committed() as first, committed() as second:
        await worklog.append(
            first, project=RACE_PROJECT, key="cas-existing", run_key="r",
            entries=[{"kind": "ledger", "body": "one\n"}], expected_last_seq=seq,
        )
        racing = asyncio.create_task(worklog.append(
            second, project=RACE_PROJECT, key="cas-existing", run_key="r",
            entries=[{"kind": "ledger", "body": "two\n"}], expected_last_seq=seq,
        ))
        await asyncio.sleep(0.3)
        assert not racing.done(), "the second append must wait on the first's row lock"
        await first.commit()
        with pytest.raises(worklog.WorklogSeqConflict):
            await racing
        await second.rollback()
    async with committed() as check:
        bodies = (await check.execute(
            select(WorklogEntry.body).where(WorklogEntry.workstream_id == ws_id).order_by(WorklogEntry.seq)
        )).scalars().all()
    assert bodies == ["zero\n", "one\n"]
