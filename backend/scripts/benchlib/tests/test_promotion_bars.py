"""The G-C bars are pinned by value: moving a goalpost is a two-file diff.

gate-ledger.md rule 3 forbids widening a bar to fit a result. The committed
defaults ARE the stated bars (G-D's "config default" precedent), so this
suite pins each one by exact value — an edit to ``PROMOTION_BAR_DEFAULTS``
fails here until the pin is edited too, which is what makes a moved bar
visible in review rather than a quiet constant tweak.

Since T2.127 it also holds the runtime half: the pin reads the source and
holds no session, so the ``config`` surface needs its own clamp, and that
clamp needs a *direction per bar*. ``TestDirectionIsDerivedNotDeclared``
re-derives every direction from the predicate that actually compares the
bar, so a mis-stated ``Conservative`` fails the build rather than
protecting the wrong side of one number.
"""
from __future__ import annotations

import ast
import inspect
import logging
import textwrap
from pathlib import Path

import pytest

from benchlib import promotion_bars as pb
from benchlib.promotion_metrics import UNDER_POWERED_THRESHOLD

LEDGER = "gate-ledger.md, 'G-C re-measurement'"


def _licence(entries: dict) -> dict:
    return {pb.PROMOTION_BAR_LICENCES_KEY: {"licensed": entries}}


# One observation per bar, chosen so the gate does NOT speak at the committed
# value: `loosens` is the config value that would make it speak, `tightens`
# the one that moves the other way. Nothing here states a direction — the
# direction is read back out of `PROMOTION_BARS` and checked against these.
LIVE_PROBES = {
    "verification_false_promotion_bar": (
        lambda bars: pb.audit_clears(0.02, 200, bars), 0.05, 0.005,
    ),
    "false_promotion_min_corroborations": (
        lambda bars: pb.audit_clears(0.0, 10, bars), 5, 50,
    ),
    "promotion_rate_floor": (
        lambda bars: pb.slice_clears(2, 5, bars), 0.3, 0.9,
    ),
    "promotion_rate_min_eligible": (
        lambda bars: pb.slice_clears(3, 3, bars), 2, 10,
    ),
    "promotion_rate_min_promotions": (
        lambda bars: pb.axis_decidable([(0, 5)], 0, bars), 0, 5,
    ),
}

# The bars that genuinely have a free direction. `promotion_rate_min_eligible`
# is deliberately not one: it is non-monotone at the *composed* verdict, so
# both of its moves take a licence and the per-direction suites below would
# assert a contract it no longer has. Its own behaviour is pinned by
# `TestTheNonMonotoneBar`.
MONOTONE_PROBES = {
    key: probe for key, probe in LIVE_PROBES.items()
    if pb.PROMOTION_BARS[key].conservative is not pb.Conservative.NEITHER
}
assert set(MONOTONE_PROBES) == set(LIVE_PROBES) - {"promotion_rate_min_eligible"}



class TestDefaultsArePinned:
    def test_exact_values(self):
        assert pb.PROMOTION_BAR_DEFAULTS == {
            "verification_false_promotion_bar": 0.01,
            "false_promotion_min_corroborations": 20,
            "promotion_rate_floor": 0.5,
            "promotion_rate_min_eligible": 5,
            "promotion_rate_min_promotions": 1,
            "promotion_journal_completeness_bar": 1.0,
        }

    def test_min_eligible_is_the_harness_power_floor_not_a_retype(self):
        assert (
            pb.PROMOTION_BAR_DEFAULTS["promotion_rate_min_eligible"]
            is UNDER_POWERED_THRESHOLD
        )


class TestResolve:
    def test_defaults_when_no_rows(self):
        bars = pb.resolve_promotion_bars({})
        assert bars["verification_false_promotion_bar"] == 0.01
        assert bars["promotion_journal_completeness_bar"] == 1.0

    def test_db_row_wins_per_key(self):
        bars = pb.resolve_promotion_bars(
            {"verification_false_promotion_bar": 0.005}
        )
        assert bars["verification_false_promotion_bar"] == 0.005
        assert bars["promotion_rate_floor"] == 0.5

    def test_wrapped_value_shape(self):
        bars = pb.resolve_promotion_bars(
            {"promotion_rate_floor": {"value": 0.6}}
        )
        assert bars["promotion_rate_floor"] == 0.6

    def test_unknown_keys_ignored(self):
        bars = pb.resolve_promotion_bars({"unrelated_config_row": {"x": 1}})
        assert bars == pb.resolve_promotion_bars({})

    @pytest.mark.parametrize(
        "bad",
        ["0.01", True, None, [0.01], {"value": "x"},
         float("nan"), float("inf")],
    )
    def test_unreadable_row_raises_never_reverts(self, bad):
        with pytest.raises(ValueError):
            pb.resolve_promotion_bars({"verification_false_promotion_bar": bad})


