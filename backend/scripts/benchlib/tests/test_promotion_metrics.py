"""T2.51 — the promotion-metrics runner.

Seeds real ladder transitions through the app's own writers
(`KnowledgeTripleRepository`, `FactSourceRepository`,
`verification_ladder.recompute_fact`) exactly the way
`tests/test_ladder_journaling.py` does, then proves `promotion_metrics`'s
SQL over the resulting `events` journal returns hand-computed answers.
Runs against `darkmem_bench` (the `_bench_db` fixture), never
`darkmem_test`/`darkmem_test_N` -- benchlib's own database, per its own
reset discipline.

**Isolation.** `darkmem_bench` is reset once per pytest session (`_bench_db`
is session-scoped, same as every other benchlib test module), so rows from
earlier tests in this file -- and from other test modules in the same run --
persist across tests. Each test brackets itself to a `since`/`until` window
captured from the **database's own clock** (`clock_timestamp()`, on the same
session, immediately before that test's first write) rather than the
process's wall clock: this needs no skew buffer and, because pytest runs
tests strictly sequentially in one worker here, is exact -- a `since`
captured after every prior test committed excludes all of their rows by
construction.
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.usefixtures("_bench_db")

from benchlib import bench_db, promotion_metrics as pm  # noqa: E402

from app.repositories.fact_sources import FactSourceRepository as _FSR  # noqa: E402
from app.repositories.knowledge_triples import KnowledgeTripleRepository  # noqa: E402
from app.services.events import record_event  # noqa: E402
from app.services.verification_ladder import recompute_fact  # noqa: E402

_WINDOW_SLACK = timedelta(hours=1)


async def _db_now(session) -> datetime:
    return (await session.execute(text("SELECT clock_timestamp()"))).scalar()


async def _make_fact(session, *, key: str) -> str:
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=key, subject_name="darkmem", object_name=key, rel_type="USES",
        fact=f"darkmem uses {key}",
        reference_time=datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc),
        project="default",
    )
    await session.commit()
    return row["id"]


async def _add_origin(session, fact_id, origin_key, *, kind="memory") -> None:
    await _FSR(session).add_source(
        fact_id=fact_id, source_kind=kind, source_ref=f"{kind}:{origin_key}",
        origin_key=origin_key,
    )
    await session.commit()


# ───────────────────── promotion rate, both slice axes ─────────────────────


class TestPromotionRateSlices:
    @pytest.mark.asyncio
    async def test_sliced_by_gate_fired_and_by_diversity_with_hand_computed_answers(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            # A: diversity gate, promotes.
            a = await _make_fact(session, key="t2.51-a-diversity-promote")
            await _add_origin(session, a, "sess-a", kind="memory")
            await _add_origin(session, a, "repo-a", kind="code")
            decision_a = await recompute_fact(session, a)
            await session.commit()
            assert decision_a.outcome == "promote"

            # D: diversity gate, met its bar, vetoed -- eligible but not promoted.
            d = await _make_fact(session, key="t2.51-d-diversity-vetoed")
            await _add_origin(session, d, "sess-d", kind="memory")
            await _add_origin(session, d, "repo-d", kind="code")
            decision_d = await recompute_fact(session, d, open_contradiction=True)
            await session.commit()
            assert decision_d.outcome == "dispute"

            # C: no gate (three same-kind origins), promotes -- also
            # homogeneous on the diversity axis (all `memory`).
            c = await _make_fact(session, key="t2.51-c-none-promote")
            for name in ("sess-c1", "sess-c2", "sess-c3"):
                await _add_origin(session, c, name, kind="memory")
            decision_c = await recompute_fact(session, c)
            await session.commit()
            assert decision_c.outcome == "promote"

            # B: below bar, never eligible -- journals nothing.
            b = await _make_fact(session, key="t2.51-b-below-bar")
            await _add_origin(session, b, "sess-b1", kind="memory")
            await _add_origin(session, b, "sess-b2", kind="memory")
            decision_b = await recompute_fact(session, b)
            await session.commit()
            assert decision_b.outcome == "hold"

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        by_gate = {s.bucket: s for s in report.by_gate_fired}
        assert by_gate["diversity"].promoted == 1
        assert by_gate["diversity"].eligible == 2
        assert by_gate["diversity"].rate == pytest.approx(0.5)
        assert by_gate["none"].promoted == 1
        assert by_gate["none"].eligible == 1
        assert by_gate["none"].rate == pytest.approx(1.0)
        # No aggregate substitutes for the slices: both buckets are present
        # and distinct, never collapsed into one combined rate.
        assert set(by_gate) == {"diversity", "none"}

        by_diversity = {s.bucket: s for s in report.by_diversity}
        # A and D asserted under two distinct kinds (memory + code) --
        # "diverse" on the source-kind axis, independent of gate_fired.
        assert by_diversity["diverse"].promoted == 1
        assert by_diversity["diverse"].eligible == 2
        # C asserted under `memory` only across all three origins.
        assert by_diversity["homogeneous"].promoted == 1
        assert by_diversity["homogeneous"].eligible == 1

    @pytest.mark.asyncio
    async def test_below_bar_dispute_and_post_corroboration_dispute_never_enter_a_bucket(self):
        """The two filters that *define* eligibility, proven, not assumed.

        The SQL's WHERE clause carries two conditions beyond `outcome IN
        ('promote', 'dispute')`: `before.verification_status = 'candidate'`
        and `origin_count >= required_n`. Neither is exercised by the
        hand-computed test above, because every fact seeded there either
        never journals (held below bar) or is vetoed only after meeting its
        bar starting from `candidate` -- so both filters hold vacuously and
        deleting either leaves that test green. This test seeds the two
        shapes that actually need each filter:

        - `E` (T2.06's own case, `tests/test_ladder_journaling.py`'s
          `gc-e-early-veto`): vetoed with a single origin, `origin_count (1)
          < required_n (3)`. Journals a `dispute` from `candidate`, so it
          would satisfy `outcome IN ('promote', 'dispute')` and
          `before = 'candidate'` -- only the `origin_count >= required_n`
          filter excludes it.
        - `F`: promotes cleanly (3 same-kind origins, the one real eligible
          transition in this test), then is disputed on a *second* recompute
          -- a `corroborated -> disputed` transition. This second event
          would satisfy `outcome IN ('promote', 'dispute')` and
          `origin_count >= required_n` (still 3 >= 3) -- only the
          `before = 'candidate'` filter excludes it.

        With both filters intact, the `none` gate bucket must show exactly
        F's one promotion: promoted=1, eligible=1. Deleting either filter
        independently inflates `eligible` to 2 while `promoted` stays 1,
        which is exactly the silent denominator drift the filters exist to
        prevent -- proven by mutation below.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            # E: one origin, vetoed immediately -- never reaches its bar.
            e = await _make_fact(session, key="t2.51-e-early-veto")
            await _add_origin(session, e, "sess-e1", kind="memory")
            decision_e = await recompute_fact(session, e, open_contradiction=True)
            await session.commit()
            assert decision_e.outcome == "dispute"
            assert decision_e.origin_count < decision_e.required_n
            assert decision_e.gate_fired == "none"

            # F: three same-kind origins promote cleanly (the one real
            # eligible transition), then a later veto disputes the
            # already-corroborated fact -- before='corroborated', not
            # 'candidate', on this second event.
            f = await _make_fact(session, key="t2.51-f-promote-then-disputed")
            for name in ("sess-f1", "sess-f2", "sess-f3"):
                await _add_origin(session, f, name, kind="memory")
            decision_f1 = await recompute_fact(session, f)
            await session.commit()
            assert decision_f1.outcome == "promote"
            assert decision_f1.gate_fired == "none"

            decision_f2 = await recompute_fact(session, f, open_contradiction=True)
            await session.commit()
            assert decision_f2.outcome == "dispute"
            assert decision_f2.current_status == "corroborated"

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        by_gate = {s.bucket: s for s in report.by_gate_fired}
        assert set(by_gate) == {"none"}, (
            "E's early veto and F's post-corroboration dispute must not "
            "manufacture a bucket of their own"
        )
        assert by_gate["none"].promoted == 1
        assert by_gate["none"].eligible == 1, (
            "only F's promotion is eligible; E (below bar) and F's second "
            "event (before='corroborated', not 'candidate') must both be "
            "excluded"
        )

        by_diversity = {s.bucket: s for s in report.by_diversity}
        assert set(by_diversity) == {"homogeneous"}
        assert by_diversity["homogeneous"].promoted == 1
        assert by_diversity["homogeneous"].eligible == 1

    @pytest.mark.asyncio
    async def test_a_single_observation_slice_is_labelled_under_powered(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            a = await _make_fact(session, key="t2.51-single-obs")
            await _add_origin(session, a, "sess-single-a", kind="memory")
            await _add_origin(session, a, "repo-single-a", kind="code")
            decision = await recompute_fact(session, a)
            await session.commit()
            assert decision.outcome == "promote"

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert len(report.by_gate_fired) == 1
        slice_ = report.by_gate_fired[0]
        assert slice_.eligible == 1
        # 1/1 == 100%, but a single observation must never read as a plain
        # pass -- it must be labelled under-powered like a 0/0 would be.
        assert slice_.rate == pytest.approx(1.0)
        assert slice_.powered is False

    @pytest.mark.asyncio
    async def test_an_empty_window_is_under_powered_not_a_pass_or_zero_percent(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            until = since + timedelta(milliseconds=1)  # a window that can hold nothing
            report = await pm.compute_promotion_metrics(
                session, since=since, until=until, database_identity="test",
            )

        assert report.by_gate_fired == ()
        assert report.by_diversity == ()
        assert report.false_promotion.total_corroborations == 0
        assert report.false_promotion.rate is None
        assert report.false_promotion.powered is False
        assert any("under-powered" in note for note in report.notes)
        rendered = pm.render_report(report)
        assert "UNDER-POWERED" in rendered
        # The rendered false-promotion rate must read "n/a", never a bare
        # percentage or a pass, when there is nothing to divide by.
        assert "false-promotion rate: n/a **UNDER-POWERED**" in rendered
        assert " PASS" not in rendered


# ───────────────────────── the false-promotion audit ─────────────────────────


class TestFalsePromotionAudit:
    @pytest.mark.asyncio
    async def test_recover_then_disputed_fact_is_caught_by_the_corroborated_anchor(self):
        """The exact T2.06 regression case: a fact reaches `corroborated` via
        `recover`, never `promote`, and is later disputed. An audit anchored
        on `outcome = 'promote'` would miss it entirely; anchoring on
        `after.verification_status = 'corroborated'` catches it."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            g = await _make_fact(session, key="t2.51-recover-then-disputed")
            await _add_origin(session, g, "sess-g1", kind="memory")
            first = await recompute_fact(session, g, open_contradiction=True)
            await session.commit()
            assert first.outcome == "dispute"
            assert first.origin_count < first.required_n, (
                "must be vetoed before ever meeting its bar, so no `promote` "
                "event exists for a naive audit to anchor on"
            )

            await _add_origin(session, g, "repo-g1", kind="code")
            recovered = await recompute_fact(session, g, open_contradiction=False)
            await session.commit()
            assert recovered.outcome == "recover"
            assert recovered.target_status == "corroborated"

            redisputed = await recompute_fact(session, g, open_contradiction=True)
            await session.commit()
            assert redisputed.outcome == "dispute"

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert report.false_promotion.total_corroborations == 1
        assert report.false_promotion.disputed_after_corroboration == 1
        assert report.false_promotion.rate == pytest.approx(1.0)

    @pytest.mark.asyncio
    async def test_a_clean_promotion_with_no_later_dispute_is_not_counted(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            c = await _make_fact(session, key="t2.51-clean-promotion")
            for name in ("sess-clean-1", "sess-clean-2", "sess-clean-3"):
                await _add_origin(session, c, name, kind="memory")
            decision = await recompute_fact(session, c)
            await session.commit()
            assert decision.outcome == "promote"

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert report.false_promotion.total_corroborations == 1
        assert report.false_promotion.disputed_after_corroboration == 0
        assert report.false_promotion.rate == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_same_transaction_events_are_ordered_by_the_created_at_id_tuple(self):
        """T2.06's own landmine, re-caught here: within one transaction
        `now()` is constant, so two `verified` events written in the same
        transaction share one `created_at`. A bare `created_at >` comparison
        can never see the second as "later"; the `(created_at, id)` tuple
        compare can, because `id` is a monotonic BIGINT IDENTITY. Both
        `verified` rows are written directly via `record_event` (not
        `recompute_fact`, which commits after each call and would give the
        two rows distinct timestamps on this fast a machine only by luck)
        so they are forced into the same transaction on purpose.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-same-txn-order")

            object_id = _uuid.UUID(fact_id)
            base_payload = {
                "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                "confidence": 0.9,
            }
            await record_event(
                session, event_type="verified", object_type="fact", object_id=object_id,
                project="default",
                payload={
                    **base_payload,
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "promote",
                },
            )
            await record_event(
                session, event_type="verified", object_type="fact", object_id=object_id,
                project="default",
                payload={
                    **base_payload,
                    "before": {"verification_status": "corroborated"},
                    "after": {"verification_status": "disputed"},
                    "outcome": "dispute",
                    "contradiction_blocked": True,
                },
            )
            await session.commit()  # both rows land in the same DB transaction

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert report.false_promotion.total_corroborations == 1
        assert report.false_promotion.disputed_after_corroboration == 1, (
            "the dispute row must be recognised as LATER than the corroboration "
            "row despite sharing one created_at -- this is the tuple-compare "
            "guard; a bare `created_at >` regresses this to 0"
        )


# ───────────────────────── the T2.60 / unknown-vocabulary guard ─────────────────────────


class TestUnrecognisedPayloadGuard:
    @pytest.mark.asyncio
    async def test_an_unrecognised_outcome_raises_rather_than_silently_bucketing(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-unknown-outcome")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "teleport",  # invented, not in KNOWN_OUTCOMES
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "confidence": 0.9,
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="teleport"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_an_invented_supersession_blocked_key_raises_the_t2_60_guard(self):
        """The named landmine: T2.60 has not landed, so no payload carries
        `supersession_blocked` today. This proves the runner does not
        silently absorb it the day it does."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-supersession-blocked")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "corroborated"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "hold",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "supersession_blocked": True,  # invented, not in KNOWN_PAYLOAD_KEYS
                    "confidence": 0.9,
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="supersession_blocked"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_hold_that_is_not_contradiction_blocked_raises(self):
        """Today's code never journals a plain (non-contradiction-blocked)
        hold at all -- only a contradiction-blocked hold journals. Seeing one
        means a new hold reason has started writing (T2.60's shape) and the
        eligibility filter's `outcome IN ('promote', 'dispute')` denominator
        needs to change before it can be trusted."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-bare-hold")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "corroborated"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "hold",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "confidence": 0.9,
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="hold"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_status_change_with_no_outcome_evidence_raises(self):
        """A bare two-key (`before`/`after`) payload is a documented legacy
        shape (`set_verification_status`'s docstring: "every direct/legacy
        caller that only ever wrote a bare status keeps its original
        two-key payload verbatim"). No writer produces it today, but if one
        ever journals a real `candidate -> corroborated` transition this
        way, every eligibility filter in this module's SQL
        (`outcome IN ('promote', 'dispute')`) is blind to it -- the
        promotion would silently vanish from both the numerator and the
        denominator with validation reporting nothing wrong. This is the
        same genus of hazard the T2.60 guard closes for an unrecognised
        key/value; this guard closes it for a recognised-but-absent one.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-bare-status-transition")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                    # no `outcome` and none of the evidence block -- the
                    # exact bare two-key shape the docstring documents.
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="outcome"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_bare_status_no_op_payload_does_not_raise(self):
        """The negative case for the guard above: a bare payload whose
        `before` and `after` agree (a no-op status re-write, or a payload
        with no verification_status keys at all) carries no hidden
        transition and must not be flagged -- only a real, invisible status
        *change* is the hazard."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-bare-status-no-op")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "corroborated"},
                    "after": {"verification_status": "corroborated"},
                },
            )
            await session.commit()

            # Must not raise.
            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )
            assert report.events_validated == 1

    @pytest.mark.asyncio
    async def test_an_unrecognised_review_state_raises_rather_than_silently_dropping(self):
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            c = await _make_fact(session, key="t2.51-unknown-review-state")
            for name in ("sess-rs-1", "sess-rs-2", "sess-rs-3"):
                await _add_origin(session, c, name, kind="memory")
            decision = await recompute_fact(session, c)
            await session.commit()
            assert decision.outcome == "promote"

            await session.execute(
                text(
                    "UPDATE knowledge_triples SET review_state = 'rejected' "
                    "WHERE id = CAST(:id AS uuid)"
                ),
                {"id": c},
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="rejected"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )


# ───────────────────────── report rendering (no DB) ─────────────────────────


class TestRenderReport:
    def test_no_schema_report_reads_as_under_powered_not_a_crash(self):
        since = datetime(2026, 1, 1, tzinfo=timezone.utc)
        until = datetime(2026, 1, 2, tzinfo=timezone.utc)
        report = pm.no_schema_report(since=since, until=until, database_identity="host:5433/darkmem")

        assert report.schema_present is False
        assert report.false_promotion.total_corroborations == 0
        rendered = pm.render_report(report)
        assert "no `events` table" in rendered
        assert "UNDER-POWERED" in rendered
