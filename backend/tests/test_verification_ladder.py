"""T2.03 — the verification ladder.

The tests are organised by the Done-when clause they discharge, because each
clause is a property rather than a feature and the property is what a later
reader has to be able to re-check:

* D1  promotion is a pure function of the ladder inputs, reproducible on replay
* D2  N and the diversity rule read from ``config``, defaults stated
* D3  loosening either requires a G-C measurement (T2.40), not an edit
* D4  ``confidence`` is aggregated and recomputed alongside the status
* Inv-15  nothing in capture or retrieval may reach this module

Several tests below exist specifically to kill a mutant that the obvious test
would let through; each says which one, because a test whose purpose is
invisible is a test the next person deletes.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.config import Config
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
    OriginObservation,
    OriginProfile,
)
from app.services.verification_ladder import (
    LADDER_CONFIG_KEY,
    compute_confidence,
    decide,
    LADDER_FLOORS,
    LADDER_MEASUREMENTS_KEY,
    LadderConfig,
    get_ladder_config,
    get_ladder_measurements,
)

# Fixed absolute timestamps, ~400 days before the 2026-07-29 authoring date.
# Nothing here derives from datetime.now(): a now()-relative fixture would
# re-introduce exactly the coupling the purity vector in D1 exists to detect,
# and would additionally rot as the wall clock moves past it.
T0 = datetime(2025, 6, 20, 12, 0, 0, tzinfo=timezone.utc)


def origin(
    key: str | None,
    *,
    kinds: tuple[str, ...] = ("memory",),
    first: datetime = T0,
    last: datetime | None = None,
    rows: int = 1,
) -> OriginObservation:
    return OriginObservation(
        origin_key=key,
        source_kinds=kinds,
        first_seen=first,
        last_seen=last if last is not None else first,
        row_count=rows,
    )


def profile(*origins: OriginObservation, fact_id: str = "fact-1") -> OriginProfile:
    return OriginProfile(fact_id=fact_id, origins=tuple(origins))


async def _write_config(session, key: str, value: dict) -> None:
    existing = await session.execute(select(Config).where(Config.key == key))
    row = existing.scalar_one_or_none()
    if row is None:
        session.add(Config(key=key, value=value))
    else:
        row.value = value
    await session.commit()


# ─────────────────────────── D2 — config, defaults ───────────────────────────


class TestLadderConfigDefaults:
    async def test_absent_row_yields_the_shipped_defaults(self, session):
        config = await get_ladder_config(session)
        assert config == LadderConfig()

    def test_defaults_are_the_fact_sources_constants(self):
        """Drift protection only — it passes trivially while the values coincide.

        Its whole job is to fail loudly if someone re-types a threshold here
        instead of importing it, which is how N acquires two spellings.
        """
        config = LadderConfig()
        assert config.n_default == CORROBORATION_N_DEFAULT
        assert config.n_diverse == CORROBORATION_N_DIVERSE
        assert config.time_gap_days == CORROBORATION_TIME_GAP_DAYS

    def test_floors_are_the_shipped_defaults(self):
        assert LADDER_FLOORS == {
            "n_default": LadderConfig().n_default,
            "n_diverse": LadderConfig().n_diverse,
            "time_gap_days": LadderConfig().time_gap_days,
        }

    async def test_a_tightening_row_is_honoured(self, session):
        await _write_config(
            session, LADDER_CONFIG_KEY, {"n_default": 4, "time_gap_days": 14}
        )
        config = await get_ladder_config(session)
        assert config.n_default == 4
        assert config.time_gap_days == 14
        assert config.n_diverse == CORROBORATION_N_DIVERSE

    async def test_unknown_key_is_ignored_not_fatal(self, session, caplog):
        await _write_config(
            session, LADDER_CONFIG_KEY, {"n_default": 4, "nonsense": 99}
        )
        config = await get_ladder_config(session)
        assert config.n_default == 4
        assert "nonsense" in caplog.text

    async def test_non_integer_value_falls_back_to_its_default(self, session):
        await _write_config(session, LADDER_CONFIG_KEY, {"n_default": "four"})
        config = await get_ladder_config(session)
        assert config.n_default == CORROBORATION_N_DEFAULT

    async def test_boolean_is_not_accepted_as_an_integer(self, session):
        """``True`` is an ``int`` in Python and would read as ``1``.

        A silent 1 is a loosening that looks like a typo, so it must take the
        malformed path rather than the clamp path.
        """
        await _write_config(session, LADDER_CONFIG_KEY, {"n_diverse": True})
        config = await get_ladder_config(session)
        assert config.n_diverse == CORROBORATION_N_DIVERSE


# ──────────────── D3 — loosening needs a measurement, not an edit ────────────


class TestMeasurementGate:
    async def test_no_measurements_row_means_no_permission(self, session):
        assert await get_ladder_measurements(session) == frozenset()

    async def test_measurements_row_only_names_known_parameters(self, session):
        await _write_config(
            session, LADDER_MEASUREMENTS_KEY, {"measured": ["n_default", "bogus"]}
        )
        assert await get_ladder_measurements(session) == frozenset({"n_default"})

    @pytest.mark.parametrize(
        "name,loosened",
        [("n_default", 2), ("n_diverse", 1), ("time_gap_days", 0)],
    )
    async def test_each_floor_clamps_without_a_measurement(
        self, session, caplog, name, loosened
    ):
        """All three parameters clamp, not just ``n_default``.

        Kills the mutant that clamps ``n_default`` alone: a ``time_gap_days: 0``
        row would otherwise manufacture the N=2 gate out of two same-second
        origins, which is the counterfeit corroboration the origin-counting
        doctrine exists to forbid.
        """
        await _write_config(session, LADDER_CONFIG_KEY, {name: loosened})
        config = await get_ladder_config(session)
        assert getattr(config, name) == LADDER_FLOORS[name]
        assert "T2.40" in caplog.text

    @pytest.mark.parametrize(
        "name,loosened",
        [("n_default", 2), ("n_diverse", 1), ("time_gap_days", 0)],
    )
    async def test_each_floor_is_honoured_with_its_measurement(
        self, session, name, loosened
    ):
        await _write_config(session, LADDER_CONFIG_KEY, {name: loosened})
        await _write_config(session, LADDER_MEASUREMENTS_KEY, {"measured": [name]})
        config = await get_ladder_config(session)
        assert getattr(config, name) == loosened

    async def test_permission_is_per_parameter_not_blanket(self, session):
        """The test that separates per-parameter permission from row-presence.

        A reader treating the measurements row's mere existence as permission
        passes every single-parameter test above; only a mixed row catches it.
        """
        await _write_config(
            session, LADDER_CONFIG_KEY, {"n_default": 2, "time_gap_days": 1}
        )
        await _write_config(
            session, LADDER_MEASUREMENTS_KEY, {"measured": ["n_default"]}
        )
        config = await get_ladder_config(session)
        assert config.n_default == 2, "the measured parameter must be honoured"
        assert config.time_gap_days == CORROBORATION_TIME_GAP_DAYS, (
            "the unmeasured parameter must still clamp"
        )

    async def test_ordering_inversion_clamps_even_with_a_measurement(
        self, session, caplog
    ):
        """``n_default < n_diverse`` inverts the ladder and is not unlockable.

        With the fallback bar below the gated bar, firing a gate would *raise*
        N — corroborating evidence would make promotion harder. No measurement
        can make that coherent, so this clamp ignores permission entirely.
        """
        await _write_config(
            session, LADDER_CONFIG_KEY, {"n_default": 1, "n_diverse": 2}
        )
        await _write_config(
            session,
            LADDER_MEASUREMENTS_KEY,
            {"measured": ["n_default", "n_diverse", "time_gap_days"]},
        )
        config = await get_ladder_config(session)
        assert config.n_default == config.n_diverse == 2
        assert "inverts the ladder" in caplog.text


# ───────── D2 — the parameters reach the decision, not just the dataclass ────


class TestThresholdRuleThreading:
    """Each parameter asserted through a *changed N*, never off the dataclass.

    A mutant that ignores an argument in ``required_origin_count_for`` and
    keeps reading the module constant survives every dataclass-level
    assertion: the value was parsed, but never used. These pin the use.
    """

    def test_time_gap_days_changes_the_threshold(self):
        pair = profile(
            origin("a", first=T0),
            origin("b", first=T0 + timedelta(days=10)),
        )
        assert pair.required_origin_count_for(
            n_diverse=2, n_default=3, time_gap_days=7
        ) == 2
        assert pair.required_origin_count_for(
            n_diverse=2, n_default=3, time_gap_days=14
        ) == 3

    def test_n_diverse_changes_the_threshold(self):
        diverse = profile(
            origin("a", kinds=("memory",)),
            origin("b", kinds=("code",)),
        )
        assert diverse.required_origin_count_for(
            n_diverse=2, n_default=3, time_gap_days=7
        ) == 2
        assert diverse.required_origin_count_for(
            n_diverse=3, n_default=4, time_gap_days=7
        ) == 3

    def test_n_default_changes_the_threshold(self):
        same_day = profile(origin("a"), origin("b"), origin("c"))
        assert same_day.required_origin_count_for(
            n_diverse=2, n_default=3, time_gap_days=7
        ) == 3
        assert same_day.required_origin_count_for(
            n_diverse=2, n_default=4, time_gap_days=7
        ) == 4

    def test_gate_identity_matches_the_threshold_that_fired(self):
        diverse = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        gapped = profile(origin("a", first=T0), origin("b", first=T0 + timedelta(days=10)))
        neither = profile(origin("a"), origin("b"))
        assert diverse.gate_fired_for(time_gap_days=7) == "diversity"
        assert gapped.gate_fired_for(time_gap_days=7) == "time_gap"
        assert neither.gate_fired_for(time_gap_days=7) == "none"
        assert gapped.gate_fired_for(time_gap_days=14) == "none"

    def test_the_unknown_bucket_never_lowers_the_bar(self):
        """T2.02's doctrine, re-asserted through the parameterised rule.

        The refactor that introduced ``required_origin_count_for`` must not
        have handed the anonymous bucket a path to a gate.
        """
        with_bucket = profile(
            origin("a", first=T0),
            origin(None, first=T0 + timedelta(days=30)),
        )
        assert with_bucket.origin_count == 2
        assert with_bucket.required_origin_count_for(
            n_diverse=2, n_default=3, time_gap_days=7
        ) == 3
        assert with_bucket.gate_fired_for(time_gap_days=7) == "none"


# ───────────────── D1 — the decision is a pure function ─────────────────


DEFAULTS = LadderConfig()


def decide_at(prof, status="candidate", config=None, **kw):
    return decide("fact-1", status, prof, config or DEFAULTS, **kw)


class TestPromotionShapes:
    def test_diverse_kinds_promote_at_two_origins(self):
        d = decide_at(profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",))))
        assert (d.required_n, d.gate_fired, d.outcome) == (2, "diversity", "promote")
        assert d.target_status == "corroborated"

    def test_same_kind_seven_days_apart_promote_at_two_origins(self):
        d = decide_at(
            profile(origin("a", first=T0), origin("b", first=T0 + timedelta(days=7)))
        )
        assert (d.required_n, d.gate_fired, d.outcome) == (2, "time_gap", "promote")

    def test_same_kind_same_day_needs_three_origins(self):
        two = decide_at(profile(origin("a"), origin("b")))
        assert (two.required_n, two.gate_fired, two.outcome) == (3, "none", "hold")
        assert two.target_status == "candidate"
        three = decide_at(profile(origin("a"), origin("b"), origin("c")))
        assert (three.required_n, three.outcome) == (3, "promote")

    def test_the_anonymous_bucket_counts_but_never_lowers_the_bar(self):
        d = decide_at(
            profile(origin("a", first=T0), origin(None, first=T0 + timedelta(days=30)))
        )
        assert d.origin_count == 2, "the bucket counts toward K"
        assert d.required_n == 3, "but supplies neither the kind nor the time gate"
        assert d.outcome == "hold"


class TestPurity:
    def test_clock_displacement_kill_vector(self):
        """Kills a ``decide()`` that measures the gap from *now* instead of
        between the origins.

        Both origins sit ~400 days in the past, one day apart. The correct
        cross-origin gap is 1 day, so no gate fires and K=2 < N=3: hold. A
        mutant reading ``now() - first_seen`` sees ~400 days, fires the time
        gate, drops N to 2 and promotes. The replay and run-twice assertions
        below cannot tell those two implementations apart; this one can.
        """
        one_day_apart = profile(
            origin("a", first=T0), origin("b", first=T0 + timedelta(days=1))
        )
        d = decide_at(one_day_apart)
        assert d.gate_fired == "none"
        assert d.required_n == 3
        assert d.outcome == "hold", "a clock-relative gate would promote here"

    def test_the_control_for_the_kill_vector(self):
        """The same pair 10 days apart promotes under both implementations.

        Without this, the vector above could pass because the function never
        promotes at all.
        """
        d = decide_at(profile(origin("a", first=T0), origin("b", first=T0 + timedelta(days=10))))
        assert (d.gate_fired, d.required_n, d.outcome) == ("time_gap", 2, "promote")

    def test_the_same_inputs_decide_identically_twice(self):
        prof = profile(origin("a", kinds=("memory",)), origin("b", kinds=("human",)))
        assert decide_at(prof) == decide_at(prof)

    def test_a_decision_replays_from_serialised_inputs(self):
        """Round-trip the inputs through plain data and re-decide.

        Every timestamp is a fixed ISO literal; nothing is derived from the
        test runtime's clock, so this asserts the replay property rather than
        merely re-running inside the same second.
        """
        import json

        prof = profile(
            origin("a", kinds=("memory",), first=T0, last=T0 + timedelta(days=2), rows=3),
            origin("b", kinds=("code",), first=T0 + timedelta(days=9)),
        )
        first = decide_at(prof)

        wire = json.dumps(
            {
                "origins": [
                    {
                        "origin_key": o.origin_key,
                        "source_kinds": list(o.source_kinds),
                        "first_seen": o.first_seen.isoformat(),
                        "last_seen": o.last_seen.isoformat(),
                        "row_count": o.row_count,
                    }
                    for o in prof.origins
                ],
                "config": {
                    "n_default": DEFAULTS.n_default,
                    "n_diverse": DEFAULTS.n_diverse,
                    "time_gap_days": DEFAULTS.time_gap_days,
                },
            }
        )
        restored = json.loads(wire)
        rebuilt = profile(
            *(
                OriginObservation(
                    origin_key=o["origin_key"],
                    source_kinds=tuple(o["source_kinds"]),
                    first_seen=datetime.fromisoformat(o["first_seen"]),
                    last_seen=datetime.fromisoformat(o["last_seen"]),
                    row_count=o["row_count"],
                )
                for o in restored["origins"]
            )
        )
        assert decide_at(rebuilt, config=LadderConfig(**restored["config"])) == first

    def test_decide_reads_no_clock(self):
        """Structural backstop: fail if ``decide`` grows a clock reference.

        The kill vector above catches the specific gap mutant; this catches any
        other clock read (a recency tiebreak, a staleness cutoff) before it can
        acquire its own untested semantics.
        """
        import inspect

        from app.services import verification_ladder

        source = inspect.getsource(verification_ladder.decide)
        source += inspect.getsource(verification_ladder.compute_confidence)
        for forbidden in ("now(", "utcnow", "today(", "time.time", "monotonic"):
            assert forbidden not in source, f"{forbidden} in the pure decision path"


class TestCeiling:
    def test_no_profile_reaches_confirmed(self):
        for prof in (
            profile(origin("h", kinds=("human",)), origin("m", kinds=("memory",))),
            profile(*(origin(f"o{i}", kinds=("human", "code", "memory")) for i in range(9))),
            profile(origin("a", kinds=("human",))),
        ):
            for status in ("candidate", "corroborated"):
                assert decide_at(prof, status).target_status != "confirmed"

    def test_no_profile_reaches_disputed(self):
        """Asserted at runtime, not left to the ``Literal``.

        Python does not enforce annotations, so the type excluding `disputed`
        proves nothing on its own.
        """
        prof = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        for status in ("candidate", "corroborated"):
            for blocked in (False, True):
                d = decide_at(prof, status, open_contradiction=blocked)
                assert d.target_status != "disputed"

    def test_confirmed_is_held_and_never_demoted(self):
        """Even with zero origins, which would demote any machine status."""
        d = decide_at(profile(), "confirmed")
        assert (d.target_status, d.outcome) == ("confirmed", "hold")

    def test_disputed_is_held_unconditionally(self):
        """The NO_DETECTOR stub must not resolve a real dispute.

        With no detector wired, an implementation that recomputed `disputed`
        like any other status would silently promote it to `corroborated` the
        first time the recompute ran over one.
        """
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        d = decide_at(strong, "disputed")
        assert (d.target_status, d.outcome) == ("disputed", "hold")


class TestContradictionBlocks:
    def test_an_open_contradiction_blocks_an_otherwise_good_promotion(self):
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(strong).outcome == "promote"
        blocked = decide_at(strong, open_contradiction=True)
        assert blocked.outcome == "hold"
        assert blocked.contradiction_blocked is True
        assert blocked.target_status == "candidate", "blocked, not disputed"

    def test_the_default_is_no_detector_not_adjudicated_clean(self):
        from app.services.verification_ladder import NO_DETECTOR

        assert NO_DETECTOR is False
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(strong).contradiction_blocked is False

    def test_a_block_does_not_demote_a_corroborated_fact(self):
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        d = decide_at(strong, "corroborated", open_contradiction=True)
        assert (d.target_status, d.outcome) == ("corroborated", "hold")


class TestDemotion:
    def test_falling_below_n_demotes_a_corroborated_fact(self):
        d = decide_at(profile(origin("a")), "corroborated")
        assert (d.target_status, d.outcome) == ("candidate", "demote")

    def test_a_fact_with_no_sources_demotes(self):
        d = decide_at(profile(), "corroborated")
        assert (d.origin_count, d.outcome) == (0, "demote")

    def test_a_candidate_below_n_holds_rather_than_demoting(self):
        d = decide_at(profile(origin("a")), "candidate")
        assert d.outcome == "hold"

    def test_a_corroborated_fact_still_meeting_n_holds(self):
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(strong, "corroborated").outcome == "hold"


# ───────────────────── D4 — the confidence formula ─────────────────────


class TestConfidence:
    @pytest.mark.parametrize(
        "k,n,gate,expected",
        [
            (0, 3, "none", 0.40),
            (2, 3, "none", 0.6667),
            (3, 3, "none", 0.80),
            (2, 2, "diversity", 0.90),
            (9, 3, "none", 0.80),
        ],
    )
    def test_exact_values(self, k, n, gate, expected):
        """Exact vectors, because the four properties cannot catch a typo.

        A mutant writing ``0.04 * support`` is monotone, capped, row-invariant
        and deterministic -- every property test stays green while every
        confidence in the system is wrong.
        """
        got = compute_confidence(origin_count=k, required_n=n, gate_fired=gate)
        assert got == pytest.approx(expected, abs=5e-5)

    def test_the_n_shift_crossing(self):
        """The trickiest vector: a third origin flips N from 3 to 2.

        Adding a differently-kinded origin both raises K and lowers N, so
        confidence jumps two ways at once. An implementation that recomputed
        support against the old N would land somewhere between.
        """
        two_same_kind = profile(origin("a"), origin("b"))
        assert decide_at(two_same_kind).confidence == pytest.approx(0.6667, abs=5e-5)
        plus_diverse = profile(origin("a"), origin("b"), origin("c", kinds=("code",)))
        assert decide_at(plus_diverse).confidence == pytest.approx(0.90, abs=5e-5)

    def test_row_count_invariance(self):
        """Ten rows from one origin score exactly as one row from that origin."""
        once = profile(origin("a", rows=1), origin("b", kinds=("code",), rows=1))
        chatty = profile(origin("a", rows=10), origin("b", kinds=("code",), rows=40))
        assert decide_at(once).confidence == decide_at(chatty).confidence

    def test_monotone_non_decreasing_in_distinct_origins(self):
        scores = [
            decide_at(profile(*(origin(f"o{i}") for i in range(count)))).confidence
            for count in range(0, 6)
        ]
        assert scores == sorted(scores)

    def test_capped_at_ninety_hundredths(self):
        """The machine never claims certainty, however much evidence there is."""
        overwhelming = profile(
            *(origin(f"o{i}", kinds=("memory", "code", "human")) for i in range(40))
        )
        assert decide_at(overwhelming).confidence == 0.90

    def test_a_blocked_hold_still_carries_its_support_score(self):
        """Contradiction deliberately does not enter the formula.

        Confidence is *support*; the dispute lives on the verification and
        review surfaces T2.04 owns. Pinned so the next reader finds this a
        decision rather than a bug.
        """
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        blocked = decide_at(strong, open_contradiction=True)
        assert blocked.outcome == "hold"
        assert blocked.confidence == 0.90
