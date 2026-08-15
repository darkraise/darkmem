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

import dataclasses
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


async def _real_dispute(session, *, tag: str) -> tuple[str, str]:
    """A fact and a genuine counterpart, adjudicated by the real scan.

    Every other seeding helper here either hand-writes a payload or passes
    `open_contradiction=True`, which *overrides* the adjudication -- no scan
    runs, so no finding exists and no counterpart block is written. Only a real
    inverse-replacement pair produces the payload shape T2.64 emits, which is
    the shape this runner's vocabulary has to already know.

    The names are tagged per test because `darkmem_bench` is reset once per
    session, not per test: an untagged pair would be found by a later test's
    scan as well as its own.
    """
    repo = KnowledgeTripleRepository(session)
    ids = []
    for subject, obj in ((f"{tag}-alpha", f"{tag}-beta"), (f"{tag}-beta", f"{tag}-alpha")):
        row = await repo.insert_open(
            triple_key=f"{tag}-{subject}", subject_name=subject, object_name=obj,
            rel_type="REPLACES", fact=f"{subject} replaces {obj}",
            reference_time=datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc),
            project="default",
        )
        ids.append(row["id"])
    await session.commit()
    subject_id, counterpart_id = ids
    await _add_origin(session, subject_id, f"{tag}-sess", kind="memory")
    await _add_origin(session, subject_id, f"{tag}-repo", kind="code")
    await _add_origin(session, counterpart_id, f"{tag}-witness", kind="memory")
    return subject_id, counterpart_id


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
        # percentage or a pass, when there is nothing to divide by. The label
        # gained "(point estimate)" with T2.130, which prints an upper
        # confidence bound beside it — the distinction this line now carries is
        # the reason for the qualifier, and the pinned behaviour is unchanged.
        assert "false-promotion rate (point estimate): n/a **UNDER-POWERED**" in rendered
        assert " PASS" not in rendered
        # An empty window has no bound either: the power block renders nothing
        # rather than a spurious 0.0000 upper bound on no observations.
        assert "upper confidence bound" not in rendered


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
    async def test_a_corroborated_fact_later_expired_is_reported_as_r2s_companion(self):
        """`promotion_bars` R2: the audit may not be quoted without this count.

        A fold retires one of two rows, so a later dispute can land on an id
        carrying no corroboration event and the audit's join never sees it.
        The companion is what caps a zero rate, so a corroborated fact that
        was later expired must be visible and one that was not must not
        inflate it.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            folded = await _make_fact(session, key="t2.108-r2-folded")
            for name in ("sess-fold-1", "sess-fold-2", "sess-fold-3"):
                await _add_origin(session, folded, name, kind="memory")
            assert (await recompute_fact(session, folded)).outcome == "promote"
            await session.commit()

            kept = await _make_fact(session, key="t2.108-r2-kept")
            for name in ("sess-kept-1", "sess-kept-2", "sess-kept-3"):
                await _add_origin(session, kept, name, kind="memory")
            assert (await recompute_fact(session, kept)).outcome == "promote"
            await session.commit()

            await KnowledgeTripleRepository(session).expire(folded)
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert report.false_promotion.total_corroborations == 2
        assert report.false_promotion.expired_after_corroboration == 1
        assert "R2 companion" in pm.render_report(report)
        assert (
            pm.to_ledger_row(report)["false_promotion"]["expired_after_corroboration"] == 1
        )

    @pytest.mark.asyncio
    async def test_an_expiry_before_its_corroboration_is_not_an_r2_fold(self):
        """The companion counts expiry *after* corroboration, like the dispute arm.

        Without the ordering compare every expired fact that was ever
        corroborated would count, and the cap would stop meaning what R2 says
        it means.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)

            fact = await _make_fact(session, key="t2.108-r2-expired-first")
            await KnowledgeTripleRepository(session).expire(fact)
            await session.commit()

            for name in ("sess-order-1", "sess-order-2", "sess-order-3"):
                await _add_origin(session, fact, name, kind="memory")
            assert (await recompute_fact(session, fact)).outcome == "promote"
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        assert report.false_promotion.total_corroborations == 1
        assert report.false_promotion.expired_after_corroboration == 0

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
    async def test_a_supersession_blocked_hold_is_counted_not_refused(self):
        """**T2.60 has now landed**, so this tripwire's job has changed.

        It was written to prove the runner would not silently absorb the
        flag the day it appeared, and it fired exactly as designed. Now the
        flag is legitimate, and what must be proven is the other half of the
        same ruling: a blocked hold is a fact that MET its bar and did not
        promote, so it belongs in the denominator. If it were merely accepted
        and dropped, a widening block would raise the reported rate by
        shrinking the denominator -- the silent inflation the T2.06 ruling
        minted the flag to prevent.

        The guard against genuinely unknown keys is unchanged and still
        proven by `test_an_unknown_payload_key_raises`."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-supersession-blocked")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    # `candidate`, not `corroborated`: T2.60 reports the flag
                    # only when the decision actually WITHHELD a promotion, so
                    # an already-corroborated fact carrying the signal is not
                    # flagged -- counting it would inflate the blocked count
                    # with facts that were never going to promote.
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "candidate"},
                    "outcome": "hold",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "supersession_blocked": True,
                    "confidence": 0.9,
                },
            )
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )
            buckets = {s.bucket: s for s in report.by_gate_fired}
            assert "diversity" in buckets, "the blocked hold never reached a slice"
            assert buckets["diversity"].supersession_blocked == 1
            # In the denominator, not the numerator: it met its bar and was
            # withheld, so it counts as eligible and not as a promotion.
            assert buckets["diversity"].eligible >= 1
            assert buckets["diversity"].promoted == 0

    @pytest.mark.asyncio
    async def test_an_unknown_payload_key_raises(self):
        """The guard the class above has always cited and never exercised.

        `KNOWN_PAYLOAD_KEYS` is the reason a new field cannot be silently
        mis-bucketed, and until now nothing proved it rejected anything: every
        test here seeded a key the set already knew.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.51-unknown-key")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "promote",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "confidence": 0.9,
                    "hysteresis_cycles": 2,  # invented, not in KNOWN_PAYLOAD_KEYS
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="hysteresis_cycles"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_real_counterpart_block_is_accepted_and_changes_no_number(self):
        """T2.64's payload, produced by the ladder rather than hand-written.

        Two halves, and both matter. The runner must **accept** it -- an
        unwidened vocabulary turns every G-C measurement into a hard failure
        the day the ladder starts emitting -- and it must **not** re-bucket
        anything on its account: the counterpart explains a decision that
        `outcome` and `contradiction_blocked` already describe in full, so a
        vetoed-after-meeting-its-bar fact lands in the denominator exactly
        where it did before the block existed.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            subject, counterpart = await _real_dispute(session, tag="t2.64-accepted")

            decision = await recompute_fact(session, subject)
            await session.commit()
            assert decision.outcome == "dispute"
            assert decision.origin_count >= decision.required_n
            assert decision.gate_fired == "diversity"

            payload = (
                await session.execute(
                    text(
                        "SELECT payload FROM events WHERE event_type = 'verified' "
                        "AND object_id = CAST(:id AS uuid) ORDER BY created_at DESC, id DESC"
                    ),
                    {"id": subject},
                )
            ).scalar()
            assert payload["contradiction"]["counterpart_id"] == counterpart

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )

        buckets = {s.bucket: s for s in report.by_gate_fired}
        assert buckets["diversity"].eligible == 1
        assert buckets["diversity"].promoted == 0

    @pytest.mark.asyncio
    async def test_an_unrecognised_contradiction_key_raises(self):
        """The nested block gets the same closed vocabulary as the top level.

        Without this, a field added inside the block would pass the runner
        untouched -- the silent widening `KNOWN_PAYLOAD_KEYS` exists to make
        impossible one level up.
        """
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.64-unknown-inner-key")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "disputed"},
                    "outcome": "dispute",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": True,
                    "confidence": 0.9,
                    "contradiction": {
                        "counterpart_id": str(_uuid.uuid4()),
                        "enumeration": "first_finding",
                        "counterpart_confidence": 0.4,  # invented
                    },
                },
            )
            await session.commit()

            with pytest.raises(
                pm.UnrecognisedPayloadError, match="counterpart_confidence"
            ):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_an_unknown_enumeration_raises(self):
        """`enumeration` states how many contradictions the block names. A
        reader that took `first_finding`'s meaning for a value that no longer
        means it would report one counterpart as if it were all of them."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.64-unknown-enumeration")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "disputed"},
                    "outcome": "dispute",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": True,
                    "confidence": 0.9,
                    "contradiction": {
                        "counterpart_id": str(_uuid.uuid4()),
                        "enumeration": "all_findings",
                    },
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="all_findings"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_counterpart_on_a_row_whose_veto_never_fired_raises(self):
        """The block is written only by the verdict that fired the veto, so it
        beside `contradiction_blocked: false` means a second writer or a block
        copied onto a decision it does not describe -- either way, a live
        dispute's evidence attached to a fact nothing is disputing."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.64-unblocked-counterpart")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "corroborated"},
                    "outcome": "promote",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "confidence": 0.9,
                    "contradiction": {
                        "counterpart_id": str(_uuid.uuid4()),
                        "enumeration": "first_finding",
                    },
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="did not happen"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_a_contradiction_block_with_no_counterpart_id_raises(self):
        """A block that names no fact is worse than no block: it reads as
        "both sides are recorded" while carrying only one."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.64-anonymous-counterpart")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "disputed"},
                    "outcome": "dispute",
                    "origin_count": 2, "required_n": 2, "gate_fired": "diversity",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": True,
                    "confidence": 0.9,
                    "contradiction": {
                        "counterpart_id": None,
                        "enumeration": "first_finding",
                    },
                },
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="counterpart_id"):
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
    async def test_an_unrecognised_human_verdict_raises_rather_than_counting_past(self):
        """**Retargeted by T2.63.** This test used to plant an unrecognised
        `review_state` and assert the runner raised. That guard is retired:
        T2.62 makes `review_state` pure queue membership, so it could never
        carry a verdict, and the arm it guarded read 0 forever while its own
        tripwire could not fire -- the vocabulary it watched was correct.

        The verdict now lives in the journal, so the same discipline applies
        one layer over: `record_human_verdict` refuses anything outside the
        closed set, and a value reaching the audit anyway means a second
        writer bypassed the emitter. The audit must not count past a verdict
        it cannot classify."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.63-unknown-verdict")
            await record_event(
                session, event_type="human_verdict", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={"verdict": "vetoed", "verification_status": "corroborated"},
            )
            await session.commit()

            with pytest.raises(pm.UnrecognisedPayloadError, match="vetoed"):
                await pm.compute_promotion_metrics(
                    session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
                )

    @pytest.mark.asyncio
    async def test_the_blocked_hold_reaches_both_slices_and_both_outputs(self):
        """The by-diversity slice's widened denominator was decorative: the
        earlier test only exercised by-gate, so dropping the OR-branch from
        the diversity query left the whole suite green. Both G-C slices must
        admit the blocked hold, and both durable outputs — the rendered
        report and the ledger row — must carry the count, because those are
        what a gate run actually reads. A number that exists only on the
        in-memory dataclass cannot tell a reader whether a low rate came from
        blocking or from starvation."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            fact_id = await _make_fact(session, key="t2.60-both-slices")
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(fact_id), project="default",
                payload={
                    "before": {"verification_status": "candidate"},
                    "after": {"verification_status": "candidate"},
                    "outcome": "hold",
                    "origin_count": 2, "required_n": 2, "gate_fired": "time_gap",
                    "source_kinds": ["memory", "code"], "contradiction_blocked": False,
                    "supersession_blocked": True, "confidence": 0.8,
                },
            )
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )
            by_gate = {s.bucket: s for s in report.by_gate_fired}
            by_div = {s.bucket: s for s in report.by_diversity}
            assert by_gate["time_gap"].supersession_blocked == 1
            assert by_div["diverse"].supersession_blocked == 1, (
                "the by-diversity slice must admit the blocked hold too"
            )
            assert by_div["diverse"].eligible >= 1

            rendered = pm.render_report(report)
            # Assert a rendered ROW carrying the value, not the substring
            # "blocked" -- the header alone satisfies that, so dropping the
            # value from every row while keeping the column heading would
            # have passed.
            assert any(
                line.startswith("| time_gap |") and line.count("|") == 6
                and line.split("|")[3].strip() == "1"
                for line in rendered.splitlines()
            ), f"the rendered row must carry the blocked value:\n{rendered}"
            row = pm.to_ledger_row(report)
            # BOTH ledger slices, not just one: asserting through
            # by_diversity alone left by_gate_fired's field unguarded.
            assert any(
                s["supersession_blocked"] == 1 for s in row["by_diversity"]
            ), "the by_diversity ledger row must carry the count"
            assert any(
                s["supersession_blocked"] == 1 for s in row["by_gate_fired"]
            ), "the by_gate_fired ledger row must carry the count"

    @pytest.mark.asyncio
    async def test_one_fact_disputed_and_rejected_counts_once_not_twice(self):
        """doc 17 §5.1 counts **facts**, not arm-hits, and the overlap is the
        primary flow rather than an edge case: the queue serves the human
        disputed facts, so the ones they reject are in both arms by
        construction.

        While the human-rejected arm was structurally 0 the audit summed the
        two arms on a comment asserting they could not overlap. T2.63 made
        that false, and one fact taken corroborated -> disputed ->
        human-rejected scored 2 — a 200% false-promotion rate off a single
        fact."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            c = await _make_fact(session, key="t2.63-both-arms-one-fact")
            for name in ("sess-both-1", "sess-both-2", "sess-both-3"):
                await _add_origin(session, c, name, kind="memory")
            assert (await recompute_fact(session, c)).outcome == "promote"
            await session.commit()

            # arm one: disputed after corroboration
            await record_event(
                session, event_type="verified", object_type="fact",
                object_id=_uuid.UUID(c), project="default",
                payload={
                    "before": {"verification_status": "corroborated"},
                    "after": {"verification_status": "disputed"},
                    "outcome": "dispute", "origin_count": 3, "required_n": 3,
                    "gate_fired": "diversity", "source_kinds": ["memory"],
                    "contradiction_blocked": True, "confidence": 0.6,
                },
            )
            # arm two: the same fact, human-rejected
            await record_event(
                session, event_type="human_verdict", object_type="fact",
                object_id=_uuid.UUID(c), project="default",
                payload={"verdict": "rejected", "verification_status": "disputed"},
            )
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )
            audit = report.false_promotion
            assert audit.disputed_after_corroboration == 1, "arm one should see it"
            assert audit.human_rejected == 1, "arm two should see it too"
            assert audit.false_promotions == 1, (
                "one fact in both arms is ONE false promotion, not two"
            )
            assert audit.rate is not None and audit.rate <= 1.0, (
                "a rate above 1.0 is arithmetically impossible for a fact count"
            )
            # The headline must reach the durable artifact too. Without it a
            # ledger reader sees the two arm counts beside a union-derived
            # rate and reconstructs the count by summing -- getting 2 where
            # the recorded rate says 1. Fixing the object and not the
            # artifact is exactly what this round already had to correct
            # once, on the slice tables.
            ledger = pm.to_ledger_row(report)["false_promotion"]
            assert ledger["false_promotions"] == 1, (
                "the ledger must carry the union headline, not just the arms"
            )
            assert (
                ledger["disputed_after_corroboration"] + ledger["human_rejected"]
                != ledger["false_promotions"]
            ), "this fixture exists precisely because the arms must not sum"

    @pytest.mark.asyncio
    async def test_a_seeded_rejection_is_counted_by_the_audit(self):
        """The other half of T2.63's closure: the arm must actually read
        non-zero now. Without this, retargeting the guard above would leave
        the count structurally blind exactly as before, just for a new
        reason."""
        async with bench_db.session_factory() as session:
            since = await _db_now(session)
            c = await _make_fact(session, key="t2.63-rejected-after-corroboration")
            for name in ("sess-hv-1", "sess-hv-2", "sess-hv-3"):
                await _add_origin(session, c, name, kind="memory")
            decision = await recompute_fact(session, c)
            await session.commit()
            assert decision.outcome == "promote"

            # Drive the REAL emitter, not a planted row. Planting via
            # `record_event` would leave this green with `reject_fact`'s
            # emission deleted -- the door -> emitter -> runner chain would
            # rest on nothing but the two copies of the SQL happening to
            # agree, and this epic has already shipped a green floor over a
            # red gate once.
            from app.services.human_adjudication import reject_fact

            await reject_fact(session, c, actor="reviewer@example.com")
            await session.commit()

            report = await pm.compute_promotion_metrics(
                session, since=since, until=since + _WINDOW_SLACK, database_identity="test",
            )
            audit = report.false_promotion
            assert audit.human_rejected == 1
            # The arm display count is not the headline. Without this, the
            # union's `rejected_after` branch is decorative: rewriting its
            # verdict predicate to match nothing survived the whole suite,
            # because the overlap test reaches the headline through the
            # DISPUTED arm and this one only checked the display. A
            # rejection-only false promotion -- the human catching what the
            # machine missed, which is the exact case doc 17 §5.1's second
            # half exists for -- would then be undercounted, in the one
            # number this module may never undercount.
            assert audit.disputed_after_corroboration == 0, (
                "this fact was never machine-disputed -- the headline must "
                "come from the rejection arm alone"
            )
            assert audit.false_promotions == 1, (
                "a rejection-only false promotion must reach the headline"
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

    def test_the_ledger_row_carries_the_scored_bound_not_only_the_rate(self):
        """A recorded run must carry the number its verdict came from.

        The row held `rate` alone. That was the scored quantity until T2.132
        and is context now, so a reader re-deriving a verdict from a stored
        row would re-derive the superseded one — and `1/149` and `20/2980`
        are the same number in it, which is the exact distinction the switch
        was made to draw.
        """
        base = pm.no_schema_report(
            since=datetime(2026, 1, 1, tzinfo=timezone.utc),
            until=datetime(2026, 4, 1, tzinfo=timezone.utc),
            database_identity="host:5433/darkmem",
        )
        report = dataclasses.replace(
            base,
            schema_present=True,
            false_promotion=pm.FalsePromotionAudit(
                total_corroborations=149,
                disputed_after_corroboration=1,
                human_rejected=0,
                false_promoted_facts=1,
            ),
        )
        fp = pm.to_ledger_row(report)["false_promotion"]
        assert fp["rate"] == pytest.approx(0.006711, abs=1e-5)
        assert fp["upper_bound"] == pytest.approx(0.0314, abs=5e-4)
        assert fp["confidence"] == pm.FALSE_PROMOTION_CONFIDENCE
        assert fp["scored_on"] == "upper_bound"

    def test_an_empty_window_records_no_bound_rather_than_a_zero(self):
        base = pm.no_schema_report(
            since=datetime(2026, 1, 1, tzinfo=timezone.utc),
            until=datetime(2026, 4, 1, tzinfo=timezone.utc),
            database_identity="host:5433/darkmem",
        )
        fp = pm.to_ledger_row(base)["false_promotion"]
        assert fp["rate"] is None
        assert fp["upper_bound"] is None