class TestDirectionIsDerivedNotDeclared:
    """The direction table is re-derived from the comparison sites.

    A clamp that only refused *downward* moves would protect five of these
    six and leave the sixth — the false-promotion ceiling — pointing the
    wrong way: raising it from 0.01 to 0.05 tolerates five times the rate
    and reads as a tightening to any direction-blind guard. So the
    direction each bar declares is checked against the verdict that
    actually consults it.
    """

    def test_every_bar_states_a_direction_and_a_coherent_limit(self):
        # `PROMOTION_BAR_DEFAULTS` is a comprehension over `PROMOTION_BARS`, so
        # comparing the two can never fail. Pin what can: every live bar must
        # carry a probe, so a seventh cannot arrive without its direction
        # being re-derived from the predicate that consults it.
        assert set(MONOTONE_PROBES) | {"promotion_rate_min_eligible"} == {
            key for key in pb.PROMOTION_BARS
            if key != "promotion_journal_completeness_bar"
        }
        for key, spec in pb.PROMOTION_BARS.items():
            loosening_side_is_below = spec.conservative is pb.Conservative.HIGHER
            assert (spec.licence_limit < spec.default) is loosening_side_is_below, (
                f"{key}: the licence limit must sit at the domain edge in the "
                f"bar's own loosening direction"
            )

    @pytest.mark.parametrize("key", sorted(MONOTONE_PROBES))
    def test_declared_direction_matches_the_verdict(self, key):
        probe, loosens, tightens = LIVE_PROBES[key]
        spec = pb.PROMOTION_BARS[key]
        defaults = pb.resolve_promotion_bars({})
        assert not probe(defaults), "the probe must not already clear"

        assert spec.loosens(loosens), f"{key} declares the wrong direction"
        assert probe({**defaults, key: float(loosens)}), (
            f"{key} moved the way this module calls loosening did not make the "
            f"gate speak — the declared direction is wrong or the probe is"
        )

        assert not spec.loosens(tightens)
        assert not probe({**defaults, key: float(tightens)}), (
            f"{key} moved the conservative way must never newly clear"
        )

    def test_the_completeness_bar_is_read_by_no_predicate(self):
        """Stated so the clamp on it is not read as a live protection.

        `journal_completeness_clears` takes no bars at all — the 100 % bar
        is spelled as its only satisfiable form — so a config row moving
        this bar changes no verdict today. Its clamp is prophylactic.
        """
        params = inspect.signature(pb.journal_completeness_clears).parameters
        assert "bars" not in params
        assert pb.journal_completeness_clears(0)
        assert not pb.journal_completeness_clears(1)


class TestClampDirectionPerBar:
    @pytest.mark.parametrize("key", sorted(MONOTONE_PROBES))
    def test_an_unlicensed_loosening_clamps_back(self, key, caplog):
        _, loosens, _ = LIVE_PROBES[key]
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars({key: loosens})
        assert bars[key] == float(pb.PROMOTION_BAR_DEFAULTS[key])
        assert pb.PROMOTION_BAR_LICENCES_KEY in caplog.text

    @pytest.mark.parametrize("key", sorted(MONOTONE_PROBES))
    def test_the_clamped_run_still_cannot_clear(self, key):
        """The negative of the clamp: the verdict the moved bar bought."""
        probe, loosens, _ = LIVE_PROBES[key]
        assert not probe(pb.resolve_promotion_bars({key: loosens}))

    @pytest.mark.parametrize("key", sorted(MONOTONE_PROBES))
    def test_a_tightening_row_survives_untouched(self, key, caplog):
        """The negative control: moving a bar its own conservative way is
        free, needs no licence, and is honoured exactly as written."""
        _, _, tightens = LIVE_PROBES[key]
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars({key: tightens})
        assert bars[key] == float(tightens)
        assert caplog.text == ""

    def test_the_ceiling_bar_clamps_upward_not_downward(self):
        """The bar the direction-blind guard would have missed, spelled out."""
        key = "verification_false_promotion_bar"
        assert pb.resolve_promotion_bars({key: 0.05})[key] == 0.01
        assert pb.resolve_promotion_bars({key: 0.005})[key] == 0.005

    def test_the_unread_completeness_bar_still_clamps(self):
        key = "promotion_journal_completeness_bar"
        assert pb.resolve_promotion_bars({key: 0.9})[key] == 1.0

    def test_a_row_equal_to_the_bar_is_not_a_loosening(self, caplog):
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars({"promotion_rate_floor": 0.5})
        assert bars["promotion_rate_floor"] == 0.5
        assert caplog.text == ""


