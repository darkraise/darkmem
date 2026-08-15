"""TH1.01 — the faithfulness bars: pinned defaults, re-derived directions,
and the floor clamp. Committed before any of Lane A exists; the definition is
docs/superpowers/specs/2026-08-15-faithfulness-metric-and-bar-design.md."""
import logging

import pytest

from app.models.config import Config
from app.services import faithfulness_bars as fb


# ── the pins: moving a goalpost is a visible two-file diff ───────────────


def test_defaults_pinned_by_value():
    assert fb.FAITHFULNESS_BAR_DEFAULTS == {
        "faithfulness_coverage_bar": 1.0,
        "faithfulness_gate_precision_bar": 0.95,
        "faithfulness_gate_recall_bar": 0.90,
    }


def test_coverage_bar_is_not_the_fitted_value():
    # The obvious fitted value is the article twin's 0.95 ("match the twin").
    # 1.0 is the derivation — the grounded label asserts *full* grounding and
    # must mean the same thing at every answer length — and it is the one
    # value no laundering argument can reach, since every fit loosens.
    assert fb.FAITHFULNESS_BAR_DEFAULTS["faithfulness_coverage_bar"] == 1.0
    assert fb.FAITHFULNESS_BAR_DEFAULTS["faithfulness_coverage_bar"] != 0.95


def test_precision_bar_is_the_truth_critical_side_of_the_rule():
    # Doc 17 §6's standing rule: truth-critical 0.95, the other 0.90. A pair
    # that drifted to 0.90/0.90 would be a laundered gate, not a rederivation.
    assert fb.FAITHFULNESS_BAR_DEFAULTS["faithfulness_gate_precision_bar"] == 0.95
    assert fb.FAITHFULNESS_BAR_DEFAULTS["faithfulness_gate_precision_bar"] != 0.90


# ── directions re-derived from the predicates, never trusted from prose ──


def _bars(**overrides):
    bars = dict(fb.FAITHFULNESS_BAR_DEFAULTS)
    bars.update(overrides)
    return bars


def test_coverage_bar_is_a_floor_at_its_own_comparison_site():
    # Raising the bar can only refuse answers a lower bar admitted, so
    # higher is stricter and the conservative direction is HIGHER.
    admitted_low = fb.answer_grounded(19, 20, _bars(faithfulness_coverage_bar=0.95))
    admitted_high = fb.answer_grounded(19, 20, _bars(faithfulness_coverage_bar=1.0))
    assert admitted_low and not admitted_high
    spec = fb.FAITHFULNESS_BARS["faithfulness_coverage_bar"]
    assert spec.conservative is fb.Conservative.HIGHER


@pytest.mark.parametrize(
    "key,clears_kwargs",
    [
        ("faithfulness_gate_precision_bar", dict(entailed_precision=0.93,
                                                 entailed_recall=1.0)),
        ("faithfulness_gate_recall_bar", dict(entailed_precision=1.0,
                                              entailed_recall=0.85)),
    ],
)
def test_gate_bars_are_floors_at_their_own_comparison_sites(key, clears_kwargs):
    admitted_low = fb.faithfulness_role_clears(**clears_kwargs, bars=_bars(**{key: 0.8}))
    admitted_high = fb.faithfulness_role_clears(**clears_kwargs, bars=_bars(**{key: 0.99}))
    assert admitted_low and not admitted_high
    assert fb.FAITHFULNESS_BARS[key].conservative is fb.Conservative.HIGHER


def test_every_bar_has_a_stated_direction():
    for key, spec in fb.FAITHFULNESS_BARS.items():
        assert isinstance(spec.conservative, fb.Conservative), key


# ── the serving predicate: counts, the zero-claim refusal, the regime ────


def test_fully_entailed_answers_are_grounded():
    assert fb.answer_grounded(1, 1, fb.FAITHFULNESS_BAR_DEFAULTS)
    assert fb.answer_grounded(37, 37, fb.FAITHFULNESS_BAR_DEFAULTS)


def test_one_miss_refuses_the_grounded_label_at_any_length():
    assert not fb.answer_grounded(9, 10, fb.FAITHFULNESS_BAR_DEFAULTS)
    assert not fb.answer_grounded(39, 40, fb.FAITHFULNESS_BAR_DEFAULTS)


