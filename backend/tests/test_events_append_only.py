"""`events` is append-only, and stays append-only as partitions come and go.

Append-only is what makes the timeline trustworthy and the calendar honest
(doc 04 §8.1), so it is enforced structurally by triggers rather than by
convention. Two properties are easy to get wrong and are asserted here
explicitly:

1. **A statement-level `BEFORE TRUNCATE` trigger on a partitioned parent does
   not cascade to its children.** Row-level triggers do — `UPDATE`/`DELETE` on a
   child are caught by the parent's trigger — but `TRUNCATE events_202607`
   addresses the child directly and never reaches the parent's trigger. Without
   a per-child guard that one statement silently erases a month of the audit
   trail. Measured on PostgreSQL 17.
2. **Every partition-creating path must attach that guard.** Which is why there
   is exactly one such path, `events_ensure_partition`, used by the baseline,
   the boot reconciliation, and the cleanup job's maintenance arm alike.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.services.events import reconcile_event_partitions, record_event


async def _seed_one(session) -> None:
    await record_event(session, event_type="created", object_type="system")
    await session.commit()


async def _partition_names(session) -> list[str]:
    rows = await session.execute(
        text(
            "SELECT c.relname FROM pg_inherits i "
            "JOIN pg_class c ON c.oid = i.inhrelid "
            "JOIN pg_class p ON p.oid = i.inhparent "
            "WHERE p.relname = 'events' ORDER BY c.relname"
        )
    )
    return [r[0] for r in rows]


# ── The three forbidden verbs ───────────────────────────────────────


@pytest.mark.asyncio
async def test_insert_is_allowed(session):
    await _seed_one(session)
    count = (await session.execute(text("SELECT count(*) FROM events"))).scalar_one()
    assert count >= 1


@pytest.mark.asyncio
async def test_update_raises(session):
    await _seed_one(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text("UPDATE events SET event_type = 'tampered'"))
    await session.rollback()


@pytest.mark.asyncio
async def test_delete_raises(session):
    await _seed_one(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text("DELETE FROM events"))
    await session.rollback()


@pytest.mark.asyncio
async def test_truncate_raises(session):
    await _seed_one(session)
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text("TRUNCATE events"))
    await session.rollback()


# ── The same three, addressed at a child partition directly ─────────


@pytest.mark.asyncio
async def test_update_on_a_child_partition_raises(session):
    await _seed_one(session)
    child = (await _partition_names(session))[0]
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text(f"UPDATE {child} SET event_type = 'tampered'"))
    await session.rollback()


@pytest.mark.asyncio
async def test_delete_on_a_child_partition_raises(session):
    await _seed_one(session)
    child = (await _partition_names(session))[0]
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text(f"DELETE FROM {child}"))
    await session.rollback()


@pytest.mark.asyncio
async def test_truncate_on_a_child_partition_raises(session):
    """The invariant-bearing one: this passes only because of the per-child
    guard. Drop that guard and every other test in this file still passes while
    a month of the journal becomes erasable in one statement."""
    await _seed_one(session)
    child = (await _partition_names(session))[0]
    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text(f"TRUNCATE {child}"))
    await session.rollback()


@pytest.mark.asyncio
async def test_every_child_partition_carries_a_truncate_guard(session):
    children = await _partition_names(session)
    assert children, "the baseline must land at least one child, or inserts fail"
    for child in children:
        guarded = (
            await session.execute(
                text(
                    "SELECT count(*) FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "WHERE c.relname = :child AND NOT t.tgisinternal "
                    "AND t.tgname = :guard"
                ),
                {"child": child, "guard": f"{child}_forbid_truncate"},
            )
        ).scalar_one()
        assert guarded == 1, f"{child} has no TRUNCATE guard"


# ── Partitions are created ahead of need and reconciled at boot ─────


@pytest.mark.asyncio
async def test_baseline_lands_current_and_next_month(session):
    # A RANGE parent with no matching child rejects every insert, so month-0
    # must exist before the first journaled write, not at the first boot.
    children = await _partition_names(session)
    expected = (
        await session.execute(
            text(
                "SELECT 'events_' || to_char("
                "  date_trunc('month', now() AT TIME ZONE 'UTC'), 'YYYYMM'), "
                "       'events_' || to_char("
                "  date_trunc('month', now() AT TIME ZONE 'UTC') "
                "  + interval '1 month', 'YYYYMM')"
            )
        )
    ).one()
    assert expected[0] in children
    assert expected[1] in children


@pytest.mark.asyncio
async def test_reconcile_is_idempotent(session):
    before = await _partition_names(session)
    first = await reconcile_event_partitions(session)
    await session.commit()
    after_first = await _partition_names(session)
    second = await reconcile_event_partitions(session)
    await session.commit()
    after_second = await _partition_names(session)

    assert first == second
    assert after_first == after_second
    # The baseline already created exactly what reconcile wants, so a boot on a
    # fresh database adds nothing.
    assert before == after_first


@pytest.mark.asyncio
async def test_reconcile_regrows_a_dropped_partition_with_its_guard(session):
    """A restored dump, or a month that rolled over while the process ran, must
    self-heal — including the guard, not just the table."""
    next_child = (
        await session.execute(
            text(
                "SELECT 'events_' || to_char("
                "  date_trunc('month', now() AT TIME ZONE 'UTC') "
                "  + interval '1 month', 'YYYYMM')"
            )
        )
    ).scalar_one()
    await session.execute(text(f"DROP TABLE {next_child}"))
    await session.commit()
    assert next_child not in await _partition_names(session)

    await reconcile_event_partitions(session)
    await session.commit()

    assert next_child in await _partition_names(session)
    guarded = (
        await session.execute(
            text(
                "SELECT count(*) FROM pg_trigger t "
                "JOIN pg_class c ON c.oid = t.tgrelid "
                "WHERE c.relname = :child AND NOT t.tgisinternal "
                "AND t.tgname = :guard"
            ),
            {"child": next_child, "guard": f"{next_child}_forbid_truncate"},
        )
    ).scalar_one()
    assert guarded == 1


@pytest.mark.asyncio
async def test_a_regrown_partition_is_not_truncatable(session):
    next_child = (
        await session.execute(
            text(
                "SELECT 'events_' || to_char("
                "  date_trunc('month', now() AT TIME ZONE 'UTC') "
                "  + interval '1 month', 'YYYYMM')"
            )
        )
    ).scalar_one()
    await session.execute(text(f"DROP TABLE {next_child}"))
    await session.commit()
    await reconcile_event_partitions(session)
    await session.commit()

    with pytest.raises(DBAPIError, match="append-only"):
        await session.execute(text(f"TRUNCATE {next_child}"))
    await session.rollback()


# ── api_key_id and actor land inert (their writer is T4.02) ─────────


@pytest.mark.asyncio
async def test_api_key_id_and_actor_exist_and_are_nullable(session):
    rows = await session.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'events' "
            "AND column_name IN ('api_key_id', 'actor') ORDER BY column_name"
        )
    )
    assert [(r[0], r[1]) for r in rows] == [("actor", "YES"), ("api_key_id", "YES")]