class TestLicence:
    def test_a_licence_honours_a_loosening_within_its_bound(self):
        rows = {"promotion_rate_floor": 0.4}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        assert pb.resolve_promotion_bars(rows)["promotion_rate_floor"] == 0.4

    def test_the_ceiling_licence_bounds_upward(self):
        key = "verification_false_promotion_bar"
        rows = {key: 0.03}
        rows.update(_licence({key: {"value": 0.05, "argument": LEDGER}}))
        assert pb.resolve_promotion_bars(rows)[key] == 0.03

        rows[key] = 0.08
        assert pb.resolve_promotion_bars(rows)[key] == 0.01

    def test_a_licence_bounds_how_far_the_bar_may_move(self, caplog):
        """The anti-ratchet property: a licence that unlocked whatever the
        bar row says would be the bar row licensing itself one hop over.
        Past the bound clamps to the committed bar, never to the licensed
        value, which the operator never wrote."""
        rows = {"promotion_rate_floor": {"value": 0.1}}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars(rows)
        assert bars["promotion_rate_floor"] == 0.5
        assert "bound 0.3" in caplog.text

    def test_permission_is_per_parameter_not_row_presence(self):
        """A reader treating the row's existence as permission passes every
        single-parameter test above; only a mixed row catches it."""
        rows = {"promotion_rate_floor": 0.4, "promotion_rate_min_eligible": 2}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        bars = pb.resolve_promotion_bars(rows)
        assert bars["promotion_rate_floor"] == 0.4
        assert bars["promotion_rate_min_eligible"] == 5.0

    @pytest.mark.parametrize("entry,missing", [
        ({"value": 0.3}, "argument"),
        ({"value": 0.3, "argument": "   "}, "argument"),
        ({"argument": LEDGER}, "value"),
        ({"value": "0.3", "argument": LEDGER}, "value"),
        # bool is an int subclass, so False would read as a licence to 0.0 —
        # a total unlock, and the one malformed value whose damage is not
        # the same as clamping.
        ({"value": False, "argument": LEDGER}, "value"),
        ("licensed", "value"),
    ])
    def test_a_malformed_entry_licenses_nothing(self, caplog, entry, missing):
        rows = {"promotion_rate_floor": 0.4}
        rows.update(_licence({"promotion_rate_floor": entry}))
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars(rows)
        assert bars["promotion_rate_floor"] == 0.5
        assert missing in caplog.text

    @pytest.mark.parametrize("key,bound", [
        # A floor licensed down to 0 or below can never be tripped by any
        # candidate, so the out-of-bound warning would never fire: the
        # parameter is unlocked silently, which is the one shape this
        # design exists not to be.
        ("promotion_rate_floor", 0.0),
        ("promotion_rate_floor", -1.0),
        ("false_promotion_min_corroborations", 0),
        # The ceiling's mirror image: a rate cannot exceed 1.
        ("verification_false_promotion_bar", 1.0),
        ("verification_false_promotion_bar", 2.0),
    ])
    def test_a_bound_that_bounds_nothing_licenses_nothing(
        self, caplog, key, bound
    ):
        rows = _licence({key: {"value": bound, "argument": LEDGER}})
        with caplog.at_level(logging.WARNING):
            licensed = pb.parse_promotion_bar_licences(
                rows[pb.PROMOTION_BAR_LICENCES_KEY]
            )
        assert licensed == {}
        assert "domain" in caplog.text

    @pytest.mark.parametrize("key,bound", [
        ("promotion_rate_floor", 0.9),
        ("verification_false_promotion_bar", 0.005),
    ])
    def test_an_inert_but_coherent_bound_is_admitted(self, key, bound):
        """The guard refuses incoherence, not values it merely considers
        pointless: a bound on the tightening side licenses no loosening
        any clamp would have refused."""
        licensed = pb.parse_promotion_bar_licences({"licensed": {
            key: {"value": bound, "argument": LEDGER}}})
        assert licensed[key] == bound

    @pytest.mark.parametrize("row_value", [
        {"licensed": "*"},
        {"licensed": True},
        {"licensed": ["promotion_rate_floor"]},
        {"measured": ["promotion_rate_floor"]},
        "*",
    ])
    def test_no_blanket_shape_unlocks_a_bar(self, caplog, row_value):
        """Each of these is a plausible operator guess at the schema —
        including the ladder's own `measured` list, the nearest neighbour —
        and every one must license nothing rather than everything."""
        rows = {"promotion_rate_floor": 0.4,
                pb.PROMOTION_BAR_LICENCES_KEY: row_value}
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars(rows)
        assert pb.parse_promotion_bar_licences(row_value) == {}
        assert bars["promotion_rate_floor"] == 0.5
        assert pb.PROMOTION_BAR_LICENCES_KEY in caplog.text

    def test_a_licence_for_a_non_gc_bar_is_ignored(self, caplog):
        with caplog.at_level(logging.WARNING):
            licensed = pb.parse_promotion_bar_licences({"licensed": {
                "contradiction_recall_bar": {"value": 0.9, "argument": LEDGER}}})
        assert licensed == {}
        assert "contradiction_recall_bar" in caplog.text

    def test_an_unreadable_bar_row_still_raises_under_a_licence(self):
        rows = {"promotion_rate_floor": "0.4"}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        with pytest.raises(ValueError):
            pb.resolve_promotion_bars(rows)


