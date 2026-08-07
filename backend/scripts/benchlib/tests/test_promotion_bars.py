"""The G-C bars are pinned by value: moving a goalpost is a two-file diff.

gate-ledger.md rule 3 forbids widening a bar to fit a result. The committed
defaults ARE the stated bars (G-D's "config default" precedent), so this
suite pins each one by exact value — an edit to ``PROMOTION_BAR_DEFAULTS``
fails here until the pin is edited too, which is what makes a moved bar
visible in review rather than a quiet constant tweak.
"""
from __future__ import annotations

import pytest

from benchlib import promotion_bars as pb
from benchlib.promotion_metrics import UNDER_POWERED_THRESHOLD


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

    @pytest.mark.parametrize("bad", ["0.01", True, None, [0.01], {"value": "x"}])
    def test_unreadable_row_raises_never_reverts(self, bad):
        with pytest.raises(ValueError):
            pb.resolve_promotion_bars({"verification_false_promotion_bar": bad})


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
