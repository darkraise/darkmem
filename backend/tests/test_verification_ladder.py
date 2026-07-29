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
