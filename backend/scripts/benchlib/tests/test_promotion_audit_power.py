"""T2.130 — what the false-promotion audit's verdict is actually worth.

The audit scored `observed rate < bar`. That rule is a coin flip against a
system sitting exactly at the bar, **at every sample size**, so a "clears" from
it carried almost no information. These tests pin the arithmetic behind that
claim and the behaviour of the confidence rule that answers the gate's real
question.
"""
import pytest

from benchlib.promotion_metrics import (
    FalsePromotionAudit,
    at_bar_pass_probability,
    binomial_cdf,
    clopper_pearson_upper,
    corroborations_required,
)

BAR = 0.01
CONF = 0.95


def _audit(k, n):
    return FalsePromotionAudit(
        total_corroborations=n,
        disputed_after_corroboration=k,
        human_rejected=0,
        false_promoted_facts=k,
    )


def test_more_data_does_not_repair_the_point_estimate_rule():
    """The finding. Pass probability at the bar stays ~0.5 forever.

    This is why "raise the corroboration floor" is not the fix, and why an
    independent probe's suggestion that n >= 300 would drop it meaningfully is
    arithmetically false.
    """
    probabilities = {n: at_bar_pass_probability(n, BAR) for n in (149, 300, 1000, 10000)}
    for n, p in probabilities.items():
        assert 0.40 < p < 0.60, f"n={n} gave {p}"
    # It does not trend toward zero with more data — the whole point.
    assert probabilities[10000] > 0.40


def test_the_confidence_rule_is_bounded_by_its_own_confidence_level():
    """Under `upper bound < bar`, an at-the-bar system passes at most 1-conf."""
    for n in (300, 500, 1000, 2000):
        p = at_bar_pass_probability(n, BAR, confidence=CONF)
        assert p <= 1.0 - CONF + 1e-9, f"n={n} gave {p}"


def test_the_confidence_rule_still_passes_a_genuinely_good_system():
    """A tightening that rejected everything would be useless, not conservative."""
    assert at_bar_pass_probability(1000, BAR, confidence=CONF) < 0.05
    # true rate 5x under the bar, n=1000: should pass nearly always
    threshold = -1
    for k in range(1001):
        if clopper_pearson_upper(k, 1000, CONF) < BAR:
            threshold = k
        else:
            break
    assert binomial_cdf(threshold, 1000, 0.002) > 0.90


def test_the_confidence_rule_is_strictly_a_tightening():
    """It can never clear a window the point estimate fails — so it needs no
    loosening licence under `promotion_bars`' floors discipline."""
    for n in (50, 149, 300, 1000):
        for k in range(0, min(n, 12)):
            audit = _audit(k, n)
            if audit.clears_with_confidence(BAR, CONF):
                assert audit.rate < BAR, f"k={k} n={n} cleared the bound but not the rate"


def test_the_measured_window_does_not_support_its_own_verdict():
    """1/149 — the number the record reports as `clears=True`."""
    audit = _audit(1, 149)
    assert audit.rate == pytest.approx(0.006711, abs=1e-5)
    assert audit.rate < BAR                      # the rule that "cleared"
    assert audit.upper_bound(CONF) == pytest.approx(0.0314, abs=5e-4)
    assert audit.clears_with_confidence(BAR, CONF) is False
    # And the window is too small to clear even with a perfect record.
    assert clopper_pearson_upper(0, 149, CONF) > BAR


def test_required_window_sizes_are_derived_not_guessed():
    """Replaces a stated decidability floor with a consequence of the bar."""
    assert corroborations_required(0, BAR, CONF) == 299
    assert corroborations_required(1, BAR, CONF) == 473
    assert corroborations_required(2, BAR, CONF) == 628


def test_clopper_pearson_matches_its_definition():
    """The bound is the p at which observing <= k stops being unsurprising."""
    for k, n in ((0, 10), (1, 149), (3, 200)):
        upper = clopper_pearson_upper(k, n, CONF)
        assert binomial_cdf(k, n, upper) == pytest.approx(1.0 - CONF, abs=1e-6)
    assert clopper_pearson_upper(5, 5, CONF) == 1.0
    with pytest.raises(ValueError):
        clopper_pearson_upper(3, 2, CONF)


def test_an_empty_window_reports_nothing_rather_than_zero():
    empty = _audit(0, 0)
    assert empty.rate is None
    assert empty.upper_bound(CONF) is None
    assert empty.clears_with_confidence(BAR, CONF) is None
