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
    DEFAULT_SLOW_ARM_INTERVAL_SECONDS,
    DEFAULT_SLOW_BATCH,
    RECOMPUTE_CONFIG_SCHEMA,
    run_recompute,
)

T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

# The fast arm's I-1 commit-skew margin (_COMMIT_SKEW_MARGIN, 5s in
# verification_recompute.py) means `run_recompute` never reads an event newer
# than `now - margin`. Events this suite emits carry a real Postgres `now()`
# as their `created_at`, not the fixed historical `T0` above (which is only
# ever used for `reference_time`, a cosmetic belief-axis field unrelated to
# drain timing) -- so a `now=` passed to `run_recompute` has to be anchored
# to real wall-clock, comfortably past the margin, or every event this suite
# writes falls on the wrong side of the cutoff and the drain finds nothing.
# Computed fresh per call (never once at import time) so it stays valid
# under arbitrary collection/scheduling delay, not just a fixed offset from
# module import.
_SAFE_MARGIN_BUFFER = timedelta(seconds=30)


def _safe_now() -> datetime:
    return datetime.now(timezone.utc) + _SAFE_MARGIN_BUFFER


async def _prime_slow_arm(session) -> None:
    """Burn the slow arm's "always due on the first tick" window before a
    test that needs to isolate the fast arm's own behaviour.

    `slow_arm_last_run_at` starts unset for every test (`_reset_recompute_state`
    seeds it to `None`), so the very first `run_recompute` call always runs
    the slow arm regardless of `slow_arm_interval_seconds` -- `due` is an OR,
    and the `is None` branch wins on tick one. The slow arm has no
    commit-skew margin and no per-helper call-count contract of its own, so
    letting it run on the same tick as a test asserting either would let it
    independently reconcile the very fact under test, confounding the
    assertion. Priming with `_safe_now()` (real wall clock + 30s) sets
    `slow_arm_last_run_at` far enough in the future that a later call
    anchored to a *real*, un-inflated timestamp (an event's own recorded
    `created_at`, for instance) reads as comfortably not-yet-due.
    """
    await run_recompute(session, now=_safe_now())
    await session.commit()


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

        outcome = await run_recompute(session, now=_safe_now())
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
        """The withdrawal demotes — one grace cycle after it is detected.

        Two ticks, because T2.46's hysteresis holds the first one. The second
        tick reaches the fact through the slow arm: the fast arm's watermark
        has already passed the withdrawal's event, which is precisely the
        shape that makes the two arms a pair rather than a duplicate.
        """
        # Same-kind, close-in-time origins: no diversity gate, no time gate,
        # so N = CORROBORATION_N_DEFAULT = 3.
        fact_id = await _make_fact(session, key="demote-1", status="corroborated")
        s1 = await _add_origin(session, fact_id, "sess-a")
        await _add_origin(session, fact_id, "sess-b")
        await _add_origin(session, fact_id, "sess-c")

        await _remove_source(session, s1)
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-a")

        first = await run_recompute(session, now=_safe_now())
        await session.commit()

        # Labelled, not demoted, and not journalled: the rung has not moved.
        assert await _status_of(session, fact_id) == "corroborated"
        assert first.drain.transitions == 0
        assert await _verified_events(session, fact_id) == []
        # The slow arm ran on this tick too and declined to re-look at the
        # fact the fast arm had just recomputed. Without that skip the window
        # would have closed inside the tick that opened it.
        assert first.reconcile.facts_skipped_fresh == 1

        outcome = await run_recompute(
            session, now=_safe_now() + timedelta(seconds=DEFAULT_SLOW_ARM_INTERVAL_SECONDS)
        )
        await session.commit()

        assert await _status_of(session, fact_id) == "candidate"
        assert outcome.reconcile.facts_healed == 1
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["outcome"] == "demote"
        assert events[0]["before"] == {"verification_status": "corroborated"}
        assert events[0]["after"] == {"verification_status": "candidate"}