class TestTheReportShowsWhatTheClampDid:
    """T2.128: the clamp was real and invisible in the artifact.

    It announced itself through `logging` alone, and no runner configures a
    handler, so a clamped run's report body was byte-identical to an
    unclamped one — the gate ledger quotes that body. These pin the
    property the task exists to create: the rendered block must *differ*,
    and it must differ by naming what was refused.
    """

    LOOSENING = {"promotion_rate_floor": 0.3}

    def _render(self, rows):
        return pb.render_bar_report(pb.resolve_promotion_bar_report(rows))

    def test_a_clamped_run_does_not_render_like_a_clean_one(self, caplog):
        with caplog.at_level(logging.WARNING):
            clamped = self._render(self.LOOSENING)
        clean = self._render({})
        assert clamped != clean, (
            "a refused config row must be visible in the report body, which "
            "is the whole of this task"
        )
        assert "CLAMPED" in clamped and "CLAMPED" not in clean
        assert pb.PROMOTION_BAR_LICENCES_KEY in clamped

    def test_a_silent_run_says_so_rather_than_by_omission(self):
        clean = self._render({})
        assert "no `config` row for any G-C bar" in clean
        assert "CLAMPED" not in clean

    def test_the_clamp_past_a_bound_names_the_bound(self, caplog):
        rows = {"promotion_rate_floor": 0.1}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        with caplog.at_level(logging.WARNING):
            rendered = self._render(rows)
        assert "bound 0.3" in rendered
        assert "CLAMPED" in rendered

    def test_a_licensed_loosening_reads_as_honoured_not_clamped(self):
        rows = {"promotion_rate_floor": 0.4}
        rows.update(_licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}}))
        rendered = self._render(rows)
        assert "honoured, under a licence bounded at 0.3" in rendered
        assert "CLAMPED" not in rendered

    def test_a_free_tightening_reads_as_honoured_and_needs_no_licence(self):
        rendered = self._render({"promotion_rate_floor": 0.9})
        assert "honoured; it moves the bar its own conservative way" in rendered
        assert "CLAMPED" not in rendered

    def test_every_bar_appears_with_both_numbers(self):
        report = pb.resolve_promotion_bar_report({})
        assert [r.key for r in report.resolutions] == list(pb.PROMOTION_BARS)
        rendered = self._render({})
        for key, committed in pb.PROMOTION_BAR_DEFAULTS.items():
            assert key in rendered
            assert pb._fmt(committed) in rendered

    def test_the_prophylactic_bar_is_labelled_as_one(self):
        """The report must not let an unread bar read as a live protection."""
        assert "prophylactic" in self._render({})

    def test_the_report_and_the_verdict_read_one_resolution(self, caplog):
        """The number printed and the number a verdict uses are the same
        resolution, not two that agree today."""
        for rows in ({}, self.LOOSENING, {"promotion_rate_floor": 0.9}):
            with caplog.at_level(logging.WARNING):
                assert (
                    pb.resolve_promotion_bar_report(rows).bars
                    == pb.resolve_promotion_bars(rows)
                )

    def test_an_absent_row_is_not_reported_as_a_request(self):
        report = pb.resolve_promotion_bar_report({})
        assert not report.config_rows_present
        assert not report.licence_row_present
        assert all(r.requested is None and r.clamp is None
                   for r in report.resolutions)

    def test_a_licence_row_alone_is_still_disclosed(self):
        """A licence with no bar row moves nothing, and the report says the
        row is there — an operator who wrote one and saw no change needs to
        know it was read."""
        rows = _licence({"promotion_rate_floor": {
            "value": 0.3, "argument": LEDGER}})
        report = pb.resolve_promotion_bar_report(rows)
        assert report.licence_row_present and not report.config_rows_present
        rendered = pb.render_bar_report(report)
        assert f"`{pb.PROMOTION_BAR_LICENCES_KEY}` row present" in rendered

    def test_a_licence_row_holding_json_null_is_still_disclosed(self):
        """`Config.value` is JSONB, so a row can exist holding null. It
        licenses nothing — but reporting it absent tells an operator who
        wrote one that it was never read, which is a different fact."""
        report = pb.resolve_promotion_bar_report(
            {pb.PROMOTION_BAR_LICENCES_KEY: None}
        )
        assert report.licence_row_present
        assert f"`{pb.PROMOTION_BAR_LICENCES_KEY}` row present" in (
            pb.render_bar_report(report)
        )

    def test_the_directionless_bar_does_not_call_a_lower_value_past_a_bound(
        self, caplog
    ):
        """"Past" is this module's `!=` sense for the NEITHER bar, and a
        reader seeing 6 described as past 8 concludes the renderer is broken.
        The clamp is right either way; the sentence has to be too."""
        key = "promotion_rate_min_eligible"
        rows = {key: 6}
        rows.update(_licence({key: {"value": 8, "argument": LEDGER}}))
        with caplog.at_level(logging.WARNING):
            rendered = self._render(rows)
        assert "the licence names 8, not this value" in rendered
        assert "past" not in rendered

    def test_an_unreadable_row_still_raises_rather_than_rendering(self):
        with pytest.raises(ValueError):
            pb.resolve_promotion_bar_report({"promotion_rate_floor": "0.4"})


