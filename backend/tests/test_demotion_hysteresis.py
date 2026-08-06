"""T2.46 — demotion hysteresis and the ``under-sourced`` label.

Organised by the Done-when clause each group discharges:

* D1  ``demotion_pending_since`` lands on the schema, and it is a label rather
      than a fifth rung
* D2  the grace window is a ``config`` row
* D3  an under-sourced fact is served **labelled**, not withheld
* D4  regaining a source inside the window cancels the demotion cleanly

Plus the two properties that hold the rest up: the window is counted in
recompute cycles and a cycle is an opportunity for the fact to have recovered
(D5), and the interim state opens the review queue through the registered
derivation rather than through a writer of its own (D6).

Several tests exist to kill a specific mutant and say which one, because the
obvious test passes against a hysteresis that never fires, one that never
ends, and one that leaves a residue behind.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.models.config import Config
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    FactSourceRepository,
)
from app.repositories.knowledge_triples import (
    REVIEW_STATE_OPEN,
    DemotionPending,
    KnowledgeTripleRepository,
)
from app.services import verification_ladder
from app.services.events import record_event
from app.services.review_queue import list_open_facts
from app.services.verification_ladder import (
    DEMOTE_GRACE_CONFIG_KEY,
    DEMOTE_GRACE_DEFAULT,
    DEMOTE_GRACE_MAX,
    DEMOTE_GRACE_VALUE_KEY,
    LadderDecision,
    apply_demotion_hysteresis,
    derive_review_state,
    get_demote_grace_cycles,
    recompute_fact,
)
from app.services.verification_recompute import (
    DEFAULT_SLOW_ARM_INTERVAL_SECONDS,
    run_recompute,
)

# Fixed and absolute, like the sibling ladder suite's: nothing here derives
# from the wall clock, so a fixture cannot rot as the calendar moves past it.
T0 = datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc)
NOW = datetime(2026, 8, 3, 9, 0, 0, tzinfo=timezone.utc)

PROJECT = "hysteresis"


# ───────────────────────────── helpers ─────────────────────────────


async def _make_fact(session, *, key="hys-1", status="corroborated", subject="darkmem"):
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=key,
        subject_name=subject,
        object_name="pgvector",
        rel_type="USES",
        fact=f"{subject} uses pgvector",
        reference_time=T0,
        project=PROJECT,
    )
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    await session.commit()
    return row["id"]


async def _add_origin(session, fact_id, origin_key, *, kind="memory"):
    await FactSourceRepository(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=f"{kind}:{origin_key}",
        origin_key=origin_key,
    )
    await session.commit()


async def _row(session, fact_id) -> dict:
    result = await session.execute(
        text(
            "SELECT verification_status, review_state, confidence, "
            "demotion_pending_since, demotion_pending_cycles "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(result.mappings().one())


async def _verified_events(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )
    return [r[0] for r in result.all()]


async def _emit_sources_changed(session, fact_id) -> None:
    await record_event(
        session,
        event_type="sources_changed",
        object_type="fact",
        object_id=UUID(str(fact_id)),
        project=PROJECT,
        payload={"fact_id": str(fact_id), "memory_id": None},
    )
    await session.commit()


@pytest.fixture
async def _reset_recompute_state(session):
    """The recompute job's bookkeeping row is cross-connection state that
    sibling suites commit for real, so a tick here would otherwise inherit a
    watermark and a slow-arm last-run stamp from whatever ran before it."""
    await session.execute(
        text("DELETE FROM config WHERE key = 'verification_recompute_state'")
    )
    await session.commit()
    yield


async def _set_grace(session, cycles) -> None:
    existing = await session.execute(
        select(Config).where(Config.key == DEMOTE_GRACE_CONFIG_KEY)
    )
    row = existing.scalar_one_or_none()
    value = {DEMOTE_GRACE_VALUE_KEY: cycles}
    if row is None:
        session.add(Config(key=DEMOTE_GRACE_CONFIG_KEY, value=value))
    else:
        row.value = value
    await session.commit()


async def _under_sourced_fact(session, *, key="hys-1", subject="darkmem"):
    """A corroborated fact one grace cycle into a pending demotion.

    One memory origin against ``CORROBORATION_N_DEFAULT`` (3): same kind, one
    instant, so neither the diversity nor the time gate fires and the bar is
    the ungated one.
    """
    fact_id = await _make_fact(session, key=key, subject=subject)
    await _add_origin(session, fact_id, f"{key}-sess-a")
    decision = await recompute_fact(session, fact_id, now=NOW)
    await session.commit()
    assert decision.demotion_pending is True
    return fact_id


def _wire_instant(value):
    """A JSON timestamp as the instant it denotes.

    The app's encoder spells UTC as ``Z`` where ``isoformat`` spells it
    ``+00:00``; comparing instants keeps the assertion about the label rather
    than about the spelling.
    """
    assert value is not None
    return datetime.fromisoformat(value)


def _decision(outcome: str, *, current="corroborated", target="candidate"):
    return LadderDecision(
        fact_id="fact-1",
        current_status=current,
        target_status=target,
        outcome=outcome,  # type: ignore[arg-type]
        origin_count=1,
        required_n=CORROBORATION_N_DEFAULT,
        gate_fired="none",
        source_kinds=("memory",),
        contradiction_blocked=False,
        confidence=0.53,
    )


# ───────── D1 — the column lands, and it is not a fifth rung ─────────


class TestTheSchema:
    async def test_both_hysteresis_columns_exist_with_their_shipped_shapes(
        self, session
    ):
        result = await session.execute(
            text(
                "SELECT column_name, data_type, is_nullable, column_default "
                "FROM information_schema.columns "
                "WHERE table_name = 'knowledge_triples' "
                "AND column_name LIKE 'demotion_pending%' "
                "ORDER BY column_name"
            )
        )
        columns = {row["column_name"]: dict(row) for row in result.mappings().all()}
        assert set(columns) == {"demotion_pending_cycles", "demotion_pending_since"}

        marker = columns["demotion_pending_since"]
        assert marker["data_type"] == "timestamp with time zone"
        # Nullable is the whole mechanism: `IS NOT NULL` is the label and the
        # review-queue predicate at once, so a default would label every fact.
        assert marker["is_nullable"] == "YES"
        assert marker["column_default"] is None

        counter = columns["demotion_pending_cycles"]
        assert counter["data_type"] == "integer"
        assert counter["is_nullable"] == "NO"
        assert counter["column_default"] == "0"

    async def test_a_fresh_fact_is_born_unmarked(self, session):
        fact_id = await _make_fact(session, status=None)
        row = await _row(session, fact_id)
        assert row["demotion_pending_since"] is None
        assert row["demotion_pending_cycles"] == 0

    async def test_the_status_check_still_admits_exactly_four_values(self, session):
        """R1: ``under-sourced`` is an overlay, never a fifth rung.

        The kill target is a future edit that "simplifies" the label by
        widening the CHECK — at which point the overlay becomes a status, doc
        13 §5.3's rendering rule becomes unimplementable, and every consumer
        that switches on the four-value vocabulary silently acquires a fifth
        branch it does not handle.
        """
        clause = (
            await session.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conname = "
                    "'knowledge_triples_verification_status_check'"
                )
            )
        ).scalar_one()
        for rung in ("candidate", "corroborated", "disputed", "confirmed"):
            assert f"'{rung}'" in clause
        assert "under" not in clause

        fact_id = await _make_fact(session, status=None)
        with pytest.raises(IntegrityError):
            async with session.begin_nested():
                await session.execute(
                    text(
                        "UPDATE knowledge_triples SET verification_status = "
                        "'under-sourced' WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": str(fact_id)},
                )

    async def test_the_label_is_never_written_into_review_state(self, session):
        """The queue predicate and its partial index are both ``'open'``.

        A row labelled ``'under-sourced'`` there is a row that has silently
        left the queue, which is exactly what T2.62's derivation forbids.
        """
        fact_id = await _under_sourced_fact(session)
        assert (await _row(session, fact_id))["review_state"] == REVIEW_STATE_OPEN

        with pytest.raises(ValueError, match="invalid review_state"):
            await KnowledgeTripleRepository(session).set_verification_status(
                fact_id, None, confidence=0.5, review_state="under-sourced"
            )


# ───────────────── D2 — the grace window is a config row ─────────────────


class TestTheGraceConfig:
    async def test_an_absent_row_ships_one_cycle(self, session):
        assert await get_demote_grace_cycles(session) == DEMOTE_GRACE_DEFAULT
        assert DEMOTE_GRACE_DEFAULT == 1

    @pytest.mark.parametrize("cycles", [0, 1, 2, 7])
    async def test_a_well_formed_row_is_honoured(self, session, cycles):
        await _set_grace(session, cycles)
        assert await get_demote_grace_cycles(session) == cycles

    @pytest.mark.parametrize("bad", ["2", 2.5, None, True, [2]])
    async def test_a_malformed_value_degrades_to_the_default(self, session, bad):
        """Degrade, never raise: the row is operator-edited with no schema in
        front of it, and a bad value must not take the recompute down.

        ``True`` is in the list because ``bool`` is an ``int`` subclass and
        would otherwise read as one cycle — the default by accident, which is
        indistinguishable from the default on purpose in every log.
        """
        await _set_grace(session, bad)
        assert await get_demote_grace_cycles(session) == DEMOTE_GRACE_DEFAULT

    async def test_a_negative_value_becomes_no_hysteresis_not_never(self, session):
        await _set_grace(session, -5)
        assert await get_demote_grace_cycles(session) == 0

    async def test_an_absurd_value_is_clamped_to_the_ceiling(self, session):
        await _set_grace(session, DEMOTE_GRACE_MAX * 1000)
        assert await get_demote_grace_cycles(session) == DEMOTE_GRACE_MAX

    async def test_an_unrelated_row_shape_falls_back(self, session):
        session.add(Config(key=DEMOTE_GRACE_CONFIG_KEY, value={"grace": 9}))
        await session.commit()
        assert await get_demote_grace_cycles(session) == DEMOTE_GRACE_DEFAULT


# ─────────── D5 — the window, as a pure function of its inputs ───────────


class TestTheHysteresisFunction:
    """No session, no clock of its own — the same discipline ``decide`` keeps."""

    def test_it_opens_the_window_on_the_first_demote(self):
        outcome = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=None,
            pending_cycles=0,
            grace_cycles=1,
            now=NOW,
        )
        assert outcome.decision.outcome == "hold"
        assert outcome.decision.target_status == "corroborated"
        assert outcome.decision.demotion_pending is True
        assert outcome.marker == DemotionPending(since=NOW, cycles=1)

    def test_it_demotes_once_the_window_closes(self):
        outcome = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=T0,
            pending_cycles=1,
            grace_cycles=1,
            now=NOW,
        )
        assert outcome.decision.outcome == "demote"
        assert outcome.decision.target_status == "candidate"
        assert outcome.decision.demotion_pending is False
        assert outcome.marker == DemotionPending(since=None, cycles=0)

    def test_a_wider_window_holds_for_every_one_of_its_cycles(self):
        pending_since, cycles = None, 0
        for expected in (1, 2, 3):
            outcome = apply_demotion_hysteresis(
                _decision("demote"),
                pending_since=pending_since,
                pending_cycles=cycles,
                grace_cycles=3,
                now=NOW,
            )
            assert outcome.decision.outcome == "hold"
            assert outcome.marker is not None
            assert outcome.marker.cycles == expected
            pending_since, cycles = outcome.marker.since, outcome.marker.cycles

        closing = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=pending_since,
            pending_cycles=cycles,
            grace_cycles=3,
            now=NOW,
        )
        assert closing.decision.outcome == "demote"

    def test_the_open_instant_is_not_re_stamped(self):
        """Kill target: a hysteresis that refreshes ``since`` every cycle.

        It would demote at the same moment either way, so no behavioural test
        catches it — but an under-sourced row would report itself as freshly
        under-sourced however long it had been held, which is the one thing a
        human triaging the queue reads the marker for.
        """
        outcome = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=T0,
            pending_cycles=1,
            grace_cycles=5,
            now=NOW,
        )
        assert outcome.marker is not None
        assert outcome.marker.since == T0

    def test_zero_grace_demotes_immediately_and_marks_nothing(self):
        outcome = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=None,
            pending_cycles=0,
            grace_cycles=0,
            now=NOW,
        )
        assert outcome.decision.outcome == "demote"
        assert outcome.marker is None

    def test_turning_the_knob_off_drains_a_window_it_had_already_opened(self):
        outcome = apply_demotion_hysteresis(
            _decision("demote"),
            pending_since=T0,
            pending_cycles=1,
            grace_cycles=0,
            now=NOW,
        )
        assert outcome.decision.outcome == "demote"
        assert outcome.marker == DemotionPending(since=None, cycles=0)

    @pytest.mark.parametrize(
        ("outcome_name", "current", "target"),
        [
            ("hold", "corroborated", "corroborated"),
            ("promote", "candidate", "corroborated"),
            ("dispute", "corroborated", "disputed"),
            ("recover", "disputed", "corroborated"),
        ],
    )
    def test_every_non_demotion_cancels(self, outcome_name, current, target):
        outcome = apply_demotion_hysteresis(
            _decision(outcome_name, current=current, target=target),
            pending_since=T0,
            pending_cycles=1,
            grace_cycles=3,
            now=NOW,
        )
        assert outcome.decision.demotion_pending is False
        assert outcome.marker == DemotionPending(since=None, cycles=0)

    def test_an_unmarked_fact_on_a_non_demotion_writes_nothing(self):
        """``None`` marker means *leave the columns alone*, which is not the
        same value as the clear — otherwise every ordinary recompute of every
        ordinary fact writes two columns it has no opinion about."""
        outcome = apply_demotion_hysteresis(
            _decision("hold", current="candidate", target="candidate"),
            pending_since=None,
            pending_cycles=0,
            grace_cycles=1,
            now=NOW,
        )
        assert outcome.marker is None

    def test_the_marker_type_refuses_an_incoherent_pair(self):
        with pytest.raises(ValueError):
            DemotionPending(since=None, cycles=2)
        with pytest.raises(ValueError):
            DemotionPending(since=NOW, cycles=0)
        with pytest.raises(ValueError):
            DemotionPending(since=NOW, cycles=-1)


# ────────────── the window, applied end to end ──────────────


class TestTheAppliedWindow:
    async def test_the_first_cycle_labels_and_does_not_demote(self, session):
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "hold"
        assert decision.demotion_pending is True
        row = await _row(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["demotion_pending_since"] == NOW
        assert row["demotion_pending_cycles"] == 1

    async def test_the_second_cycle_demotes_and_clears_the_marker(self, session):
        fact_id = await _under_sourced_fact(session)

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "demote"
        row = await _row(session, fact_id)
        assert row["verification_status"] == "candidate"
        assert row["demotion_pending_since"] is None
        assert row["demotion_pending_cycles"] == 0

    async def test_a_widened_window_really_holds_longer(self, session):
        """Kill target: a grace read but ignored.

        A hysteresis hard-coded at one cycle passes every test above. It fails
        here, because the third cycle would already have demoted.
        """
        await _set_grace(session, 3)
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")

        for expected_cycles in (1, 2, 3):
            decision = await recompute_fact(session, fact_id, now=NOW)
            await session.commit()
            assert decision.outcome == "hold"
            row = await _row(session, fact_id)
            assert row["verification_status"] == "corroborated"
            assert row["demotion_pending_cycles"] == expected_cycles

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        assert decision.outcome == "demote"
        assert (await _row(session, fact_id))["verification_status"] == "candidate"

    async def test_zero_grace_restores_the_pre_hysteresis_behaviour(self, session):
        await _set_grace(session, 0)
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "demote"
        row = await _row(session, fact_id)
        assert row["verification_status"] == "candidate"
        assert row["demotion_pending_since"] is None

    async def test_confidence_falls_on_the_cycle_the_source_is_lost(self, session):
        """The rung is held; the support estimate is not.

        The badge's claim is "asserted by K distinct origins", and K really
        did fall. Holding the confidence back too would make the held rung
        look supported rather than merely un-demoted.
        """
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        corroborated = (await _row(session, fact_id))["confidence"]

        await session.execute(
            text(
                "DELETE FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
                "AND source_kind = 'code'"
            ),
            {"id": str(fact_id)},
        )
        await session.commit()
        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.demotion_pending is True
        row = await _row(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["confidence"] < corroborated

    async def test_the_hold_journals_nothing(self, session):
        """Entering and holding the state move no rung.

        A ``verified`` row here would be counted by G-C's promotion-rate SQL
        as a transition that did not happen, and ``benchlib.promotion_metrics``
        refuses an unexplained ``hold`` outright.
        """
        await _set_grace(session, 2)
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")
        # The fixture's own seeding write journals a candidate -> corroborated
        # row, so the claim below is about rows added from here on.
        seeded = len(await _verified_events(session, fact_id))

        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        assert len(await _verified_events(session, fact_id)) == seeded

        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        events = await _verified_events(session, fact_id)
        assert len(events) == seeded + 1
        assert events[-1]["outcome"] == "demote"
        assert events[-1]["before"] == {"verification_status": "corroborated"}
        assert events[-1]["after"] == {"verification_status": "candidate"}

    async def test_a_candidate_below_its_bar_is_never_under_sourced(self, session):
        """There is no rung left for the window to protect, so no label."""
        fact_id = await _make_fact(session, status="candidate")
        await _add_origin(session, fact_id, "sess-a")

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "hold"
        assert decision.demotion_pending is False
        assert (await _row(session, fact_id))["demotion_pending_since"] is None

    async def test_a_confirmed_fact_is_never_under_sourced(self, session):
        """Doc 08 §4.4: the machine never moves a ratified fact, in either
        direction, so it can never enter the window either."""
        fact_id = await _make_fact(session, status=None)
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'confirmed' "
                "WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(fact_id)},
        )
        await session.commit()

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.demotion_pending is False
        assert (await _row(session, fact_id))["demotion_pending_since"] is None

    async def test_the_veto_pre_empts_the_window(self, session):
        """A contradicted fact has already lost the rung the window protects.

        Carrying the marker across would resume a count towards a demotion
        from a status the fact no longer holds.
        """
        fact_id = await _under_sourced_fact(session)

        decision = await recompute_fact(
            session, fact_id, open_contradiction=True, now=NOW
        )
        await session.commit()

        assert decision.outcome == "dispute"
        row = await _row(session, fact_id)
        assert row["verification_status"] == "disputed"
        assert row["demotion_pending_since"] is None
        assert row["demotion_pending_cycles"] == 0
        # Still queued — by the veto's opener now, not the hysteresis'.
        assert row["review_state"] == REVIEW_STATE_OPEN


# ───────── D4 — regaining a source cancels the demotion cleanly ─────────


class TestCancellation:
    async def test_regaining_a_source_clears_the_marker(self, session):
        fact_id = await _under_sourced_fact(session)

        # A second origin of a different kind fires the diversity gate, so
        # the bar drops to 2 and the fact meets it again.
        await _add_origin(session, fact_id, "repo-b", kind="code")
        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "hold"
        assert decision.demotion_pending is False
        row = await _row(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["demotion_pending_since"] is None
        assert row["demotion_pending_cycles"] == 0
        assert row["review_state"] is None

    async def test_the_cancellation_leaves_nothing_that_demotes_later(self, session):
        """The clause's real content, and the one a partial clear fails.

        Two kill targets, and both are invisible to the test above — after
        either one the fact is corroborated, unmarked and unqueued:

        * a cancellation that does not write the clear at all, so the next dip
          inherits a spent window and demotes on its *first* cycle instead of
          being held;
        * a clear that moves only one of the two columns, so the counter the
          next window is measured against is not the one the marker implies.

        Both show up only in the next dip's behaviour, never in the state
        right after the clear — which is why the test dips a second time.

        Note the residue the reader expects first — marker cleared, counter
        left behind — is *not* one of them: the open branch keys on
        ``pending_since is None`` alone and rewrites ``cycles=1``
        unconditionally, so that shape is self-healing and unreachable.
        """
        fact_id = await _under_sourced_fact(session)
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        # Dip again: withdraw the origin that restored it.
        await session.execute(
            text(
                "DELETE FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
                "AND source_kind = 'code'"
            ),
            {"id": str(fact_id)},
        )
        await session.commit()

        decision = await recompute_fact(session, fact_id, now=NOW)
        await session.commit()

        assert decision.outcome == "hold", (
            "the second dip got a shorter window than the first, so the "
            "cancellation left a residue behind"
        )
        row = await _row(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["demotion_pending_cycles"] == 1

    async def test_a_flapping_source_never_moves_the_rung(self, session):
        """Doc 08 §4.3's motivating case, end to end.

        Ten lose/regain rounds, each fully inside the window: the rung never
        moves and the journal stays empty, so the badge never flaps.
        """
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        await recompute_fact(session, fact_id, now=NOW)
        await session.commit()
        baseline = len(await _verified_events(session, fact_id))

        for round_no in range(10):
            await session.execute(
                text(
                    "DELETE FROM fact_sources WHERE fact_id = CAST(:id AS uuid) "
                    "AND source_kind = 'code'"
                ),
                {"id": str(fact_id)},
            )
            await session.commit()
            await recompute_fact(session, fact_id, now=NOW)
            await session.commit()

            await _add_origin(session, fact_id, f"repo-b-{round_no}", kind="code")
            await recompute_fact(session, fact_id, now=NOW)
            await session.commit()

            assert (await _row(session, fact_id))["verification_status"] == (
                "corroborated"
            )

        assert len(await _verified_events(session, fact_id)) == baseline


# ───────── D3 — served labelled, never withheld ─────────


class TestServedLabelled:
    """Doc 08 §6 / invariant 14, proved against the fact read paths rather
    than against the column.

    A test that only checks the column moved asserts nothing about honesty:
    it passes just as happily against a read path that filters under-sourced
    facts out entirely, which is precisely the failure "served labelled, not
    withheld" names.
    """

    async def test_get_live_still_returns_it_and_carries_the_label(self, session):
        fact_id = await _under_sourced_fact(session)

        rows = await KnowledgeTripleRepository(session).get_live(
            project=PROJECT, triple_key="hys-1"
        )

        assert [row["id"] for row in rows] == [fact_id]
        assert rows[0]["verification_status"] == "corroborated"
        assert rows[0]["demotion_pending_since"] == NOW

    async def test_it_is_listed_beside_an_unaffected_fact_not_instead_of_it(
        self, session
    ):
        """Membership, not merely presence: the under-sourced fact and a
        healthy one are both served, in one call, unfiltered."""
        healthy = await _make_fact(session, key="hys-healthy", subject="healthy")
        await _add_origin(session, healthy, "h-sess-a")
        await _add_origin(session, healthy, "h-repo-b", kind="code")
        await recompute_fact(session, healthy, now=NOW)
        await session.commit()

        under = await _under_sourced_fact(session, key="hys-under", subject="under")

        rows, total = await KnowledgeTripleRepository(session).list_live(
            project=PROJECT
        )
        served = {row["id"]: row for row in rows}

        assert total == 2
        assert {healthy, under} <= set(served)
        assert served[healthy]["demotion_pending_since"] is None
        assert served[under]["demotion_pending_since"] == NOW
        # And the label did not cost it its rung on the way out.
        assert served[under]["verification_status"] == "corroborated"

    async def test_the_historical_read_carries_it_too(self, session):
        fact_id = await _under_sourced_fact(session)
        rows = await KnowledgeTripleRepository(session).as_of(
            T0 + timedelta(days=1), project=PROJECT, triple_key="hys-1"
        )
        assert [row["id"] for row in rows] == [fact_id]
        assert rows[0]["demotion_pending_since"] == NOW

    async def test_the_detail_read_carries_it_too(self, session):
        fact_id = await _under_sourced_fact(session)
        row = await KnowledgeTripleRepository(session).get(fact_id)
        assert row is not None
        assert row["demotion_pending_since"] == NOW

    async def test_the_rest_facts_list_renders_the_label(
        self, session, client, auth_headers, cleared_promotion_record):
        """Renderable, not merely stored.

        ``_base_item`` hand-enumerates the wire item and ``FactListItem``
        gates what survives serialisation, so a marker that reaches
        ``_COLUMNS`` still stops at either of them. Doc 13 §5.3's overlay
        renders on this tab; reaching it by elimination
        (``corroborated`` + ``review_state='open'``) is not the same guarantee,
        because a second queue opener makes that inference wrong.
        """
        healthy = await _make_fact(session, key="hys-healthy", subject="healthy")
        await _add_origin(session, healthy, "h-sess-a")
        await _add_origin(session, healthy, "h-repo-b", kind="code")
        await recompute_fact(session, healthy, now=NOW)
        await session.commit()

        under = await _under_sourced_fact(session, key="hys-under", subject="under")

        response = await client.get(
            f"/api/v1/knowledge/facts?project={PROJECT}", headers=auth_headers
        )

        assert response.status_code == 200
        served = {item["id"]: item for item in response.json()["items"]}
        assert {healthy, under} <= set(served)
        assert _wire_instant(served[under]["demotion_pending_since"]) == NOW
        assert served[under]["verification_status"] == "corroborated"
        assert served[healthy]["demotion_pending_since"] is None

    async def test_the_rest_facts_detail_renders_the_label(
        self, session, client, auth_headers
    ):
        fact_id = await _under_sourced_fact(session)

        response = await client.get(
            f"/api/v1/knowledge/facts/{fact_id}", headers=auth_headers
        )

        assert response.status_code == 200
        assert _wire_instant(response.json()["demotion_pending_since"]) == NOW

    async def test_the_review_queue_names_the_reason(
        self, session, cleared_promotion_record
    ):
        """R3: T2.46 supplies the distinguishing column ``review_queue``'s
        docstring said did not exist yet, so this row stops reporting
        ``unspecified``.

        The gate is opened because the assertion is about the rung an
        under-sourced fact still holds, not about T2.95's suppression of it —
        which ``tests/test_claim_serving_gates.py`` drives at this same door
        unfixtured.
        """
        fact_id = await _under_sourced_fact(session)

        items, total = await list_open_facts(session, project=PROJECT)

        assert total == 1
        assert items[0]["id"] == fact_id
        assert items[0]["reason"] == "under-sourced"
        assert items[0]["verification_status"] == "corroborated"
        assert items[0]["demotion_pending_since"] == NOW

    async def test_a_disputed_fact_still_names_the_graver_reason(self, session):
        fact_id = await _make_fact(session, status="disputed")
        items, _ = await list_open_facts(session, project=PROJECT)
        assert items == [] or items[0]["id"] != fact_id  # not queued until derived

        await KnowledgeTripleRepository(session).set_verification_status(
            fact_id, "disputed", confidence=0.4, review_state=REVIEW_STATE_OPEN
        )
        await session.commit()

        items, _ = await list_open_facts(session, project=PROJECT)
        assert [item["reason"] for item in items] == ["disputed"]


# ───────── D6 — the queue flag is derived, not written ─────────


class TestTheReviewStateDerivation:
    def test_the_hysteresis_is_a_registered_opener(self):
        """It must not be plumbed past ``REVIEW_OPENERS``.

        Registering is what makes the condition both able to open the queue
        and *required* to keep it open — ``derive_review_state`` clears on the
        absence of every member, so an opener written as a direct column write
        would be cleared by the next recompute of any other opener.
        """
        assert len(verification_ladder.REVIEW_OPENERS) == 2
        pending = replace(
            _decision("hold", target="corroborated"), demotion_pending=True
        )
        assert derive_review_state(pending) == REVIEW_STATE_OPEN

    def test_a_plain_corroborated_hold_is_not_queued(self):
        assert derive_review_state(_decision("hold", target="corroborated")) is None

    def test_the_closing_cycle_leaves_the_queue(self):
        """The demotion is what the human was queued about, and it happened.

        Nothing was silently resolved: the transition journals, and a plain
        ``candidate`` is a rung rather than a condition needing adjudication.
        """
        assert derive_review_state(_decision("demote")) is None

    async def test_the_flag_opens_and_clears_with_the_window(self, session):
        fact_id = await _under_sourced_fact(session)
        assert (await _row(session, fact_id))["review_state"] == REVIEW_STATE_OPEN

        await recompute_fact(session, fact_id, now=NOW)  # closes the window
        await session.commit()
        assert (await _row(session, fact_id))["review_state"] is None


# ───────── D5 — a cycle is an opportunity to recover, not a call ─────────


class TestOneCyclePerTick:
    pytestmark = pytest.mark.usefixtures("_reset_recompute_state")

    async def test_both_arms_in_one_tick_burn_only_one_cycle(self, session):
        """Kill target: the slow arm re-recomputing what the fast arm just did.

        Both looks share one session and one transaction, so the second reads
        exactly what the first wrote and cannot observe a recovery. Counting
        it would collapse the shipped one-cycle window into the tick that
        opened it — the hysteresis silently not applying, on precisely the
        ticks the slow arm is due.
        """
        fact_id = await _make_fact(session, key="hys-tick")
        await _add_origin(session, fact_id, "tick-sess-a")
        await _emit_sources_changed(session, fact_id)

        outcome = await run_recompute(session, now=datetime.now(timezone.utc) + timedelta(seconds=30))
        await session.commit()

        assert outcome.slow_arm_ran is True
        assert outcome.drain.facts_recomputed == 1
        assert outcome.reconcile.facts_skipped_fresh == 1
        row = await _row(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["demotion_pending_cycles"] == 1

    async def test_the_next_tick_closes_it(self, session):
        fact_id = await _make_fact(session, key="hys-tick-2")
        await _add_origin(session, fact_id, "tick2-sess-a")
        await _emit_sources_changed(session, fact_id)

        base = datetime.now(timezone.utc) + timedelta(seconds=30)
        await run_recompute(session, now=base)
        await session.commit()
        await run_recompute(
            session, now=base + timedelta(seconds=DEFAULT_SLOW_ARM_INTERVAL_SECONDS)
        )
        await session.commit()

        assert (await _row(session, fact_id))["verification_status"] == "candidate"