class TestExpiredFactsAreNeverJournaledByEitherArm:
    """I-2 (slow arm) + N-1 (fast arm): expiry lives on the belief axis
    (`expired_at`), which `KnowledgeTripleRepository.expire` never conflates
    with `verification_status`. A dead fact is not merely "under-sourced",
    and neither arm may recompute or journal a transition on one.

    **N-1 correction, recorded here so the mistake is not repeated.** An
    earlier draft of this suite (and of the module's own comments) claimed
    "`fact_provenance` deliberately withholds `sources_changed` when it
    expires a fact inline" as the reason only the slow arm needed guarding.
    That claim is false: `fact_provenance._withdraw` emits `sources_changed`
    *unconditionally* for every source row it withdraws, including the
    source whose withdrawal is what just expired the fact -- doc 08 3.3's
    own contract is "expires inline ... **then enqueues**", not "instead of
    enqueuing". So the fast arm reaches a freshly-dead fact through an
    ordinary, correctly-emitted event just as readily as the slow arm can
    reach one through a slice-read race, and both tests below have to hold
    for the same underlying property: `_still_live`, checked inside the
    per-fact savepoint on **both** arms, not a claim about who emits what.
    """

    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_an_expired_corroborated_fact_is_never_scanned_or_demoted(self, session):
        fact_id = await _make_fact(session, key="expired-1", status="corroborated")
        # Left with a single origin -- well under any N -- so if the slow arm
        # *did* reach this row it would demote it, which is exactly the
        # false signal I-2 flags: journaled as an ordinary `verified` demote,
        # indistinguishable from a live one in the payload.
        await _add_origin(session, fact_id, "sess-a")
        await KnowledgeTripleRepository(session).expire(fact_id)
        await session.commit()

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert outcome.reconcile.facts_scanned == 0
        assert outcome.reconcile.facts_healed == 0
        # Status axis untouched -- still corroborated, because the slow arm
        # never reached the row to recompute it in the first place.
        assert await _status_of(session, fact_id) == "corroborated"
        assert await _verified_events(session, fact_id) == []

    async def test_fast_arm_skips_an_expired_fact_reached_via_a_real_event(self, session):
        """N-1's exact demonstrated scenario: a corroborated fact whose
        sources are withdrawn expires inline and receives one
        `sources_changed` event per withdrawn source -- exactly what
        `fact_provenance._withdraw` really does (simulated here rather than
        called directly: `fact_provenance.py` is T2.61's file). The fast arm
        must not journal a demote on it."""
        fact_id = await _make_fact(session, key="expired-via-event-1", status="corroborated")
        s1 = await _add_origin(session, fact_id, "sess-a")
        s2 = await _add_origin(session, fact_id, "sess-b")
        s3 = await _add_origin(session, fact_id, "sess-c")

        await _remove_source(session, s1)
        await _remove_source(session, s2)
        await _remove_source(session, s3)
        await KnowledgeTripleRepository(session).expire(fact_id)
        await session.commit()
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-a")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-b")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-c")

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert outcome.drain.events_scanned == 3
        assert outcome.drain.facts_touched == 1  # deduped to one fact_id
        assert outcome.drain.facts_recomputed == 0
        assert outcome.drain.facts_skipped_expired == 1
        assert await _status_of(session, fact_id) == "corroborated"  # untouched, dead
        assert await _verified_events(session, fact_id) == []


# ─────────────────────── 3. watermark does not replay ───────────────────────


class TestWatermarkDoesNotReplay:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_second_run_over_the_same_events_journals_nothing_new(self, session):
        fact_id = await _make_fact(session, key="promote-2")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        base = _safe_now()
        first = await run_recompute(session, now=base)
        await session.commit()
        assert first.drain.events_scanned == 1
        assert len(await _verified_events(session, fact_id)) == 1

        second = await run_recompute(session, now=base + timedelta(minutes=2))
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

        base = _safe_now()
        await run_recompute(session, now=base)
        await session.commit()
        status_after_first = await _status_of(session, fact_id)

        await run_recompute(session, now=base + timedelta(minutes=2))
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

        base = _safe_now()
        first = await run_recompute(session, batch_size=1, now=base)
        await session.commit()
        assert first.drain.events_scanned == 1

        second = await run_recompute(session, batch_size=1, now=base)
        await session.commit()
        assert second.drain.events_scanned == 1, (
            "the second, same-timestamp event was dropped by the watermark"
        )

        assert await _status_of(session, fact_a) == "corroborated"
        assert await _status_of(session, fact_b) == "corroborated"