class TestTheDerivationIsStructuralNotIncidental:
    """The one-resolution guarantee cannot be pinned extensionally.

    T2.128's review planted the mutant that proves it: revert
    ``resolve_promotion_bars`` to an independent recomputation of the old
    merge loop and **every** test in this file still passes, because two
    implementations that agree today agree on every input a test can name —
    which is exactly the parallel-implementation drift the derivation exists
    to prevent. So the assertion is structural, in the repo's own AST-scan
    idiom: the public dict must be the report's ``bars`` and nothing else.
    """

    def test_resolve_delegates_to_the_report_and_computes_nothing(self):
        fn = ast.parse(
            textwrap.dedent(inspect.getsource(pb.resolve_promotion_bars))
        ).body[0]
        statements = [
            node for node in fn.body
            if not (isinstance(node, ast.Expr)
                    and isinstance(node.value, ast.Constant))
        ]
        assert len(statements) == 1, (
            "resolve_promotion_bars must be one return; anything else is a "
            "second resolution that agrees with the report until it does not"
        )
        returned = statements[0]
        assert isinstance(returned, ast.Return)
        assert isinstance(returned.value, ast.Attribute)
        assert returned.value.attr == "bars"
        call = returned.value.value
        assert isinstance(call, ast.Call)
        assert getattr(call.func, "id", None) == "resolve_promotion_bar_report"

    def test_the_runner_reads_the_report_it_prints(self):
        """The other half: run_gc_evidence must not resolve twice either."""
        source = (
            Path(pb.__file__).with_name("run_gc_evidence.py").read_text()
        )
        assert "get_promotion_bar_report(session)" in source
        assert "get_promotion_bars(" not in source, (
            "a second resolution in the runner would let the printed block and "
            "the verdicts disagree, which is the whole property"
        )


