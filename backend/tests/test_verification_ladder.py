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
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.models.config import Config
from app.repositories.fact_sources import FactSourceRepository as _FSR
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
    OriginObservation,
    OriginProfile,
)
from app.services.verification_ladder import (
    LADDER_CONFIG_KEY,
    NO_DETECTOR,
    compute_confidence,
    decide,
    recompute_fact,
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
        assert d.confidence == pytest.approx(0.90, abs=5e-5)

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

    def test_no_origin_profile_reaches_disputed_on_its_own(self):
        """`disputed` is reachable only through the veto input (T2.04).

        Asserted at runtime rather than left to the ``Literal``, because Python
        does not enforce annotations. The count, the gates and the config can
        move the fact up and down the ladder; none of them may move it sideways.
        """
        profiles = (
            profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",))),
            profile(origin("a")),
            profile(),
            profile(*(origin(f"o{i}") for i in range(9))),
        )
        for prof in profiles:
            for status in ("candidate", "corroborated"):
                for verdict in (NO_DETECTOR, False):
                    d = decide_at(prof, status, open_contradiction=verdict)
                    assert d.target_status != "disputed"

    def test_confirmed_is_held_and_never_demoted(self):
        """Even with zero origins, which would demote any machine status."""
        d = decide_at(profile(), "confirmed")
        assert (d.target_status, d.outcome) == ("confirmed", "hold")

    def test_disputed_is_held_without_an_adjudication(self):
        """No detector reported, so nothing may resolve the dispute.

        An implementation that recomputed `disputed` like any other status
        would silently promote it to `corroborated` the first time a recompute
        ran over one. The full entry/exit semantics live in
        ``tests/test_contradiction_veto.py``; this is the T2.03-side pin that
        the default keyword cannot move a disputed fact.
        """
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        d = decide_at(strong, "disputed")
        assert (d.target_status, d.outcome) == ("disputed", "hold")


class TestContradictionVeto:
    def test_an_open_contradiction_vetoes_an_otherwise_good_promotion(self):
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(strong).outcome == "promote"
        vetoed = decide_at(strong, open_contradiction=True)
        assert vetoed.outcome == "dispute"
        assert vetoed.contradiction_blocked is True
        assert vetoed.target_status == "disputed"

    def test_the_default_is_no_detector_not_adjudicated_clean(self):
        assert NO_DETECTOR is None, (
            "NO_DETECTOR must stay distinguishable from an affirmative clean "
            "verdict; collapsing them lets silence resolve a dispute"
        )
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(strong).contradiction_blocked is False

    def test_a_veto_demotes_a_corroborated_fact(self):
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        d = decide_at(strong, "corroborated", open_contradiction=True)
        assert (d.target_status, d.outcome) == ("disputed", "dispute")


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
            # The time_gap instantiation of "any gate-fired K>=N -> 0.90".
            # Without it, a mutant paying the bonus only for "diversity"
            # survives, and a time-gap-corroborated fact silently carries
            # 0.80 into T2.06's journal evidence and T2.36's badge.
            (2, 2, "time_gap", 0.90),
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

    def test_a_disputed_fact_still_carries_its_support_score(self):
        """Contradiction deliberately does not enter the formula.

        Confidence is *support*; the dispute is adjudication and lives on the
        verification and ``review_state`` surfaces. Pinned so the next reader
        finds a disputed fact at 0.90 a decision rather than a bug.
        """
        strong = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        vetoed = decide_at(strong, open_contradiction=True)
        assert vetoed.target_status == "disputed"
        assert vetoed.confidence == 0.90


# ────────────── Step 4 — recompute_fact against real rows ──────────────


async def _make_fact(session, *, key="k-1", status=None):
    repo = KnowledgeTripleRepository(session)
    row = await repo.insert_open(
        triple_key=key,
        subject_name="darkmem",
        object_name="pgvector",
        rel_type="USES",
        fact="darkmem uses pgvector",
        reference_time=T0,
        project="default",
    )
    if status is not None:
        await repo.set_verification_status(row["id"], status)
    await session.commit()
    return row["id"]


async def _add_origin(session, fact_id, origin_key, *, kind="memory", ref=None):
    await _FSR(session).add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref or f"{kind}:{origin_key}",
        origin_key=origin_key,
    )
    await session.commit()