def test_the_regime_arithmetic_the_derivation_states():
    # Short regime: below 20 sentences, one miss fails the twin's 0.95 too —
    # the two bars are the same predicate where answers actually live.
    assert not 9 / 10 >= 0.95
    assert not 18 / 19 >= 0.95
    # Long regime: 0.95 starts serving unsupported sentences under the
    # grounded badge (39/40 clears it), which is the leak 1.0 closes.
    assert 39 / 40 >= 0.95
    assert not fb.answer_grounded(39, 40, fb.FAITHFULNESS_BAR_DEFAULTS)


def test_zero_claims_ground_nothing():
    # 0/0 is refused, never vacuously cleared: an empty or all-label body
    # must not collect the strongest label the surface serves.
    assert not fb.answer_grounded(0, 0, fb.FAITHFULNESS_BAR_DEFAULTS)


@pytest.mark.parametrize("entailed,total", [(-1, 5), (3, -1), (6, 5)])
def test_incoherent_counts_raise(entailed, total):
    with pytest.raises(ValueError):
        fb.answer_grounded(entailed, total, fb.FAITHFULNESS_BAR_DEFAULTS)


# ── resolution: DB over defaults, floors clamped, licences bounded ───────


def test_no_rows_resolves_to_the_committed_defaults():
    assert fb.resolve_faithfulness_bars({}) == fb.FAITHFULNESS_BAR_DEFAULTS


def test_tightening_is_free():
    bars = fb.resolve_faithfulness_bars({"faithfulness_gate_recall_bar": 0.95})
    assert bars["faithfulness_gate_recall_bar"] == 0.95


def test_wrapped_value_shape_is_read():
    bars = fb.resolve_faithfulness_bars(
        {"faithfulness_gate_recall_bar": {"value": 0.93}}
    )
    assert bars["faithfulness_gate_recall_bar"] == 0.93


def test_an_unlicensed_loosening_clamps_to_the_floor(caplog):
    with caplog.at_level(logging.WARNING):
        bars = fb.resolve_faithfulness_bars({"faithfulness_coverage_bar": 0.8})
    assert bars["faithfulness_coverage_bar"] == 1.0
    assert fb.FAITHFULNESS_BAR_LICENCES_KEY in caplog.text


def test_a_licensed_loosening_within_its_bound_is_honoured():
    rows = {
        "faithfulness_coverage_bar": 0.95,
        fb.FAITHFULNESS_BAR_LICENCES_KEY: {
            "licensed": {
                "faithfulness_coverage_bar": {
                    "value": 0.95,
                    "argument": "gate-ledger.md#g-f",
                }
            }
        },
    }
    assert fb.resolve_faithfulness_bars(rows)["faithfulness_coverage_bar"] == 0.95


def test_loosening_past_the_licence_bound_clamps_to_the_floor_not_the_bound():
    rows = {
        "faithfulness_coverage_bar": 0.9,
        fb.FAITHFULNESS_BAR_LICENCES_KEY: {
            "licensed": {
                "faithfulness_coverage_bar": {
                    "value": 0.95,
                    "argument": "gate-ledger.md#g-f",
                }
            }
        },
    }
    # To the floor, never to 0.95: the licensed value is a number the
    # operator did not write, on an argument they did not make for it.
    assert fb.resolve_faithfulness_bars(rows)["faithfulness_coverage_bar"] == 1.0


@pytest.mark.parametrize(
    "entry",
    [
        {"value": 0.95},                                   # no argument
        {"value": "0.95", "argument": "gate-ledger.md"},   # non-numeric
        {"value": 0.0, "argument": "gate-ledger.md"},      # untippable bound
        {"value": -1, "argument": "gate-ledger.md"},
        {"value": True, "argument": "gate-ledger.md"},     # bool is int
        "0.95",                                            # not an object
    ],
)
def test_a_malformed_licence_entry_licenses_nothing(entry):
    rows = {
        "faithfulness_coverage_bar": 0.95,
        fb.FAITHFULNESS_BAR_LICENCES_KEY: {
            "licensed": {"faithfulness_coverage_bar": entry}
        },
    }
    assert fb.resolve_faithfulness_bars(rows)["faithfulness_coverage_bar"] == 1.0


