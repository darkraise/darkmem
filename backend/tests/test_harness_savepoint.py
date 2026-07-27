"""The conftest ``session`` fixture's transaction isolation.

The fixture runs each test inside an outer transaction it rolls back at
teardown, and relies on SQLAlchemy 2.0's default
``join_transaction_mode="conditional_savepoint"`` to keep a test's own
``commit()`` inside a SAVEPOINT rather than letting it reach that boundary.

This is harness machinery, but it sits underneath every test in the suite, so
when it misbehaves it does so everywhere at once and reads as product
behaviour. It did: the fixture also carried the SQLAlchemy 1.x recipe that
reopened the savepoint by hand from an ``after_transaction_end`` listener, and
that listener fired while an application-level ``session.begin_nested()`` was
still unwinding. SQLAlchemy refuses that, and ``record_event`` caught the
refusal and logged "failed to journal" on every call in the suite while the row
landed correctly. T1.07 built that message to degrade loudly, and a message
that is always on carries no information — a real journal failure was
indistinguishable from harness noise.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.events import record_event

pytestmark = pytest.mark.asyncio

JOURNAL_FAILURE = "failed to journal"


async def test_record_event_succeeds_without_reporting_a_failure(session, caplog):
    """The guard that keeps ``test_record_event_swallows_a_real_db_failure``
    honest: on the success path the loud message must be absent, or that test
    passes on harness noise rather than on the failure it induces."""
    with caplog.at_level("ERROR", logger="app.services.events"):
        await record_event(
            session,
            event_type="auth_login_success",
            object_type="system",
            payload={"ip": "10.0.0.2"},
        )

    assert JOURNAL_FAILURE not in caplog.text
    written = (await session.execute(
        text("SELECT count(*) FROM events WHERE event_type = 'auth_login_success'"),
    )).scalar()
    assert written == 1


async def test_a_caller_owned_savepoint_commits_and_rolls_back_normally(session):
    """``record_event`` is not the only nested-transaction user, and the
    fixture must leave a caller-opened SAVEPOINT alone in both directions."""
    async with session.begin_nested():
        await session.execute(
            text("INSERT INTO config (key, value) VALUES ('kept', '{}'::jsonb)"),
        )

    with pytest.raises(RuntimeError):
        async with session.begin_nested():
            await session.execute(
                text("INSERT INTO config (key, value) VALUES ('dropped', '{}'::jsonb)"),
            )
            raise RuntimeError("caller aborts its own savepoint")

    keys = set((await session.execute(
        text("SELECT key FROM config WHERE key IN ('kept', 'dropped')"),
    )).scalars())
    assert keys == {"kept"}


async def test_a_test_that_commits_still_sees_its_own_writes(session):
    """Half of the isolation contract. The partner test below is what proves
    this commit never reached the fixture's outer transaction; the two only
    mean anything read together, and in this file order."""
    await session.execute(
        text("INSERT INTO config (key, value) VALUES ('committed-key', '{}'::jsonb)"),
    )
    await session.commit()

    keys = set((await session.execute(
        text("SELECT key FROM config WHERE key = 'committed-key'"),
    )).scalars())
    assert keys == {"committed-key"}


async def test_the_fixture_rolls_back_what_the_previous_test_committed(session):
    """The other half. A fixture that let a test's ``commit()`` through would
    leak that row into every test after it, which is how a green suite starts
    depending on its own execution order."""
    leaked = set((await session.execute(
        text("SELECT key FROM config WHERE key = 'committed-key'"),
    )).scalars())
    assert leaked == set()