async def _verified_events(session, fact_id) -> list[dict]:
    result = await session.execute(
        text(
            "SELECT payload FROM events WHERE event_type = 'verified' "
            "AND object_id = CAST(:id AS uuid) ORDER BY created_at"
        ),
        {"id": str(fact_id)},
    )
    return [r[0] for r in result.all()]


async def _read(session, fact_id) -> dict:
    result = await session.execute(
        text(
            "SELECT verification_status, confidence, valid_at, invalid_at, expired_at "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )
    return dict(result.mappings().one())


class TestRecomputeFact:
    async def test_promotion_writes_status_and_confidence_together(self, session):
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "promote"
        row = await _read(session, fact_id)
        assert row["verification_status"] == "corroborated"
        assert row["confidence"] == pytest.approx(0.90, abs=5e-5)

    async def test_exactly_one_verified_event_per_transition(self, session):
        """The sole-journaller hand-off, by construction.

        ``recompute_fact``'s only write path is the repository emitter, so a
        second emitter here would show up as two rows for one transition and
        would double-count in G-C.
        """
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        await recompute_fact(session, fact_id)
        await session.commit()
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["before"]["verification_status"] == "candidate"
        assert events[0]["after"]["verification_status"] == "corroborated"

    async def test_an_idempotent_rerun_journals_nothing_further(self, session):
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        await recompute_fact(session, fact_id)
        await session.commit()
        second = await recompute_fact(session, fact_id)
        await session.commit()

        assert second.outcome == "hold"
        assert len(await _verified_events(session, fact_id)) == 1

    async def test_below_n_demotes_a_corroborated_fact(self, session):
        fact_id = await _make_fact(session, status="corroborated")
        await _add_origin(session, fact_id, "sess-a", kind="memory")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert decision.outcome == "demote"
        assert (await _read(session, fact_id))["verification_status"] == "candidate"

    async def test_a_fact_with_no_sources_demotes_and_does_not_expire(self, session):
        """Demotion only. Expiry on last-source-withdrawal is T2.47's."""
        fact_id = await _make_fact(session, status="corroborated")
        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert (decision.origin_count, decision.outcome) == (0, "demote")
        row = await _read(session, fact_id)
        assert row["verification_status"] == "candidate"
        assert row["expired_at"] is None

    async def test_a_confirmed_fact_holds_while_confidence_refreshes(self, session):
        """The status-free write path.

        ``set_verification_status`` refuses ``confirmed`` before any read, so
        the applier cannot pass a confirmed fact its own status back; it must
        write confidence with ``status=None``. Without that path this test
        raises rather than fails.
        """
        fact_id = await _make_fact(session)
        await session.execute(
            text(
                "UPDATE knowledge_triples SET verification_status = 'confirmed', "
                "confidence = 0.1 WHERE id = CAST(:id AS uuid)"
            ),
            {"id": str(fact_id)},
        )
        await session.commit()
        await _add_origin(session, fact_id, "human-1", kind="human")
        await _add_origin(session, fact_id, "sess-a", kind="memory")

        decision = await recompute_fact(session, fact_id)
        await session.commit()

        assert (decision.target_status, decision.outcome) == ("confirmed", "hold")
        row = await _read(session, fact_id)
        assert row["verification_status"] == "confirmed", "the machine never moves it"
        assert row["confidence"] == pytest.approx(0.90, abs=5e-5), "but support refreshes"
        assert await _verified_events(session, fact_id) == [], "a hold is not a transition"

    async def test_the_belief_axis_is_bit_identical_across_a_recompute(self, session):
        """Verification and belief are orthogonal axes (doc 08 §3)."""
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")
        before = await _read(session, fact_id)

        await recompute_fact(session, fact_id)
        await session.commit()
        after = await _read(session, fact_id)

        for column in ("valid_at", "invalid_at", "expired_at"):
            assert before[column] == after[column]

    async def test_a_missing_fact_holds_and_writes_nothing(self, session):
        from uuid import uuid4

        decision = await recompute_fact(session, uuid4())
        assert (decision.current_status, decision.outcome) == ("missing", "hold")

    async def test_a_contradiction_vetoes_the_promotion_it_would_have_made(self, session):
        fact_id = await _make_fact(session)
        await _add_origin(session, fact_id, "sess-a", kind="memory")
        await _add_origin(session, fact_id, "repo-b", kind="code")

        decision = await recompute_fact(session, fact_id, open_contradiction=True)
        await session.commit()

        assert decision.contradiction_blocked is True
        row = await _read(session, fact_id)
        assert row["verification_status"] == "disputed"
        events = await _verified_events(session, fact_id)
        assert len(events) == 1
        assert events[0]["after"]["verification_status"] == "disputed"


# ────────── Invariant 15 — the ladder is Tier-C only, enforced ──────────

BACKEND = Path(__file__).resolve().parent.parent

# Modules legitimately permitted to reach the ladder. T2.09's
# `verification_recompute` job is the intended Tier-C caller: it drains
# `sources_changed` past a watermark and reconciles a slow-arm slice of
# `fact_sources` directly, calling `recompute_fact` on each affected fact.
# Nothing else may reach it -- the Tier-C hand-off is recorded here, not as a
# silent test edit.
_ALLOWED_LADDER_FILES: set[str] = {"app/services/verification_recompute.py"}


def _app_sources() -> list[Path]:
    return [p for p in (BACKEND / "app").rglob("*.py") if "__pycache__" not in str(p)]


def _forbidden_ladder_references(paths: list[Path], root: Path = BACKEND) -> list[str]:
    """The one predicate. ``root`` is a parameter so the negative control below
    can point this exact function at a synthesised tree.

    A control that re-types the predicate inline proves only that the copy
    works: the real scan could go completely blind — its match strings
    misspelled — and the control would still pass, which is the rot the control
    exists to prevent.
    """
    offenders: list[str] = []
    for path in paths:
        rel = str(path.relative_to(root))
        if rel == "app/services/verification_ladder.py" or rel in _ALLOWED_LADDER_FILES:
            continue
        for lineno, line in enumerate(path.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if (
                "app.services.verification_ladder" in line
                or "from app.services import verification_ladder" in line
                or "recompute_fact" in line
            ):
                offenders.append(f"{rel}:{lineno}: {stripped}")
    return offenders


def test_no_app_code_reaches_the_verification_ladder():
    """Tree-wide, not an enumerated blocklist.

    A named list of Tier-A/B modules is exactly as good as its enumeration:
    a violation in `hybrid_search.py`, `buffer_flush.py`, or any module added
    next year walks straight past it while the test stays green. Scanning
    everything and allowlisting the exceptions inverts that — a new module is
    forbidden by default.
    """
    paths = _app_sources()
    # A vacuous scan would pass by finding nothing to scan. The floor sits well
    # below the real count and far above zero, so a mis-resolved root fails
    # loudly instead of reporting success.
    assert len(paths) > 100, (
        f"only found {len(paths)} files under app/ — the scan below would pass "
        "vacuously; check BACKEND / the glob path"
    )
    offenders = _forbidden_ladder_references(paths)
    assert not offenders, (
        "app code reached the verification ladder:\n"
        + "\n".join(offenders)
        + "\nThe ladder is Tier-C only (invariant 15): reconciliation stays off "
          "the hot path, and a capture or retrieval path calling recompute_fact "
          "inline to 'accelerate' a promotion is exactly what this forbids. "
          "T2.09's job is the intended caller and joins _ALLOWED_LADDER_FILES."
    )


def test_the_guard_rejects_a_forbidden_reference(tmp_path):
    """In-suite negative control — the guard's teeth, proven every run.

    A one-time manual break-and-revert proves the guard worked once, on one
    machine, in one session. This proves it on every run, which is what stops
    the scan from rotting into a test that passes because it matches nothing.
    """
    fake = tmp_path / "app" / "services"
    fake.mkdir(parents=True)
    violation = fake / "eager_capture.py"
    violation.write_text(
        "from app.services.verification_ladder import recompute_fact\n"
        "async def on_capture(session, fact_id):\n"
        "    await recompute_fact(session, fact_id)\n"
    )
    # Calls the REAL guard, not a re-typed copy of its predicate. Breaking the
    # match strings in `_forbidden_ladder_references` — a fully blind scan —
    # must turn this red, which is the whole point of a teeth-prover.
    offenders = _forbidden_ladder_references([violation], root=tmp_path)
    assert offenders, (
        "the real guard failed to flag a synthesised violation; the tree-wide "
        "scan above would be reporting success while blind"
    )
    assert any("eager_capture.py" in o for o in offenders)

    # And the allowlist must be able to exempt it — a guard that cannot be
    # satisfied is one a future agent deletes rather than configures. Restore
    # the *real* prior value on the way out, not a hardcoded set() — T2.09
    # landed a permanent, non-empty allowlist, and resetting to the literal
    # empty set here would silently drop verification_recompute.py's own
    # exemption for the rest of the test session.
    global _ALLOWED_LADDER_FILES
    previous = _ALLOWED_LADDER_FILES
    _ALLOWED_LADDER_FILES = {"app/services/eager_capture.py"}
    try:
        assert _forbidden_ladder_references([violation], root=tmp_path) == []
    finally:
        _ALLOWED_LADDER_FILES = previous


def test_the_allowlist_holds_exactly_t209s_module_now_that_it_has_landed():
    """T2.09 is the first legitimate caller, and now the only one.

    Before this task, the allowlist was empty and a sibling test pinned that
    directly (`test_the_allowlist_is_empty_until_its_owning_task_lands`, now
    obsolete — this is its landed replacement, same discipline
    `test_shipped_family_members_no_longer_wear_the_placeholder_marker`
    follows in `test_dream_jobs.py`: the marker for "not yet" must flip
    the moment its owning task ships, not stay green by accident.
    """
    assert _ALLOWED_LADDER_FILES == {"app/services/verification_recompute.py"}


# ───────── F1 — the config → decision seam, pinned end to end ─────────


class TestConfigReachesTheDecision:
    """The brief's own D2 test: *the decision actually changes when config changes*.

    Everything else about config is pinned one layer away from the outcome — the
    reader is asserted off the returned dataclass, and the threshold rule is
    asserted on `OriginProfile` directly. Neither notices a `decide()` that
    ignores its `config` argument, or a `recompute_fact` that substitutes
    `LadderConfig()` for the row it read. Both mutants survived all 64 tests
    before these; an operator's tightened row, or T2.40's measured loosening,
    would silently never reach a single promotion.
    """

    def test_decide_honours_a_tightened_config(self):
        three_same_day = profile(origin("a"), origin("b"), origin("c"))
        assert decide_at(three_same_day).outcome == "promote"
        tightened = decide_at(three_same_day, config=LadderConfig(n_default=4))
        assert tightened.required_n == 4
        assert tightened.outcome == "hold", "the config never reached the decision"

    def test_decide_honours_a_tightened_time_gap(self):
        ten_days = profile(origin("a", first=T0), origin("b", first=T0 + timedelta(days=10)))
        assert decide_at(ten_days).outcome == "promote"
        tightened = decide_at(ten_days, config=LadderConfig(time_gap_days=14))
        assert (tightened.gate_fired, tightened.required_n) == ("none", 3)
        assert tightened.outcome == "hold"

    def test_decide_honours_a_tightened_n_diverse(self):
        diverse = profile(origin("a", kinds=("memory",)), origin("b", kinds=("code",)))
        assert decide_at(diverse).outcome == "promote"
        tightened = decide_at(diverse, config=LadderConfig(n_diverse=3, n_default=4))
        assert tightened.required_n == 3
        assert tightened.outcome == "hold"

    async def test_recompute_reads_the_config_row_not_the_defaults(self, session):
        """A written row must change a real promotion outcome.

        This is the mutant that matters most: `recompute_fact` calling
        `LadderConfig()` instead of `await get_ladder_config(session)` passes
        every config test in this file, because none of them goes through the
        applier.
        """
        # Two identical facts. The first runs under the shipped defaults, the
        # second under a tightened row -- same evidence, different outcome, so
        # only the config can explain the difference.
        baseline_id = await _make_fact(session, key="k-cfg-baseline")
        for name in ("sess-a", "sess-b", "sess-c"):
            await _add_origin(session, baseline_id, name, ref=f"base:{name}")
        baseline = await recompute_fact(session, baseline_id)
        await session.commit()
        assert (baseline.required_n, baseline.outcome) == (3, "promote")

        await _write_config(session, LADDER_CONFIG_KEY, {"n_default": 4})

        tightened_id = await _make_fact(session, key="k-cfg-tightened")
        for name in ("sess-d", "sess-e", "sess-f"):
            await _add_origin(session, tightened_id, name, ref=f"tight:{name}")
        tightened = await recompute_fact(session, tightened_id)
        await session.commit()

        assert tightened.required_n == 4, "recompute ignored the config row"
        assert tightened.outcome == "hold"
        assert (await _read(session, tightened_id))["verification_status"] == "candidate"


class TestSubOneThresholds:
    """The absolute >= 1 bound must not preempt the floor clamp.

    Fix-round regression (re-review NB-1): the bound originally ran *before*
    the measurement gate and skipped past it, so an unmeasured `n_default: 0`
    became 1, the ordering clamp lifted it to 2, and a two-same-kind-same-day
    fact promoted where the floor holds at 3 — one operator typo producing the
    counterfeit corroboration D3 exists to prevent.
    """

    @pytest.mark.parametrize("value", [0, -7])
    async def test_unmeasured_sub_one_clamps_to_the_floor_not_to_one(
        self, session, caplog, value
    ):
        await _write_config(session, LADDER_CONFIG_KEY, {"n_default": value})
        config = await get_ladder_config(session)
        assert config.n_default == CORROBORATION_N_DEFAULT
        assert "T2.40" in caplog.text, "an unmeasured loosening must name the gate"

    async def test_unmeasured_zero_n_default_does_not_promote_a_same_day_pair(
        self, session
    ):
        """The outcome the ordering bug produced, asserted at the decision."""
        await _write_config(session, LADDER_CONFIG_KEY, {"n_default": 0})
        config = await get_ladder_config(session)
        pair = profile(origin("a"), origin("b"))
        decision = decide("f", "candidate", pair, config)
        assert decision.required_n == 3
        assert decision.outcome == "hold"

    @pytest.mark.parametrize("name", ["n_default", "n_diverse"])
    async def test_a_measured_sub_one_origin_threshold_is_raised_to_one(
        self, session, name
    ):
        """The measurement gate rules how far, never whether it may vanish."""
        await _write_config(session, LADDER_CONFIG_KEY, {name: 0})
        await _write_config(session, LADDER_MEASUREMENTS_KEY, {"measured": [name]})
        config = await get_ladder_config(session)
        assert getattr(config, name) >= 1

    async def test_a_zero_threshold_can_never_promote_a_sourceless_fact(self, session):
        """The hazard the bound exists for, asserted end to end."""
        await _write_config(
            session, LADDER_CONFIG_KEY, {"n_default": 0, "n_diverse": 0}
        )
        await _write_config(
            session, LADDER_MEASUREMENTS_KEY, {"measured": ["n_default", "n_diverse"]}
        )
        config = await get_ladder_config(session)
        decision = decide("f", "candidate", profile(), config)
        assert decision.origin_count == 0
        assert decision.required_n >= 1
        assert decision.outcome != "promote"