def test_a_licence_for_a_foreign_key_is_ignored():
    rows = {
        fb.FAITHFULNESS_BAR_LICENCES_KEY: {
            "licensed": {
                "contradiction_recall_bar": {
                    "value": 0.5,
                    "argument": "gate-ledger.md",
                }
            }
        }
    }
    assert fb.resolve_faithfulness_bars(rows) == fb.FAITHFULNESS_BAR_DEFAULTS


@pytest.mark.parametrize("value", ["high", True, float("nan"), {"value": None}])
def test_an_unreadable_bar_row_raises_not_silently_defaults(value):
    with pytest.raises(ValueError):
        fb.resolve_faithfulness_bars({"faithfulness_gate_recall_bar": value})


# ── the config surface end to end ────────────────────────────────────────


async def test_get_faithfulness_bars_reads_the_config_table(session):
    session.add(Config(key="faithfulness_gate_recall_bar", value={"value": 0.94}))
    session.add(Config(key="faithfulness_coverage_bar", value=0.7))
    await session.flush()
    bars = await fb.get_faithfulness_bars(session)
    assert bars["faithfulness_gate_recall_bar"] == 0.94   # tightening honoured
    assert bars["faithfulness_coverage_bar"] == 1.0       # loosening clamped
    assert bars["faithfulness_gate_precision_bar"] == 0.95


class TestLoosensReadsTheDirectionItCarries:
    """`loosens` hardcoded `<` while the type carried a `conservative` field.

    Every shipped bar is a HIGHER floor, so the two agreed and no test could
    tell them apart — which is exactly how a guard reads as enforced while
    being decorative. The module's own docstring cites T2.127, whose finding
    was that a direction-blind clamp reads a ceiling bar's abuse *upward* as a
    tightening; G-C's `verification_false_promotion_bar` is that ceiling, and
    a faithfulness ceiling added later would have inherited the same hole
    (TH1.01 review, Important-1).
    """

    def test_a_floor_loosens_downward(self):
        spec = fb.FaithfulnessBarSpec(0.90, fb.Conservative.HIGHER)
        assert spec.loosens(0.80)
        assert not spec.loosens(0.95)

    def test_a_ceiling_loosens_upward(self):
        """The case the hardcoded `<` got backwards."""
        spec = fb.FaithfulnessBarSpec(0.01, fb.Conservative.LOWER)
        assert spec.loosens(0.05), (
            "a ceiling is loosened by being raised; a direction-blind guard "
            "waves that through as a tightening"
        )
        assert not spec.loosens(0.005)

    def test_the_direction_is_read_rather_than_assumed(self):
        """Structural: `loosens` must consult the field it stores."""
        import ast, inspect, textwrap
        src = textwrap.dedent(inspect.getsource(fb.FaithfulnessBarSpec.loosens))
        names = {
            node.attr for node in ast.walk(ast.parse(src))
            if isinstance(node, ast.Attribute)
        }
        assert "conservative" in names, (
            "loosens must dispatch on the direction the spec carries, not on a "
            "comparison that happens to match every bar shipped today"
        )


def test_the_licence_row_is_actually_fetched_from_the_database():
    """A mutant dropping the licence key from `_BARS_SQL` survived all 32
    tests (TH1.01 review, Minor-1): every licence test fed rows in directly,
    so nothing proved the resolver *asks* the database for the row it clamps
    against. The failure direction is conservative — a licence that never
    arrives clamps a loosening back — but an unlicensable bar is not the
    documented contract."""
    import app.services.faithfulness_bars as fb
    sql = str(fb._BARS_SQL)
    assert fb.FAITHFULNESS_BAR_LICENCES_KEY in sql or ":keys" in sql, (
        "the bars query must reach for the licence row too"
    )
    # And the key must be in the parameter set the caller binds.
    import ast, inspect, textwrap
    src = textwrap.dedent(inspect.getsource(fb.get_faithfulness_bars))
    assert "FAITHFULNESS_BAR_LICENCES_KEY" in src, (
        "the licence key must be bound into the query's keys, or the row is "
        "never read and the licence path is decorative"
    )
