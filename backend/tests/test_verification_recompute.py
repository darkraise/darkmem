"""T2.09 — the verification_recompute drain: the fast arm over sources_changed,
and the slow reconciliation arm that closes T2.10's I-4 finding.

``recompute_fact`` (T2.03) is out of scope and untouched; every assertion here
is about *which* facts get called with it and *when*, never about the ladder's
own decision table (that is ``tests/test_verification_ladder.py`` and
``tests/test_ladder_journaling.py``'s job).

Organised by the brief's "at minimum" list, each with a name naming the
property so a reader can match a failure straight back to the brief.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.repositories.fact_sources import FactSourceRepository as _FSR
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.dream_jobs import VERIFICATION_RECOMPUTE_JOB_KEY, register_dream_jobs
from app.services.events import record_event
from app.services.job_registry import JobRegistry
from app.services.verification_recompute import (
    DEFAULT_FAST_BATCH,
    DEFAULT_SLOW_BATCH,
    RECOMPUTE_CONFIG_SCHEMA,
    run_recompute,
)

T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


async def _tail(session, query: str) -> tuple:
    row = (await session.execute(text(query))).mappings().first()
    if row is None:
        return None, None
    return row["created_at"], row["id"]


@pytest.fixture
async def _reset_recompute_state(session):
    """Isolate a test from both the job's real cross-connection bookkeeping
    row AND the real, permanently-committed data other suites leave behind.

    Two distinct sources of cross-test interference, both real (not a bug in
    this suite's own isolation, which the rolled-back ``session`` fixture
    otherwise guarantees):

    1. Several sibling suites (``test_dream_jobs.py``, this file's own
       ``TestJobWiring``) trigger the real job through a bare
       ``create_async_engine`` rather than the rolled-back ``session``
       fixture, so their writes to ``verification_recompute_state`` are
       genuinely committed and outlive their test.
    2. ``test_sources_changed_emit.py``'s Phase-5-through-the-real-pipeline
       tests (``setup_database``-scoped, not ``session``-scoped) commit real
       ``sources_changed`` events and then delete their own
       ``knowledge_triples`` rows in a ``finally`` block — but ``events`` is
       append-only (a DB trigger forbids UPDATE/DELETE), so the event rows
       for those now-deleted facts survive forever in the shared database.

    A watermark reset all the way to epoch would still see every one of
    those orphaned events on the very first drain of this whole pytest
    process — cheap here (a "missing" hold, `recompute_fact`'s own documented
    behaviour for a raced-out fact_id), but it silently inflates this
    suite's own event/recompute counts by however many leftovers exist,
    which is exactly the kind of assertion this suite makes ("recomputed
    == 1"). Seeding the watermark and the slow-arm cursor to whatever is
    *already at the tail* — rather than deleting the row to `None` — makes
    every test start counting from a known "nothing outstanding" baseline:
    this test's own later events/facts, created inside its own transaction,
    always sort after that tail (a strictly later transaction cannot tie a
    prior transaction's `now()`, and ties within one transaction are what
    the tuple compare itself is for), so nothing this test writes is ever
    skipped, and nothing pre-existing is ever replayed.

    **Deliberately not autouse.** This fixture's own write sits inside the
    rolled-back ``session`` transaction until the *test function* returns —
    the SAVEPOINT ``session.commit()`` ends here is not the outer transaction
    the ``session`` fixture holds open until teardown (see ``conftest.py``).
    ``TestJobWiring`` writes the *same* ``config`` row for real, through its
    own separate bare-engine connection, from inside its own test body. If
    this fixture ran there too (autouse), its still-open row-insert would
    block that second connection's write to the same primary key, which
    can only be released by the fixture's own teardown — which cannot run
    until the test body (blocked on that very write) returns. Every other
    class below explicitly opts in via ``pytestmark``.
    """
    from app.models.config import Config

    event_ts, event_id = await _tail(
        session,
        "SELECT created_at, id FROM events WHERE event_type = 'sources_changed' "
        "ORDER BY created_at DESC, id DESC LIMIT 1",
    )
    fact_ts, fact_id = await _tail(
        session,
        "SELECT created_at, id FROM knowledge_triples ORDER BY created_at DESC, id DESC LIMIT 1",
    )
    state = {
        "watermark_created_at": event_ts.isoformat() if event_ts else None,
        "watermark_id": event_id,
        "slow_arm_last_run_at": None,
        "slow_cursor_created_at": fact_ts.isoformat() if fact_ts else None,
        "slow_cursor_id": str(fact_id) if fact_id else None,
    }
    row = (
        await session.execute(select(Config).where(Config.key == "verification_recompute_state"))
    ).scalar_one_or_none()
    if row is None:
        session.add(Config(key="verification_recompute_state", value=state))
    else:
        row.value = state
    await session.commit()
    yield


# ─────────────────────────── fixtures/helpers ───────────────────────────


async def _make_fact(session, *, key: str, status: str | None = None, project="default") -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=key,
        subject_name="darkmem",
        object_name=key,
        rel_type="USES",
        fact=f"darkmem uses {key}",
        reference_time=T0,
        project=project,
    )
    if status is not None:
        # Raw SQL, not set_verification_status: seeding the starting state
        # through the ladder's own writer would itself journal a transition,
        # polluting the event counts this suite asserts on the *drain's* own
        # work, not the fixture's.
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = CAST(:status AS text) "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"status": status, "id": row["id"]},
        )
    await session.commit()
    return row["id"]


async def _add_origin(session, fact_id, origin_key, *, kind="memory") -> str:
    row = await _FSR(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"{kind}:{origin_key}",
        origin_key=origin_key,
    )
    await session.commit()
    return row["id"]


async def _remove_source(session, source_id) -> None:
    await session.execute(
        text("DELETE FROM fact_sources WHERE id = CAST(:id AS uuid)"), {"id": source_id}
    )
    await session.commit()


async def _emit_sources_changed(session, *, fact_id, memory_ref, project="default") -> None:
    """Mimics what fact_lift/fact_provenance actually emit -- same event type,
    same object_type/object_id, same payload shape -- without pulling either
    producer (out of scope) into this suite."""
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=UUID(fact_id),
        project=project,
        payload={"fact_id": fact_id, "memory_id": memory_ref},
    )
    await session.commit()


async def _status_of(session, fact_id) -> str:
    result = await session.execute(
        text("SELECT verification_status FROM knowledge_triples WHERE id = CAST(:id AS uuid)"),
        {"id": fact_id},
    )
    return result.scalar_one()


async def _verified_events(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": fact_id},
    )
    return [row[0] for row in result.all()]


# ─────────────────────── 1. fast arm promotes ───────────────────────


class TestFastArmPromotes:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_drain_finds_a_lifted_fact_and_promotes_it(self, session):
        fact_id = await _make_fact(session, key="promote-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert await _status_of(session, fact_id) == "corroborated"
        assert outcome.drain.events_scanned == 1
        assert outcome.drain.facts_recomputed == 1
        assert outcome.drain.transitions == 1
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["outcome"] == "promote"


# ─────────────────────── 2. withdrawal demotes ───────────────────────


class TestWithdrawalDemotes:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_withdrawn_source_demotes_corroborated_to_candidate(self, session):
        # Same-kind, close-in-time origins: no diversity gate, no time gate,
        # so N = CORROBORATION_N_DEFAULT = 3.
        fact_id = await _make_fact(session, key="demote-1", status="corroborated")
        s1 = await _add_origin(session, fact_id, "sess-a")
        await _add_origin(session, fact_id, "sess-b")
        await _add_origin(session, fact_id, "sess-c")

        await _remove_source(session, s1)
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-a")

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert await _status_of(session, fact_id) == "candidate"
        assert outcome.drain.transitions == 1
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["outcome"] == "demote"
        assert events[0]["before"] == {"verification_status": "corroborated"}
        assert events[0]["after"] == {"verification_status": "candidate"}


# ─────────────────────── 3. watermark does not replay ───────────────────────


class TestWatermarkDoesNotReplay:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_second_run_over_the_same_events_journals_nothing_new(self, session):
        fact_id = await _make_fact(session, key="promote-2")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        first = await run_recompute(session, now=T0)
        await session.commit()
        assert first.drain.events_scanned == 1
        assert len(await _verified_events(session, fact_id)) == 1

        second = await run_recompute(session, now=T0 + timedelta(minutes=2))
        await session.commit()

        # The watermark has already passed this event; nothing left to drain.
        assert second.drain.events_scanned == 0
        assert second.drain.facts_recomputed == 0
        # Still exactly one verified event -- a phantom re-journal on the
        # unchanged corroborated fact would double this.
        assert len(await _verified_events(session, fact_id)) == 1

    async def test_row_state_is_unchanged_by_a_second_run(self, session):
        fact_id = await _make_fact(session, key="promote-2b")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        await run_recompute(session, now=T0)
        await session.commit()
        status_after_first = await _status_of(session, fact_id)

        await run_recompute(session, now=T0 + timedelta(minutes=2))
        await session.commit()
        assert await _status_of(session, fact_id) == status_after_first == "corroborated"


# ─────────────── 4. same-transaction events are not dropped ───────────────


class TestSameTransactionEventsSurvive:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_two_events_sharing_one_created_at_are_both_drained(self, session):
        """Two sources_changed rows written back-to-back inside this test's
        single outer transaction share one `now()` (T2.06's finding). A drain
        forced to stop after the first (batch_size=1) must still find the
        second on the very next call despite the identical timestamp -- which
        is exactly what a bare `created_at > watermark` compare cannot do.
        """
        fact_a = await _make_fact(session, key="tie-a")
        fact_b = await _make_fact(session, key="tie-b")
        await _add_origin(session, fact_a, "sess-a", kind="memory")
        await _add_origin(session, fact_a, "repo-a", kind="code")
        await _add_origin(session, fact_b, "sess-b", kind="memory")
        await _add_origin(session, fact_b, "repo-b", kind="code")

        # Emitted in immediate succession inside the same still-open
        # transaction -- both rows share created_at under conditional_savepoint.
        await _emit_sources_changed(session, fact_id=fact_a, memory_ref="repo-a")
        await _emit_sources_changed(session, fact_id=fact_b, memory_ref="repo-b")

        created_ats = (
            await session.execute(
                text(
                    "SELECT DISTINCT created_at FROM events "
                    "WHERE event_type = 'sources_changed' "
                    "AND object_id IN (CAST(:a AS uuid), CAST(:b AS uuid))"
                ),
                {"a": fact_a, "b": fact_b},
            )
        ).scalars().all()
        assert len(created_ats) == 1, (
            "fixture assumption broken: the two events must share one "
            "created_at for this test to exercise the tie-break at all"
        )

        first = await run_recompute(session, batch_size=1, now=T0)
        await session.commit()
        assert first.drain.events_scanned == 1

        second = await run_recompute(session, batch_size=1, now=T0)
        await session.commit()
        assert second.drain.events_scanned == 1, (
            "the second, same-timestamp event was dropped by the watermark"
        )

        assert await _status_of(session, fact_a) == "corroborated"
        assert await _status_of(session, fact_b) == "corroborated"


# ─────────────── 5. the slow arm heals a swallowed emit (I-4) ───────────────


class TestSlowArmHealsSwallowedEmit:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_slow_arm_promotes_a_fact_with_no_sources_changed_event(self, session):
        """The exact I-4 shape: fact_sources carries promotable evidence, and
        no sources_changed event was ever written for it -- simulating
        record_event's documented degrade-and-swallow. Only the slow arm,
        which never reads events at all, can find this."""
        fact_id = await _make_fact(session, key="healed-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        # Deliberately: no _emit_sources_changed call at all.

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert outcome.drain.events_scanned == 0
        assert outcome.slow_arm_ran is True
        assert outcome.reconcile.facts_scanned >= 1
        assert outcome.reconcile.facts_healed == 1
        assert await _status_of(session, fact_id) == "corroborated"
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["outcome"] == "promote"

    async def test_slow_arm_does_not_run_before_its_interval_elapses(self, session):
        fact_id = await _make_fact(session, key="healed-2")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        # First tick runs the slow arm (nothing persisted yet -> always due)
        # and heals nothing relevant here; drain the state to "just ran".
        await run_recompute(session, now=T0, slow_arm_interval_seconds=600)
        await session.commit()

        # A second fact appears between ticks, still with no event.
        fact_id2 = await _make_fact(session, key="healed-3")
        await _add_origin(session, fact_id2, "sess-x", kind="memory")
        await _add_origin(session, fact_id2, "repo-y", kind="code")

        outcome = await run_recompute(
            session, now=T0 + timedelta(seconds=5), slow_arm_interval_seconds=600
        )
        await session.commit()

        assert outcome.slow_arm_ran is False
        assert await _status_of(session, fact_id2) == "candidate"

        # Once the interval elapses, the backstop catches it.
        outcome2 = await run_recompute(
            session, now=T0 + timedelta(seconds=700), slow_arm_interval_seconds=600
        )
        await session.commit()
        assert outcome2.slow_arm_ran is True
        assert await _status_of(session, fact_id2) == "corroborated"


# ─────────────────────── 6. confirmed is never demoted ───────────────────────


class TestConfirmedNeverDemoted:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_a_confirmed_fact_holds_through_the_fast_arm(self, session):
        fact_id = await _make_fact(session, key="confirmed-1", status="confirmed")
        s1 = await _add_origin(session, fact_id, "sess-a")
        await _remove_source(session, s1)
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-a")

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert await _status_of(session, fact_id) == "confirmed"
        # decide() returns a hold for a confirmed current_status, so this is
        # not a transition -- but the call still happened (recomputed=1).
        assert outcome.drain.facts_recomputed == 1
        assert outcome.drain.transitions == 0

    async def test_a_confirmed_fact_is_excluded_from_the_slow_arm_slice(self, session):
        """Belt-and-suspenders over the ladder's own refusal: the slow arm's
        query filters verification_status != 'confirmed' outright, so a
        confirmed fact costs the slice nothing even though decide() would
        also have held it."""
        fact_id = await _make_fact(session, key="confirmed-2", status="confirmed")
        await _add_origin(session, fact_id, "sess-a")

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert await _status_of(session, fact_id) == "confirmed"
        assert outcome.reconcile.facts_healed == 0


# ───────────────── 7. per-fact isolation: one poisonous fact ─────────────────


class TestPerFactIsolation:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_one_failing_fact_does_not_block_its_siblings(self, session, monkeypatch):
        import app.services.verification_recompute as vr_module

        good_fact = await _make_fact(session, key="iso-good")
        await _add_origin(session, good_fact, "sess-a", kind="memory")
        await _add_origin(session, good_fact, "repo-b", kind="code")
        bad_fact = await _make_fact(session, key="iso-bad")
        await _add_origin(session, bad_fact, "sess-c", kind="memory")
        await _add_origin(session, bad_fact, "repo-d", kind="code")

        await _emit_sources_changed(session, fact_id=good_fact, memory_ref="repo-b")
        await _emit_sources_changed(session, fact_id=bad_fact, memory_ref="repo-d")

        real_recompute = vr_module.recompute_fact

        async def flaky(session, fact_id, **kwargs):
            if str(fact_id) == bad_fact:
                raise RuntimeError("simulated poisonous fact")
            return await real_recompute(session, fact_id, **kwargs)

        monkeypatch.setattr(vr_module, "recompute_fact", flaky)

        outcome = await run_recompute(session, now=T0)
        await session.commit()

        assert outcome.drain.facts_failed == 1
        assert outcome.drain.facts_recomputed == 1
        assert await _status_of(session, good_fact) == "corroborated"
        assert await _status_of(session, bad_fact) == "candidate"

        # The watermark still advanced past both events -- the poisonous
        # fact's event is not retried by the fast arm forever; the slow arm
        # is what eventually revisits it.
        second = await run_recompute(session, now=T0 + timedelta(minutes=5))
        await session.commit()
        assert second.drain.events_scanned == 0


# ───────────────────── 8. job wiring / Tier-C isolation ─────────────────────


class TestJobWiring:
    async def test_the_job_is_wired_with_a_real_runner_and_its_own_schema(self):
        """Proves wiring — schema, cron, floor, ceiling, and that the real
        runner completes through JobRegistry.trigger() end to end.

        Deliberately forces the slow arm's ``due`` check False before
        triggering: this is a real, non-rolled-back trigger against whatever
        the shared test database's ``knowledge_triples`` happens to hold at
        this point in the whole test session (other real-pipeline suites,
        e.g. ``test_sources_changed_emit.py``, leave real committed rows
        behind for the duration of the process). The slow arm's own
        substance — that it scans, heals and rotates correctly — is fully
        exercised elsewhere in this file over the isolated ``session``
        fixture; this test's job is only to prove the wiring, so it should
        not also be a referendum on how large the shared table happens to be
        or how loaded the shared database is when it runs.
        """
        from app.models.config import Config

        engine = create_async_engine(settings.test_database_url)
        registry = JobRegistry(async_sessionmaker(engine, expire_on_commit=False))
        register_dream_jobs(registry)
        try:
            job = registry.get(VERIFICATION_RECOMPUTE_JOB_KEY)
            assert job.config_schema is RECOMPUTE_CONFIG_SCHEMA
            assert {fd.key for fd in job.config_schema} == {
                "batch_size", "slow_arm_batch_size", "slow_arm_interval_seconds",
            }
            assert job.default_config["batch_size"] == DEFAULT_FAST_BATCH
            assert job.default_config["slow_arm_batch_size"] == DEFAULT_SLOW_BATCH
            assert job.default_cron == "*/2 * * * *"
            assert job.min_interval_seconds == 30
            assert job.max_run_seconds == 120

            async with registry.session_factory() as seed_session:
                forced = {"slow_arm_last_run_at": datetime.now(timezone.utc).isoformat()}
                existing = (
                    await seed_session.execute(
                        select(Config).where(Config.key == "verification_recompute_state")
                    )
                ).scalar_one_or_none()
                if existing is None:
                    seed_session.add(Config(key="verification_recompute_state", value=forced))
                else:
                    existing.value = forced
                await seed_session.commit()

            cfg = await registry.trigger(VERIFICATION_RECOMPUTE_JOB_KEY)
            assert cfg.last_status == "ok", cfg.last_error
        finally:
            await registry.stop_all()
            await engine.dispose()
