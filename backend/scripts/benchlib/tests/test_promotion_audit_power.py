"""T2.130 — what the false-promotion audit's verdict is actually worth.

The audit scored `observed rate < bar` until T2.132. That rule is a coin flip
against a system sitting exactly at the bar, **at every sample size**, so a
"clears" from it carried almost no information. These tests pin the arithmetic
behind that claim and the behaviour of the confidence rule that replaced it.
"""
import pytest

from benchlib import promotion_bars as pb
from benchlib.promotion_metrics import (
    _AUDIT_BAR_FOR_POWER,
    FALSE_PROMOTION_CONFIDENCE,
    FalsePromotionAudit,
    _render_audit_power,
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
    """1/149 — the window T2.129 measured, which the point-estimate rule
    reported as `clears=True` until the scored quantity changed."""
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


# ── the report must name the rule that is actually scored (T2.132) ───────────


def test_the_renderer_mirrors_the_bars_module_it_defers_to():
    """The mirrored constants carried a comment claiming a test caught a
    mismatch, and no test referenced either of them.

    It mattered less while the block was commentary. It decides what a
    cleared run's report *says* now, so the two copies of the bar are pinned
    to each other rather than to a sentence.
    """
    assert _AUDIT_BAR_FOR_POWER == pb.PROMOTION_BAR_DEFAULTS[
        "verification_false_promotion_bar"
    ]
    assert FALSE_PROMOTION_CONFIDENCE == CONF


def test_the_report_marks_the_bound_as_the_scored_line():
    """A block written while the point estimate was scored said so in words —
    "the rule scored above". Left standing, it invites a reader to quote the
    superseded number out of a run whose verdict came from the other one."""
    scored = [
        line for line in "".join(_render_audit_power(_audit(1, 149))).splitlines()
        if "SCORED" in line
    ]
    assert len(scored) == 1, "exactly one line may claim to be the scored rule"
    assert "bound" in scored[0]
    assert "point estimate" not in scored[0]


@pytest.mark.parametrize("k,n", [(1, 149), (1, 473), (0, 299), (0, 20), (3, 500)])
def test_the_rendered_verdict_is_the_predicates_verdict(k, n):
    """Two renderings of one rule drift; `resolve_promotion_bars` was
    restructured for exactly this reason and this block has the same shape."""
    block = "".join(_render_audit_power(_audit(k, n)))
    rendered_clears = "→ CLEARS" in block
    assert "→ does NOT clear" in block or rendered_clears
    assert rendered_clears is pb.audit_clears(k, n, pb.resolve_promotion_bars({}))
