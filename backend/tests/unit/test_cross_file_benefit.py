"""Phase-08 cross-file-binding skip heuristic must compare like populations.

It divided this-run's call-site count by the whole-repo 'calls' edge count, so on
an incremental run resolved_calls >> total_calls drove a strongly-negative
benefit and the phase was skipped every time — exactly when cross-file binding
helps the just-changed files. The benefit formula must clamp to [0,1].
"""
from __future__ import annotations

import pytest

from app.services.code_pipeline import _cross_file_benefit


def test_benefit_zero_when_fully_resolved():
    assert _cross_file_benefit(total_calls=10, resolved_calls=10) == 0.0


def test_benefit_positive_when_unresolved():
    assert _cross_file_benefit(total_calls=10, resolved_calls=9) == pytest.approx(0.1)


def test_benefit_clamped_when_resolved_exceeds_total():
    # Scoping resolved_calls to the same files should prevent this, but the
    # formula must never produce a negative benefit (the old skip-always bug).
    assert _cross_file_benefit(total_calls=10, resolved_calls=100) == 0.0


def test_benefit_zero_on_no_calls():
    assert _cross_file_benefit(total_calls=0, resolved_calls=5) == 0.0