class TestPredicates:
    BARS = pb.resolve_promotion_bars({})

    def test_audit_underpowered_never_clears_even_at_zero(self):
        assert not pb.audit_clears(0.0, 19, self.BARS)
        assert not pb.audit_decidable(19, self.BARS)

    def test_audit_zero_rate_clears_at_the_floor(self):
        assert pb.audit_clears(0.0, 20, self.BARS)

    def test_audit_bar_is_strict(self):
        assert not pb.audit_clears(0.01, 200, self.BARS)
        assert pb.audit_clears(0.0099, 200, self.BARS)

    def test_audit_none_rate_never_clears(self):
        assert not pb.audit_clears(None, 200, self.BARS)

    def test_slice_floor_and_power(self):
        assert not pb.slice_clears(4, 4, self.BARS)  # unpowered, rate 1.0
        assert pb.slice_clears(3, 5, self.BARS)      # powered, 0.6
        assert not pb.slice_clears(2, 5, self.BARS)  # powered, 0.4

    def test_axis_needs_a_promotion_and_a_powered_bucket(self):
        assert not pb.axis_decidable([(5, 5)], 0, self.BARS)
        assert not pb.axis_decidable([(2, 4), (1, 3)], 3, self.BARS)
        assert pb.axis_decidable([(3, 5)], 3, self.BARS)

    def test_journal_completeness_is_zero_violations(self):
        assert pb.journal_completeness_clears(0)
        assert not pb.journal_completeness_clears(1)


class TestTheNonMonotoneBar:
    """`promotion_rate_min_eligible` has no conservative direction.

    At its own comparison site (`slice_powered`) higher is stricter, so a
    raise reads as a tightening and the first implementation waved it
    through silently. But the bar's *negation* defines the domain of the
    composed rule "every powered bucket must clear `promotion_rate_floor`":
    raising it silences buckets, and a silenced bucket cannot fail. Found by
    T2.127's review and reproduced here against the real predicates.
    """

    KEY = "promotion_rate_min_eligible"
    AXIS = [(6, 10), (2, 7)]

    def _composed_verdict_clears(self, bars):
        powered = [(p, e) for p, e in self.AXIS if pb.slice_powered(e, bars)]
        return all(pb.slice_clears(p, e, bars) for p, e in powered)

    def test_the_raise_this_bar_used_to_wave_through_flips_the_verdict(self):
        """The defect itself, pinned so it cannot come back as a 'tightening'."""
        committed = pb.resolve_promotion_bars({})
        assert not self._composed_verdict_clears(committed), (
            "the fixture must fail at the committed bar, or it proves nothing"
        )
        raised = {**committed, self.KEY: 8.0}
        assert self._composed_verdict_clears(raised), (
            "raising the bar must silence the failing bucket — this is the "
            "hazard, and if it stops being true this test is measuring nothing"
        )

    @pytest.mark.parametrize("candidate", [8.0, 2.0])
    def test_every_move_needs_a_licence(self, candidate, caplog):
        """Both directions, because neither is safe."""
        with caplog.at_level(logging.WARNING):
            bars = pb.resolve_promotion_bars({self.KEY: candidate})
        assert bars[self.KEY] == float(UNDER_POWERED_THRESHOLD)
        assert self.KEY in caplog.text

    def test_a_licence_naming_the_value_is_honoured(self):
        bars = pb.resolve_promotion_bars(
            {self.KEY: 8.0,
             pb.PROMOTION_BAR_LICENCES_KEY: {"licensed": {
                 self.KEY: {"value": 8.0, "argument": "gate-ledger.md, G-C"}}}},
        )
        assert bars[self.KEY] == 8.0

    def test_a_licence_does_not_license_a_different_value(self):
        bars = pb.resolve_promotion_bars(
            {self.KEY: 9.0,
             pb.PROMOTION_BAR_LICENCES_KEY: {"licensed": {
                 self.KEY: {"value": 8.0, "argument": "gate-ledger.md, G-C"}}}},
        )
        assert bars[self.KEY] == float(UNDER_POWERED_THRESHOLD), (
            "a licence names one value; anything else is unlicensed"
        )