class TestCommitSkewMargin:
    """N-2: the I-1 commit-skew margin (`_COMMIT_SKEW_MARGIN`) was
    mechanically real but unpinned -- every prior test calls `run_recompute`
    with `now = wall clock + 30s` (`_safe_now()`), which pushes the margin's
    cutoff (`now - margin`) comfortably past every event this suite writes,
    so the `created_at <= :safe_until` conjunct was never exercised by
    anything. Deleting it left all tests green.

    This class anchors `now` to the event's own recorded `created_at`
    instead of wall-clock proximity, so it holds regardless of how fast or
    slow the test process happens to be running.
    """

    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_an_event_inside_the_margin_is_deferred_then_drained_later(self, session):
        await _prime_slow_arm(session)

        fact_id = await _make_fact(session, key="skew-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        event_created_at = (
            await session.execute(
                text(
                    "SELECT created_at FROM events WHERE event_type = 'sources_changed' "
                    "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC, id DESC "
                    "LIMIT 1"
                ),
                {"id": fact_id},
            )
        ).scalar_one()

        # 1s after the event: well inside the 5s margin, so
        # safe_until = now - 5s sits BEFORE the event's own created_at.
        deferred = await run_recompute(
            session, now=event_created_at + timedelta(seconds=1),
        )
        await session.commit()
        assert deferred.drain.events_scanned == 0, (
            "an event inside the commit-skew margin was drained early"
        )
        assert await _status_of(session, fact_id) == "candidate"

        # 10s after the event: comfortably past the margin now.
        drained = await run_recompute(
            session, now=event_created_at + timedelta(seconds=10),
        )
        await session.commit()
        assert drained.drain.events_scanned == 1
        assert await _status_of(session, fact_id) == "corroborated"


class TestLockTimeoutAndLivenessAreActuallyWired:
    """N-3: `TestLockWaitIsBounded` proves `_set_local_lock_timeout` itself
    works, but calls it directly through its own savepoint -- it never
    proves either arm's loop actually calls it. Deleting both
    `await _set_local_lock_timeout(session)` call sites left every existing
    test green. Same shape of gap for `_still_live`: nothing yet proves the
    arms call it rather than merely defining it. Both are pinned here by
    counting real calls through the arms' own code paths, not by re-deriving
    their effects indirectly.
    """

    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_fast_arm_calls_the_lock_timeout_and_liveness_helpers(
        self, session, monkeypatch
    ):
        import app.services.verification_recompute as vr_module

        await _prime_slow_arm(session)

        fact_id = await _make_fact(session, key="wiring-fast-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        lock_calls: list[None] = []
        live_calls: list[str] = []
        real_lock = vr_module._set_local_lock_timeout
        real_live = vr_module._still_live

        async def tracking_lock(session):
            lock_calls.append(None)
            await real_lock(session)

        async def tracking_live(session, fact_id):
            live_calls.append(fact_id)
            return await real_live(session, fact_id)

        monkeypatch.setattr(vr_module, "_set_local_lock_timeout", tracking_lock)
        monkeypatch.setattr(vr_module, "_still_live", tracking_live)

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert outcome.drain.facts_recomputed == 1
        assert len(lock_calls) == 1
        assert live_calls == [fact_id]

    async def test_slow_arm_calls_the_lock_timeout_and_liveness_helpers(
        self, session, monkeypatch
    ):
        import app.services.verification_recompute as vr_module

        fact_id = await _make_fact(session, key="wiring-slow-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        # Deliberately no event -- forces the slow arm, not the fast one,
        # to be the caller under test.

        lock_calls: list[None] = []
        live_calls: list[str] = []
        real_lock = vr_module._set_local_lock_timeout
        real_live = vr_module._still_live

        async def tracking_lock(session):
            lock_calls.append(None)
            await real_lock(session)

        async def tracking_live(session, fact_id):
            live_calls.append(fact_id)
            return await real_live(session, fact_id)

        monkeypatch.setattr(vr_module, "_set_local_lock_timeout", tracking_lock)
        monkeypatch.setattr(vr_module, "_still_live", tracking_live)

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert outcome.reconcile.facts_scanned == 1
        assert len(lock_calls) == 1
        assert live_calls == [fact_id]


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

        outcome = await run_recompute(session, now=_safe_now())
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
        base = _safe_now()
        await run_recompute(session, now=base, slow_arm_interval_seconds=600)
        await session.commit()

        # A second fact appears between ticks, still with no event.
        fact_id2 = await _make_fact(session, key="healed-3")
        await _add_origin(session, fact_id2, "sess-x", kind="memory")
        await _add_origin(session, fact_id2, "repo-y", kind="code")

        outcome = await run_recompute(
            session, now=base + timedelta(seconds=5), slow_arm_interval_seconds=600
        )
        await session.commit()

        assert outcome.slow_arm_ran is False
        assert await _status_of(session, fact_id2) == "candidate"

        # Once the interval elapses, the backstop catches it.
        outcome2 = await run_recompute(
            session, now=base + timedelta(seconds=700), slow_arm_interval_seconds=600
        )
        await session.commit()
        assert outcome2.slow_arm_ran is True
        assert await _status_of(session, fact_id2) == "corroborated"


class TestSlowArmCursorWrap:
    """I-4: the wrap reset is what makes 'eventually every fact is
    revisited' true, and nothing pinned it before this class."""

    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_evidence_behind_the_cursor_heals_only_after_the_wrap_resets(self, session):
        """A fact whose promotable evidence arrives *after* the rotating
        cursor has already passed it sits behind the cursor and is invisible
        to every subsequent slice until the walk wraps back to the start --
        without the reset, it is stuck there forever: I-4's own shape,
        re-opened one level down (a missing *cursor* reset instead of a
        missing *event*).
        """
        fact_id = await _make_fact(session, key="behind-cursor-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")

        base = _safe_now()

        # Pass 1 (slice=1): the only fact in the table is scanned (one
        # origin, below any N -- stays candidate) and the cursor parks
        # exactly on it. 1 row == batch_size, so this is NOT a wrap.
        first = await run_recompute(
            session, slow_arm_batch_size=1, slow_arm_interval_seconds=0, now=base,
        )
        await session.commit()
        assert first.reconcile.facts_scanned == 1
        assert first.reconcile.wrapped is False
        assert await _status_of(session, fact_id) == "candidate"

        # Evidence arrives behind the cursor -- no event emitted. This is
        # deliberately NOT a swallowed-emit case (that is the sibling class
        # above): the emit could fire perfectly and it would not matter,
        # because what stands between this fact and being found is now the
        # slow arm's own cursor position, not events at all.
        await _add_origin(session, fact_id, "repo-b", kind="code")

        # Pass 2: the query is strictly-greater-than the parked cursor, so
        # the one fact -- sitting AT the cursor -- is excluded. The resulting
        # empty slice is what triggers the wrap.
        second = await run_recompute(
            session, slow_arm_batch_size=1, slow_arm_interval_seconds=0,
            now=base + timedelta(seconds=1),
        )
        await session.commit()
        assert second.reconcile.facts_scanned == 0
        assert second.reconcile.wrapped is True
        assert await _status_of(session, fact_id) == "candidate", (
            "the fact healed on the same pass that wrapped -- the test no "
            "longer isolates the reset from the scan that follows it"
        )

        # Pass 3: the reset cursor restarts the walk from the beginning, so
        # the now-promotable fact is finally back in scope.
        third = await run_recompute(
            session, slow_arm_batch_size=1, slow_arm_interval_seconds=0,
            now=base + timedelta(seconds=2),
        )
        await session.commit()
        assert third.reconcile.facts_scanned == 1
        assert third.reconcile.facts_healed == 1
        assert await _status_of(session, fact_id) == "corroborated"


# ─────────────────────── 6. confirmed is never demoted ───────────────────────


class TestConfirmedNeverDemoted:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_a_confirmed_fact_holds_through_the_fast_arm(self, session):
        fact_id = await _make_fact(session, key="confirmed-1", status="confirmed")
        s1 = await _add_origin(session, fact_id, "sess-a")
        await _remove_source(session, s1)
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="memory:sess-a")

        outcome = await run_recompute(session, now=_safe_now())
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

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert await _status_of(session, fact_id) == "confirmed"
        # M-1: assert on facts_scanned, not facts_healed. decide() already
        # holds a confirmed fact unconditionally, so facts_healed == 0 would
        # stay green even with the != 'confirmed' predicate removed from
        # _SLOW_ARM_SLICE -- the query-level exclusion this test exists to
        # pin is only provable by asserting the row is never even scanned.
        assert outcome.reconcile.facts_scanned == 0


# ───────────────── 7. per-fact isolation: one poisonous fact ─────────────────


class TestPerFactIsolation:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_one_failing_fact_does_not_block_its_siblings(self, session, monkeypatch):
        """I-3: the poisonous fact must fail at the *SQL* level, not merely
        raise pure Python before touching the database.

        A pure-Python `raise` never puts the connection's transaction into
        Postgres's aborted state, so it cannot distinguish "the savepoint
        rolled the poisonous fact back" from "the exception was merely
        caught" -- removing `session.begin_nested()` around the per-fact
        call left this test green, because there was never anything at the
        SQL level for the missing savepoint to need to undo. `SELECT 1/0` is
        a real backend error (`DivisionByZeroError`), which Postgres reports
        by aborting the current transaction/subtransaction: every statement
        on that connection raises `InFailedSqlTransactionError` until a
        ROLLBACK (or ROLLBACK TO SAVEPOINT) clears it. With the real
        `begin_nested()` in place, only the bad fact's own savepoint absorbs
        that abort; without it, the *whole* outer transaction is left
        aborted and the good fact's own `recompute_fact` call fails too.
        """
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
                # A genuine backend error, not a Python-level raise -- see
                # the docstring above for why that distinction is the point.
                await session.execute(text("SELECT 1/0"))
            return await real_recompute(session, fact_id, **kwargs)

        monkeypatch.setattr(vr_module, "recompute_fact", flaky)

        base = _safe_now()
        outcome = await run_recompute(session, now=base)
        await session.commit()

        assert outcome.drain.facts_failed == 1
        assert outcome.drain.facts_recomputed == 1
        assert await _status_of(session, good_fact) == "corroborated"
        assert await _status_of(session, bad_fact) == "candidate"

        # The watermark still advanced past both events -- the poisonous
        # fact's event is not retried by the fast arm forever; the slow arm
        # is what eventually revisits it.
        second = await run_recompute(session, now=base + timedelta(minutes=5))
        await session.commit()
        assert second.drain.events_scanned == 0


class TestLockWaitIsBounded:
    """M-2: a wedged FOR UPDATE must fail the one fact fast, not hang the
    whole tick until max_run_seconds cancels the entire runner coroutine --
    which would roll back everything the tick had done, watermark advance
    included, and make zero progress rather than settling the blocked fact
    alone.

    A genuine cross-connection lock-contention reproduction needs a second,
    really-committed connection holding the row (the isolated `session`
    fixture's writes are invisible to a second connection until this test's
    own transaction ends, so it cannot simulate real contention) -- a real
    engine, real cleanup, and its own watermark seeding, mirroring
    `TestJobWiring`'s discipline. Given M-2 is explicitly "your call" rather
    than a demanded reproduction, this pins the narrower, deterministic
    claim instead: `SET LOCAL lock_timeout` actually executes inside the
    per-fact SAVEPOINT and reverts on that savepoint's *rollback* -- which is
    the PostgreSQL semantics `_set_local_lock_timeout`'s own docstring now
    states precisely (it does NOT revert on a savepoint's successful
    release, only on `ROLLBACK TO SAVEPOINT`; an earlier draft of that
    docstring got this backwards).
    """

    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_lock_timeout_takes_effect_inside_the_savepoint(self, session):
        from app.services.verification_recompute import _LOCK_TIMEOUT_MS, _set_local_lock_timeout

        # Postgres renders SHOW output in the coarsest whole unit ("5s"
        # rather than "5000ms" for an even multiple of 1000), so the
        # expected string is derived the same way rather than hardcoded.
        expected = (
            f"{_LOCK_TIMEOUT_MS // 1000}s"
            if _LOCK_TIMEOUT_MS % 1000 == 0
            else f"{_LOCK_TIMEOUT_MS}ms"
        )

        async with session.begin_nested():
            await _set_local_lock_timeout(session)
            inside = (await session.execute(text("SHOW lock_timeout"))).scalar_one()
            assert inside == expected

    async def test_lock_timeout_reverts_when_its_savepoint_rolls_back(self, session):
        """The rollback path is the one that matters for isolation: a
        poisonous fact's own failed savepoint must not leave the session in
        a state its sibling's savepoint inherits. A successful savepoint
        does NOT revert this setting on its own (PostgreSQL's own semantics,
        not a bug here) -- harmless in this module specifically because
        every fact's savepoint calls `_set_local_lock_timeout` again
        unconditionally, so the effective value for any given fact is always
        that fact's own call, never a stale carry-over.
        """
        from app.services.verification_recompute import _set_local_lock_timeout

        default_timeout = (
            await session.execute(text("SHOW lock_timeout"))
        ).scalar_one()

        with pytest.raises(RuntimeError):
            async with session.begin_nested():
                await _set_local_lock_timeout(session)
                raise RuntimeError("simulated poisonous fact")

        after = (await session.execute(text("SHOW lock_timeout"))).scalar_one()
        assert after == default_timeout

    async def test_a_fact_recomputed_through_the_savepoint_still_promotes(self, session):
        """Negative control: the lock_timeout call must not itself interfere
        with an ordinary, uncontended recompute -- proving the hardening is
        inert in the common case, not just present."""
        fact_id = await _make_fact(session, key="lock-timeout-inert-1")
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await _emit_sources_changed(session, fact_id=fact_id, memory_ref="repo-b")

        outcome = await run_recompute(session, now=_safe_now())
        await session.commit()

        assert outcome.drain.facts_failed == 0
        assert await _status_of(session, fact_id) == "corroborated"


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
